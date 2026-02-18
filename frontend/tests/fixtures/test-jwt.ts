import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { importPKCS8, SignJWT } from 'jose'

const privateKeyPem = readFileSync(join(import.meta.dirname, 'test-private-key.pem'), 'utf8')

/**
 * Generates a signed RS256 JWT for use in Playwright tests.
 *
 * The token is verified by the Flask backend via the local JWKS server
 * started as a Playwright webServer (see playwright.config.ts).
 */
export async function makeTestJwt(userId: string, email: string): Promise<string> {
  const key = await importPKCS8(privateKeyPem, 'RS256')
  return new SignJWT({ sub: userId, email })
    .setProtectedHeader({ alg: 'RS256', kid: 'test-key-1' })
    .setIssuedAt()
    .setExpirationTime('1h')
    .sign(key)
}
