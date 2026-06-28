"""Clerk authentication adapter for JWT verification."""

import base64
import binascii
import logging
import time
from typing import Any, TypedDict

import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from backend.config import Settings
from backend.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class JWTPayload(TypedDict, total=False):
    """JWT token payload structure.

    Standard JWT claims following RFC 7519.
    """

    sub: str
    email: str
    iss: str
    aud: str
    exp: int
    iat: int
    azp: str
    sid: str


class ClerkAuthAdapter:
    """Adapter for Clerk JWT authentication with JWKS key caching.

    This adapter handles JWT token verification using Clerk's JWKS endpoint
    for public key retrieval. It implements caching to minimize API calls
    and includes comprehensive error handling for security monitoring.

    Attributes:
        config: Settings instance containing Clerk API credentials
        _key_cache: Dictionary mapping kid to cached public keys
        _cache_time: Dictionary mapping kid to cache timestamp
        _cache_ttl: Cache time-to-live in seconds (default 3600)
    """

    def __init__(self, config: Settings) -> None:
        """Initialize the ClerkAuthAdapter with configuration settings.

        Args:
            config: Settings instance containing Clerk publishable and
                secret keys
        """
        self.config = config
        self._key_cache: dict[str, str] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl: int = 3600
        self._logger = logging.getLogger(__name__)

    def verify_token(self, token: str | None) -> JWTPayload:
        """Verify and decode a JWT token using Clerk's public key.

        This method validates the token signature, expiration, and format.
        It retrieves the appropriate public key from cache or JWKS endpoint
        based on the token's kid header.

        Args:
            token: JWT token string to verify

        Returns:
            Decoded token payload as JWTPayload containing claims

        Raises:
            AuthenticationError: If token is invalid, expired, or malformed
            ValueError: If token is None or empty
            TypeError: If token is not a string
        """
        if token is None:
            raise TypeError("Authorization token required")

        if not isinstance(token, str):
            raise TypeError("Token must be a string")

        if token == "":
            raise ValueError("Authorization token required")

        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            alg = unverified_header.get("alg", "RS256")

            if alg == "HS256":
                key = self.config.clerk_secret_key
                algorithms = ["HS256"]
            elif kid:
                key = self._get_public_key(kid)
                algorithms = ["RS256"]
            else:
                self._logger.error("Token missing kid header for RS256")
                raise AuthenticationError("Invalid token format - missing kid")

            decoded: JWTPayload = jwt.decode(
                token,
                key,
                algorithms=algorithms,
                options={"verify_signature": True, "verify_exp": True},
            )

            user_id = decoded.get("sub", "unknown")[:10]
            self._logger.info(
                f"Successfully verified token for user: {user_id}..."
            )
            return decoded

        except jwt.ExpiredSignatureError:
            self._logger.warning("Attempted to verify expired token")
            raise AuthenticationError("Token expired, please log in again")
        except jwt.InvalidTokenError as e:
            self._logger.error(f"Invalid token signature: {str(e)}")
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except (ValueError, KeyError) as e:
            self._logger.error(f"Token format error: {str(e)}")
            raise AuthenticationError(f"Invalid token format: {str(e)}")

    def _get_public_key(self, kid: str) -> str:
        """Get public key for verification with caching support.

        Retrieves the public key from cache if valid, otherwise fetches
        from Clerk's JWKS endpoint. Updates cache with new keys.

        Args:
            kid: Key ID from token header

        Returns:
            Public key string in PEM format

        Raises:
            AuthenticationError: If key cannot be retrieved or parsed
        """
        current_time = time.time()

        if kid in self._key_cache and kid in self._cache_time:
            if current_time - self._cache_time[kid] < self._cache_ttl:
                self._logger.debug(f"Using cached key for kid: {kid[:10]}...")
                return self._key_cache[kid]

        self._logger.info(f"Fetching fresh key for kid: {kid[:10]}...")
        key = self._fetch_jwks_key(kid)
        self._key_cache[kid] = key
        self._cache_time[kid] = current_time

        return key

    def _fetch_jwks_key(self, kid: str) -> str:
        """Fetch public key from Clerk's JWKS endpoint.

        Makes HTTP request to Clerk's JWKS endpoint to retrieve the
        public key set and extracts the key matching the provided kid.

        Args:
            kid: Key ID to retrieve from JWKS

        Returns:
            Public key string in PEM format

        Raises:
            AuthenticationError: If network request fails or key not found
        """
        try:
            jwks_url = self._construct_jwks_url()
            self._logger.debug(f"Fetching JWKS from: {jwks_url}")

            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()

            jwks_data = response.json()
            return self._extract_key_for_kid(jwks_data, kid)

        except requests.RequestException as e:
            self._logger.error(f"Failed to fetch JWKS: {str(e)}")
            raise AuthenticationError("Unable to fetch public key from Clerk")
        except (KeyError, ValueError, IndexError) as e:
            self._logger.error(f"Failed to parse JWKS response: {str(e)}")
            raise AuthenticationError(f"Invalid JWKS response: {str(e)}")

    def fetch_user_email(self, clerk_user_id: str) -> str:
        """Fetch the primary email address for a Clerk user via the Backend API.

        Called when the JWT payload omits the email claim, which is the default
        for Clerk session tokens without a custom JWT Template.

        Args:
            clerk_user_id: Clerk user ID from the JWT sub claim

        Returns:
            Primary email address, or empty string if none found

        Raises:
            AuthenticationError: If the Clerk API request fails
        """
        try:
            response = requests.get(
                f"https://api.clerk.com/v1/users/{clerk_user_id}",
                headers={
                    "Authorization": f"Bearer {self.config.clerk_secret_key}"
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            primary_id = data.get("primary_email_address_id")
            for email_obj in data.get("email_addresses", []):
                if email_obj.get("id") == primary_id:
                    return str(email_obj["email_address"])
            addresses = data.get("email_addresses", [])
            return str(addresses[0]["email_address"]) if addresses else ""
        except requests.RequestException as e:
            self._logger.error(f"Failed to fetch user email from Clerk: {e}")
            raise AuthenticationError("Unable to fetch user details from Clerk")

    def _construct_jwks_url(self) -> str:
        """Construct JWKS endpoint URL from Clerk configuration.

        Returns the override URL when CLERK_JWKS_URL is set (e.g. for tests),
        otherwise derives the URL from the publishable key.

        Returns:
            JWKS endpoint URL string
        """
        if self.config.clerk_jwks_url:
            return self.config.clerk_jwks_url

        pub_key = self.config.clerk_publishable_key

        if pub_key.startswith(("pk_test_", "pk_live_")):
            prefix = (
                "pk_test_" if pub_key.startswith("pk_test_") else "pk_live_"
            )
            domain_part = pub_key.removeprefix(prefix)
            try:
                padding = "=" * (-len(domain_part) % 4)
                decoded = base64.b64decode(domain_part + padding).decode(
                    "utf-8"
                )
                domain = decoded[:-1] if decoded.endswith("$") else decoded
            except (binascii.Error, UnicodeDecodeError) as e:
                raise ValueError(
                    f"Failed to decode Clerk domain from publishable key: {e}"
                )
        else:
            domain = "clerk.example.com"

        return f"https://{domain}/.well-known/jwks.json"

    def _extract_key_for_kid(self, jwks_data: dict[str, Any], kid: str) -> str:
        """Extract and convert public key from JWKS response.

        Finds the key matching the provided kid in the JWKS response,
        extracts the RSA key parameters, and converts to PEM format.

        Args:
            jwks_data: JWKS response dictionary containing key set
            kid: Key ID to extract from JWKS

        Returns:
            Public key in PEM format

        Raises:
            KeyError: If kid not found in JWKS
            ValueError: If key data is malformed
        """
        keys = jwks_data.get("keys", [])

        for key_data in keys:
            if key_data.get("kid") == kid:
                return self._convert_jwk_to_pem(key_data)

        self._logger.error(f"Key ID {kid} not found in JWKS")
        raise KeyError(f"Key ID {kid} not found in JWKS")

    def _convert_jwk_to_pem(self, jwk: dict[str, Any]) -> str:
        """Convert JWK to PEM format for PyJWT.

        Extracts RSA key parameters from JWK and constructs a PEM-formatted
        public key suitable for JWT verification.

        Args:
            jwk: JWK dictionary containing RSA key parameters

        Returns:
            PEM-formatted public key string

        Raises:
            ValueError: If JWK data is invalid or incomplete
        """
        try:
            n_bytes = base64.urlsafe_b64decode(jwk["n"] + "==")
            e_bytes = base64.urlsafe_b64decode(jwk["e"] + "==")

            n = int.from_bytes(n_bytes, byteorder="big")
            e = int.from_bytes(e_bytes, byteorder="big")

            public_numbers = RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key(default_backend())

            pem = public_key.public_bytes(
                encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
            )

            return pem.decode("utf-8")

        except (KeyError, ValueError) as ex:
            self._logger.error(f"Failed to convert JWK to PEM: {str(ex)}")
            raise ValueError(f"Invalid JWK format: {str(ex)}")
