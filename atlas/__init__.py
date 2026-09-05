"""
Open Derm Trial Atlas -- schema v2 ontology, parsers, and migration.

Every trial record is a nested dict of *sourced values*:

    {"value": <typed>, "source_type": ..., "source_url": ..., "source_excerpt": ...,
     "extracted_by": ..., "reviewed_by": ..., "confidence": ...}

v2 replaces every free-text `value` with a typed, atomic structure (see
`atlas/schema.py` for the spec and `docs/SCHEMA.md` for the field-by-field
documentation). Free prose survives only as provenance (`source_excerpt`,
or the CT.gov `verbatim` title on an endpoint), never as the queryable value.
"""

SCHEMA_VERSION = 2
