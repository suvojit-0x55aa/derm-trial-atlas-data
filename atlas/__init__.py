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

v4 moves 6 DRUG-level fields (molecule.mechanism_of_action,
adverse_events.boxed_warning, real_world_safety.faers_summary,
exclusivity.{regulatory_application,orange_book,purple_book}) off the trial
record entirely: a drug's own facts are extracted once into
data/drugs/<slug>.json and a trial now carries only a small pointer
(source_type "drug_level_ref", value {"drug", "application_number"}) instead
of a full re-description. `identity.sponsor` is NOT moved -- it genuinely
differs across a drug's own trials sometimes (development/commercial rights
change hands mid-program). See atlas/drugs.py for the record shape, the
migration, and the resolve step that reconstructs a trial's full facts for
consumers (build_csv.py) that don't care where a fact is stored.
"""

SCHEMA_VERSION = 4
