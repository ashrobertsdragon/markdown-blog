"""Value objects for the domain layer.

Value objects are immutable objects that represent descriptive aspects
of the domain with no conceptual identity. They are defined only by
their attributes.
"""

from backend.domain.value_objects.role import Role

__all__ = ["Role"]
