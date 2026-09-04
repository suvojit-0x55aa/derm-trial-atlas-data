# Open Derm Trial Atlas -- schema v2 (field reference)

Generated from `atlas/schema.py` by `scripts/export_schema.py`; do not edit by hand.
The machine-readable form is `schema/trial.schema.json`.

Every field below is a **sourced value**:

```json
{"value": <typed, see table>, "source_type": "ctgov_api" | ..., "source_url": str|null,
 "source_excerpt": str|null, "extracted_by": str|null, "reviewed_by": str|null, "confidence": number|null}
```

`source_type` is one of: `ctgov_api`, `ctgov_text_extraction`, `protocol_pdf_extraction`, `publication_extraction`, `openfda_label`, `openfda_faers`, `orange_book`, `purple_book`, `needs_extraction`.
A `needs_extraction` field always has `value: null`; every other source type carries a value of the
type in the table (nullable where marked). Free prose never lives in `value` -- where a v1 field was
prose, that prose is now in `source_excerpt` (or the endpoint's `verbatim` / intervention's
`description`) as provenance, and `value` holds the atomic decomposition.

## Trial record fields

| Field | Value type | Meaning | v1 name |
|---|---|---|---|
| `nct_id` | string \| null | ClinicalTrials.gov identifier |  |
| `identity.trial_name` | string \| null | CT.gov acronym (null when the registry has none) |  |
| `identity.official_title` | string \| null | CT.gov official title |  |
| `identity.sponsor` | string \| null | lead sponsor name |  |
| `identity.phase` | list[string] \| null | CT.gov phases, e.g. ['PHASE3'] |  |
| `molecule.drug` | string \| null | canonical drug name (curated) |  |
| `molecule.intervention_names` | list[string] \| null | CT.gov intervention names |  |
| `molecule.intervention_type` | list[string] \| null | CT.gov intervention types |  |
| `molecule.mechanism_of_action` | Mechanism \| null | typed mechanism from the FDA label section 12.1; label text in source_excerpt |  |
| `molecule.dosing_regimen` | list[Intervention] \| null | one typed object per CT.gov intervention |  |
| `population.condition` | list[string] \| null | CT.gov conditions |  |
| `population.min_age_years` | number \| null | minimum age in years (CT.gov '18 Years' -> 18) | `population.min_age` |
| `population.max_age_years` | number \| null | maximum age in years; null = no upper limit stated | `population.max_age` |
| `population.sex` | enum(ALL \| FEMALE \| MALE) \| null | CT.gov sex |  |
| `population.enrollment_count` | integer \| null | CT.gov enrollment count |  |
| `population.severity_criteria` | Severity \| null | baseline severity eligibility thresholds as ScoreCriterion rows | `population.severity_definition` |
| `design.study_type` | string \| null | CT.gov studyType |  |
| `design.allocation` | string \| null | CT.gov allocation |  |
| `design.intervention_model` | string \| null | CT.gov interventionModel |  |
| `design.masking` | string \| null | CT.gov masking |  |
| `design.number_of_arms` | integer \| null | count of CT.gov armGroups |  |
| `design.background_therapy` | BackgroundTherapy \| null | monotherapy vs combination design and the background regimen | `design.background_therapy_rule` |
| `endpoints.primary_endpoints` | list[Endpoint] \| null | typed primary outcome measures (CT.gov order) | `endpoints.primary_endpoint_measure` |
| `endpoints.secondary_endpoints` | list[Endpoint] \| null | typed secondary outcome measures (CT.gov order) | `endpoints.secondary_endpoint_measures` |
| `endpoints.multiplicity_control` | MultiplicityControl \| null | testing hierarchy / Type-I-error control | `endpoints.endpoint_hierarchy_multiplicity` |
| `timing_ops.start_date` | PartialDate \| null | CT.gov start date with precision |  |
| `timing_ops.primary_completion_date` | PartialDate \| null | CT.gov primary completion date with precision |  |
| `timing_ops.completion_date` | PartialDate \| null | CT.gov completion date with precision |  |
| `timing_ops.study_schedule` | StudySchedule \| null | periods, visit cadence, key weeks | `timing_ops.visit_schedule` |
| `timing_ops.rescue_therapy` | RescueTherapy \| null | rescue-treatment rules | `timing_ops.rescue_therapy_rules` |
| `adverse_events.serious_adverse_event_rate` | list[ArmRate] \| null | per-arm serious AE rate from CT.gov results |  |
| `adverse_events.death_rate` | list[ArmRate] \| null | per-arm death rate from CT.gov results |  |
| `adverse_events.most_common_adverse_events` | list[AdverseEventTerm] \| null | top non-serious AEs by MedDRA PT with per-arm rates |  |
| `adverse_events.discontinuation_due_to_ae_rate` | list[ArmDiscontinuation] \| null | per-arm discontinuation-for-AE rate |  |
| `adverse_events.boxed_warning` | BoxedWarning \| null | typed boxed warning; present=false is a confirmed absence |  |
| `real_world_safety.faers_summary` | FaersSummary \| null | openFDA FAERS post-marketing report summary (drug-level) |  |
| `exclusivity.regulatory_application` | RegulatoryApplication \| null | NDA/BLA join key for Orange/Purple Book (drug-level) |  |
| `exclusivity.orange_book` | OrangeBookRecord \| null | Orange Book patents + exclusivities (small-molecule NDAs only) |  |
| `exclusivity.purple_book` | PurpleBookRecord \| null | Purple Book licensure + BPCIA exclusivity (biologic BLAs only) |  |

Plus the top-level literal `schema_version: 2`.

## ScoreCriterion

ScoreCriterion: one threshold on one clinical scale

| Key | Type | Notes |
|---|---|---|
| `scale` | string \| null | canonical scale name, e.g. EASI, IGA, vIGA-AD, BSA, Pruritus NRS; null for non-scale criteria |
| `scale_component` | string \| null | sub-scale / domain (e.g. 'Sleep domain', 'Anxiety') |
| `scale_variant` | enum(peak_daily \| peak_daily_weekly_average \| worst_daily \| worst_daily_weekly_average \| severity) \| null | pruritus NRS flavour |
| `metric` | enum(absolute_score \| percent_improvement_from_baseline \| point_reduction_from_baseline \| point_improvement_from_baseline \| percent_bsa \| disease_duration_years \| percent_of_response_lost) |  |
| `comparator` | enum(>= \| > \| <= \| < \| == \| in) |  |
| `value` | any | number, or list of numbers when comparator is 'in' |
| `unit` | enum(score \| percent \| points \| years) |  |
| `scale_min` | integer \| null |  |
| `scale_max` | integer \| null |  |
| `assessed_at` | list[string] \| null | screening | baseline | week_N |
| `scale_anchors` | list[{score: integer, label: string}] \| null |  |

## Endpoint

| Key | Type | Notes |
|---|---|---|
| `verbatim` | string | CT.gov outcome measure title, unchanged (provenance) |
| `rank` | enum(primary \| secondary) |  |
| `position` | integer |  |
| `measure_type` | enum(responder_rate \| percent_change_from_baseline \| change_from_baseline \| absolute_value \| time_to_event \| count \| loss_of_response \| flare_incidence \| safety_incidence \| immunogenicity \| pharmacokinetics \| drug_usage \| other) |  |
| `scale` | string \| null |  |
| `scale_component` | string \| null |  |
| `scale_variant` | enum(peak_daily \| peak_daily_weekly_average \| worst_daily \| worst_daily_weekly_average \| severity) \| null |  |
| `responder_criteria` | list[ScoreCriterion] |  |
| `baseline_reference` | enum(baseline \| rescue_baseline) \| null |  |
| `timepoints` | list[Timepoint] |  |
| `through` | {value: integer, unit: enum(week \| day)} \| null |  |
| `analysis_population` | enum(main_study \| adolescents \| adults \| pediatrics \| full_analysis_set \| per_protocol \| prior_cyclosporine_use \| comorbid_asthma \| re_randomized_responders \| initially_randomized_to_active) \| null |  |
| `subgroup_criteria` | list[ScoreCriterion] |  |
| `subgroup_labels` | list[enum(main_study \| adolescents \| adults \| pediatrics \| full_analysis_set \| per_protocol \| prior_cyclosporine_use \| comorbid_asthma \| re_randomized_responders \| initially_randomized_to_active)] |  |
| `study_period` | enum(double_blind \| rescue \| maintenance \| treatment_period) \| null |  |
| `event_type` | enum(TEAE \| serious_TEAE \| TEAE_leading_to_discontinuation \| serious_TEAE_leading_to_discontinuation \| skin_infection_TEAE \| skin_infection_TEAE_requiring_systemic_treatment \| AE_or_SAE \| flare \| anti_drug_antibodies \| TCS_use \| TCS_free_days \| TCS_TCI_free_days \| topical_medication_free_days \| steroid_free_days \| serum_concentration \| plasma_concentration) \| null |  |
| `time_frame` | string \| null | CT.gov timeFrame text (primary outcomes) |

## EndpointRef

| Key | Type | Notes |
|---|---|---|
| `label` | string |  |
| `scale` | string \| null |  |
| `responder_criteria` | list[ScoreCriterion] |  |
| `timepoint_week` | integer \| null |  |
| `alpha` | number \| null |  |
| `step` | integer \| null |  |

## Timepoint

| Key | Type | Notes |
|---|---|---|
| `value` | integer |  |
| `unit` | enum(week \| day) |  |
| `end_value` | integer \| null |  |

## Severity

| Key | Type | Notes |
|---|---|---|
| `severity_label` | enum(moderate_to_severe) \| null |  |
| `basis` | enum(eligibility_text \| cross_reference) |  |
| `cross_reference` | {study_ids: list[string], trial_names: list[string]} \| null |  |
| `source_criterion_numbers` | list[integer] |  |
| `baseline_visit_number` | integer \| null |  |
| `criteria` | list[ScoreCriterion] |  |

## Intervention

| Key | Type | Notes |
|---|---|---|
| `intervention_name` | string |  |
| `description` | string | CT.gov intervention description, unchanged |
| `is_placebo` | boolean |  |
| `route` | enum(oral \| subcutaneous \| intravenous \| topical) \| null |  |
| `dose_form` | enum(tablet \| injection \| solution \| cream \| ointment) \| null |  |
| `dose_value` | number \| null |  |
| `dose_unit` | string \| null |  |
| `units_per_dose` | integer \| null |  |
| `frequency` | enum(once_daily \| twice_daily \| weekly \| every_2_weeks \| every_4_weeks) \| null |  |
| `duration_weeks` | integer \| null |  |
| `dosing_periods` | list[{start_value: integer, start_unit: enum(day \| week), end_value: integer, end_unit: enum(day \| week)}] |  |
| `administration_sites` | list[string] |  |
| `antibody_isotype` | string \| null |  |
| `molecular_target` | string \| null |  |
| `arm_names` | list[string] |  |
| `co_administered_with` | list[string] |  |

## Mechanism

| Key | Type | Notes |
|---|---|---|
| `modality` | enum(monoclonal_antibody \| small_molecule \| fusion_protein \| other) |  |
| `drug_class` | string \| null |  |
| `antibody_isotype` | string \| null |  |
| `binding_targets` | list[string] |  |
| `pathway_cytokines` | list[string] |  |
| `receptor_subunits` | list[string] |  |
| `kinases_inhibited` | list[string] |  |
| `lower_potency_kinases` | list[string] |  |
| `selectivity` | list[{over: string, fold: integer, comparator: enum(== \| >)}] |  |
| `reversible` | boolean \| null |  |
| `mechanism_established` | boolean \| null |  |
| `label_section` | string \| null |  |

## BackgroundTherapy

| Key | Type | Notes |
|---|---|---|
| `regimen_type` | enum(monotherapy \| combination_tcs \| standardized_background_topical) \| null |  |
| `background_agent_class` | string \| null |  |
| `tcs_regimen` | enum(standardized \| step_down) \| null |  |
| `step_down_rule` | {initial_potency: string, initial_frequency: string, initial_target: string \| null, max_consecutive_weeks: integer, then_potency: string, then_frequency: string, repeat_on_recurrence: boolean, stop_on_local_or_systemic_toxicity: boolean} \| null |  |
| `recommended_agents` | list[Agent] |  |
| `emollient_required` | boolean \| null |  |
| `emollient_frequency` | string \| null |  |
| `prohibited_concomitant` | list[string] |  |
| `permitted_concomitant` | list[string] |  |
| `applies_to_rerandomized_maintenance` | boolean \| null |  |
| `sponsor_trial_ids` | list[string] |  |
| `study_drug_doses_mg` | list[number] |  |
| `population_note` | string \| null |  |

## MultiplicityControl

| Key | Type | Notes |
|---|---|---|
| `procedure` | enum(serial_gatekeeping \| graphical \| sequential_bonferroni \| closed_testing_bonferroni \| gatekeeping_with_holm) \| null |  |
| `familywise_error_controlled` | boolean |  |
| `alpha` | number \| null |  |
| `alpha_sided` | integer |  |
| `alpha_per_dose` | number \| null |  |
| `co_primary_endpoints` | list[EndpointRef] |  |
| `testing_sequence` | list[EndpointRef] |  |
| `alpha_split` | list[{group: string, n_endpoints: integer \| null, alpha: number \| null, method: string, timepoint_week: integer \| null}] |  |
| `alpha_recycling` | boolean \| null |  |
| `doses_compared` | list[string] |  |
| `dose_comparison_order` | list[string] |  |
| `branching_on` | EndpointRef \| null |  |
| `regulatory_variants` | list[enum(US \| EU)] |  |
| `rescue_counted_as_nonresponder` | boolean \| null |  |
| `active_comparator_excluded_from_hierarchy` | string \| null |  |
| `background_tcs` | boolean \| null |  |
| `method_citations` | list[string] |  |
| `finalized_in_sap` | boolean \| null |  |
| `same_design_as` | list[{nct_id: string, trial_name: string}] |  |
| `gatekeeping_structure` | boolean \| null |  |
| `further_endpoints_through_week` | integer \| null |  |

## StudySchedule

| Key | Type | Notes |
|---|---|---|
| `screening_days` | integer \| null |  |
| `screening_washout` | boolean \| null |  |
| `periods` | list[{name: enum(screening \| randomized_treatment \| double_blind_treatment \| initial_treatment \| maintenance_treatment \| continuation_treatment \| induction_treatment \| long_term_maintenance \| long_term_extension \| follow_up \| double_dummy_treatment \| oral_only_treatment \| off_treatment_follow_up), start_week: integer \| null, end_week: integer \| null, duration_weeks: integer \| null, blinding: string \| null, background_tcs: boolean \| null}] |  |
| `dosing_interval` | string \| null |  |
| `visit_cadence` | enum(weekly \| every_2_weeks \| every_4_weeks) \| null |  |
| `visit_cadence_until_week` | integer \| null |  |
| `visit_weeks` | list[integer] \| null |  |
| `visit_days` | list[integer] \| null |  |
| `phone_contact_weeks` | list[integer] \| null |  |
| `primary_endpoint_week` | integer \| null |  |
| `end_of_treatment_week` | integer \| null |  |
| `end_of_study_week` | integer \| null |  |
| `total_duration_weeks` | integer \| null |  |
| `follow_up_weeks` | integer \| null |  |
| `follow_up_days` | integer \| null |  |
| `follow_up_visit_week` | integer \| null |  |
| `long_term_extension` | boolean \| null |  |
| `extension_end_week` | integer \| null |  |
| `extension_visit_interval_weeks` | integer \| null |  |
| `extension_study_id` | string \| null |  |
| `rerandomization_week` | integer \| null |  |
| `maintenance_arms` | list[string] \| null |  |
| `maintenance_response_check_weeks` | list[integer] \| null |  |
| `last_injection_week` | integer \| null |  |
| `key_secondary_weeks` | list[integer] \| null |  |
| `follow_up_visit_interval_weeks` | integer \| null |  |
| `end_of_treatment_weeks_after_last_dose` | integer \| null |  |
| `background_tcs_from_day` | integer \| null |  |
| `primary_endpoint_refs` | list[EndpointRef] |  |
| `double_dummy_arms` | list[string] |  |
| `active_comparator` | string \| null |  |
| `boilerplate_reused_from` | list[string] |  |
| `conflicts_with_trial` | string \| null |  |
| `full_visit_table_available` | boolean |  |
| `source_inconsistency` | string \| null |  |

## RescueTherapy

| Key | Type | Notes |
|---|---|---|
| `permitted` | boolean \| null |  |
| `trigger` | enum(investigator_discretion \| protocol_response_threshold \| flare_definition \| prohibited) \| null |  |
| `earliest_week` | integer \| null |  |
| `prohibited_through_week` | integer \| null |  |
| `trigger_rules` | list[{from_week: integer \| null, to_week: integer \| null, criterion: ScoreCriterion, consecutive_visits: integer}] |  |
| `flare_definition` | list[ScoreCriterion] |  |
| `first_step` | enum(topical \| systemic) \| null |  |
| `topical_min_days_before_systemic` | integer \| null |  |
| `topical_rescue_requires_study_drug_discontinuation` | boolean \| null |  |
| `systemic_rescue_requires_study_drug_discontinuation` | boolean \| null |  |
| `resume_after_systemic_rescue_half_lives` | integer \| null |  |
| `resume_after_phototherapy_months` | integer \| null |  |
| `rescued_counted_as_nonresponder` | boolean \| null |  |
| `rescued_counted_as_treatment_failure` | boolean \| null |  |
| `continue_visits_after_discontinuation` | boolean \| null |  |
| `continue_visits_through_week` | integer \| null |  |
| `topical_rescue_not_counted_after_week` | integer \| null |  |
| `topical_agents` | list[Agent] |  |
| `topical_potency_classes` | list[PotencyClass] |  |
| `tci_reserved_areas` | list[string] |  |
| `systemic_agents` | list[string] |  |
| `oral_corticosteroid_limit` | {agents: list[string], max_mg_per_kg: number, max_consecutive_weeks: integer} \| null |  |
| `rescue_period` | {drug: string, dose_mg: number, frequency: enum(once_daily \| twice_daily \| weekly \| every_2_weeks \| every_4_weeks), duration_weeks: integer, with_topical_standard_of_care: boolean} \| null |  |
| `escape_arm_washout_half_lives` | integer \| null |  |
| `maintenance_period_rule` | {topical_rescue: string, systemic_rescue: string} \| null |  |
| `permitted_concomitant` | list[string] |  |
| `recorded_in_ecrf` | boolean \| null |  |
| `applies_to_period` | string \| null |  |
| `long_term_extension_eligible_after_rescue` | boolean \| null |  |
| `topical_agent_class` | string \| null |  |
| `rationale` | string \| null |  |

## Agent

| Key | Type | Notes |
|---|---|---|
| `name` | string |  |
| `strength_pct` | number \| null |  |
| `form` | string \| null |  |
| `potency` | string \| null |  |

## PotencyClass

| Key | Type | Notes |
|---|---|---|
| `system` | string \| null |  |
| `comparator` | enum(>= \| > \| <= \| < \| == \| in) |  |
| `class` | any |  |

## ArmRate

| Key | Type | Notes |
|---|---|---|
| `arm` | string |  |
| `n_affected` | integer |  |
| `n_at_risk` | integer |  |
| `pct` | number \| null |  |

## ArmDiscontinuation

| Key | Type | Notes |
|---|---|---|
| `arm` | string |  |
| `n_discontinued` | integer |  |
| `n_started` | integer |  |
| `pct` | number \| null |  |

## AdverseEventTerm

| Key | Type | Notes |
|---|---|---|
| `meddra_pt` | string |  |
| `meddra_soc` | string \| null |  |
| `per_arm` | list[ArmRate] |  |

## BoxedWarning

| Key | Type | Notes |
|---|---|---|
| `present` | boolean |  |
| `title` | string \| null |  |
| `warning_categories` | list[enum(serious_infections \| mortality \| malignancy \| mace \| thrombosis \| suicidal_ideation \| hepatotoxicity \| embryo_fetal_toxicity)] |  |
| `referenced_label_sections` | list[string] |  |
| `product_names` | list[string] |  |

## PartialDate

| Key | Type | Notes |
|---|---|---|
| `date` | date | ISO date YYYY-MM-DD |
| `precision` | enum(year \| month \| day) |  |

## FaersSummary

| Key | Type | Notes |
|---|---|---|
| `query` | {search_field: string, search_term: string, receivedate_from: date \| null, receivedate_to: date \| null, api_urls: list[string], data_last_updated: date \| null} |  |
| `total_reports` | integer |  |
| `serious_reports` | integer \| null |  |
| `death_reports` | integer \| null |  |
| `hospitalization_reports` | integer \| null |  |
| `life_threatening_reports` | integer \| null |  |
| `disability_reports` | integer \| null |  |
| `top_reactions` | list[ReactionRow] |  |
| `top_serious_reactions` | list[ReactionRow] |  |
| `reports_by_year` | list[{year: integer, report_count: integer}] |  |
| `meddra_version` | string \| null |  |

## ReactionRow

| Key | Type | Notes |
|---|---|---|
| `meddra_pt` | string |  |
| `report_count` | integer |  |
| `pct_of_reports` | number \| null |  |

## OrangeBookRecord

| Key | Type | Notes |
|---|---|---|
| `application_type` | enum(N \| A) |  |
| `application_number` | string |  |
| `ingredient` | string |  |
| `trade_name` | string |  |
| `applicant` | string |  |
| `applicant_full_name` | string \| null |  |
| `products` | list[{product_number: string, strength: string, dosage_form: string, route: string \| null, approval_date: date \| null, rld: boolean, rs: boolean, te_code: string \| null, marketing_type: string}] |  |
| `patents` | list[{patent_number: string, expiration_date: date \| null, drug_substance_claim: boolean, drug_product_claim: boolean, patent_use_code: string \| null, delisted: boolean, submission_date: date \| null, product_numbers: list[string]}] |  |
| `exclusivities` | list[{code: string, expiration_date: date \| null, product_numbers: list[string]}] |  |
| `latest_patent_expiration` | date \| null | ISO date YYYY-MM-DD |
| `latest_exclusivity_expiration` | date \| null | ISO date YYYY-MM-DD |
| `data_file_date` | string \| null |  |

## PurpleBookRecord

| Key | Type | Notes |
|---|---|---|
| `bla_number` | string |  |
| `proprietary_name` | string \| null |  |
| `proper_name` | string |  |
| `applicant` | string \| null |  |
| `license_type` | enum(351(a) \| 351(k)) \| null |  |
| `license_number` | string \| null |  |
| `center` | string \| null |  |
| `products` | list[{product_number: string \| null, strength: string \| null, dosage_form: string \| null, route: string \| null, presentation: string \| null, marketing_status: string \| null, licensure: string \| null, approval_date: date \| null, submission_type: string \| null, supplement_number: string \| null}] |  |
| `first_approval_date` | date \| null | ISO date YYYY-MM-DD |
| `date_of_first_licensure` | date \| null | ISO date YYYY-MM-DD |
| `reference_product_exclusivity_expiration` | date \| null | ISO date YYYY-MM-DD |
| `exclusivity_expiration_date` | date \| null | ISO date YYYY-MM-DD |
| `first_interchangeable_exclusivity_expiration` | date \| null | ISO date YYYY-MM-DD |
| `orphan_exclusivity_expiration` | date \| null | ISO date YYYY-MM-DD |
| `patent_list_provided` | boolean \| null |  |
| `biosimilars` | list[{proper_name: string, proprietary_name: string \| null, bla_number: string, applicant: string \| null, approval_date: date \| null, license_type: enum(351(k)), interchangeable_approval_date: date \| null}] |  |
| `data_file_month` | string \| null |  |

## RegulatoryApplication

| Key | Type | Notes |
|---|---|---|
| `application_type` | enum(NDA \| BLA) |  |
| `application_number` | string |  |
| `registry` | enum(orange_book \| purple_book) |  |
| `center` | string \| null |  |
| `proprietary_name` | string \| null |  |
| `applicant` | string \| null |  |
| `first_approval_date` | date \| null | ISO date YYYY-MM-DD |
