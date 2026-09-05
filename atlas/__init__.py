"""
Open Derm Trial Atlas -- schema v3 ontology, parsers, and migration.

Every trial record is a nested dict of *sourced values*:

    {"value": <typed>, "source_type": ..., "source_url": ..., "source_excerpt": ...,
     "extracted_by": ..., "reviewed_by": ..., "confidence": ...}

v2 replaced every free-text `value` with a typed, atomic structure (see
`atlas/schema.py` for the spec and `docs/SCHEMA.md` for the field-by-field
documentation). Free prose survives only as provenance (`source_excerpt`,
or the CT.gov `verbatim` title on an endpoint), never as the queryable value.

v3 adds one new field group, `results` (arms / arm_results / effect_estimates /
published_results): normalized per-arm CT.gov results and effect estimates,
referencing the existing `endpoints.*` objects by (rank, position, verbatim
hash) rather than re-describing them. See atlas/migrate.py's
`migrate_v2_to_v3` for the pure, no-op upgrade (new fields default to
needs_extraction; no v2 value is touched).
"""

SCHEMA_VERSION = 3
