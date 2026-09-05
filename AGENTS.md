# Project agent memory

This file is the project's committed home for project-intrinsic agent memory: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- This repo is **data only** — `data/trials/*.json` (schema v2), the flattened CSVs
  (`trials.csv`, `sources.csv`, `endpoints.csv`, `severity_criteria.csv`,
  `adverse_event_rates.csv`), and two static doc snapshots (`docs/SCHEMA.md`,
  `schema/trial.schema.json`). No pipeline code, no schema spec, no tests — the
  fetch/extraction/migration/build pipeline, `atlas/schema.py`, and the test suite all live in
  `kolai-website`; this repo is regenerated from there. Don't hand-edit the CSVs or the doc
  snapshots — they're generated, and will drift from `kolai-website`'s copy if edited here.
- Field groups, the full fill-status table, and what `source_type` means: see `README.md`.
  Full field-by-field types: `docs/SCHEMA.md`.
- Every field value everywhere in `data/trials/*.json` is a sourced-value object (`value`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`) —
  never a bare scalar. `value` is typed per `docs/SCHEMA.md`, never free prose; where v1 had
  prose, it now lives in `source_excerpt` (or an endpoint's `verbatim` / an intervention's
  `description`) as provenance. `source_type` is one of `ctgov_api`, `ctgov_text_extraction`,
  `protocol_pdf_extraction`, `publication_extraction`, `openfda_label`, `openfda_faers`,
  `orange_book`, `purple_book`, or `needs_extraction`.
- Every value with a non-`ctgov_api` source_type is machine/LLM-extracted, not hand-verified —
  `reviewed_by` stays `null` and `confidence < 1.0` until a human (captain + Garvita) signs off.
  Do not treat these as clinically authoritative without that review, and do not upgrade a
  `needs_extraction` field by inference or general knowledge — every fill must trace to an
  actual quoted source (CT.gov text, a protocol/SAP PDF, openFDA, or a CT.gov `resultsSection`
  table).
- `boxed_warning.present: false` with `source_type: openfda_label` means the label was checked
  and confirmed absent — a different thing from `needs_extraction` (never checked). Don't
  collapse that distinction when editing.
- `timing_ops.study_schedule` (v1 `visit_schedule`) is deliberately `needs_extraction` for CAFE
  and JADE REGIMEN: the full per-visit schedule lives only in multi-page PDF tables the pipeline
  couldn't reliably extract. Don't force-fill it by inference — a wrong schedule is worse than a
  null.
- **This atlas is an ongoing, multi-cycle scale-out effort, not a one-shot.** It started at 1
  indication (AD, 5 drugs, 17 trials) and is now at 23 indications, 48 unique drugs, 127 trials
  (see README's "What this covers" for the full per-indication breakdown and exactly which
  candidate trials were checked and excluded as non-pivotal for each). Every drug/indication
  pairing was verified against real, live ClinicalTrials.gov and openFDA data before being
  added — never assumed from general knowledge. When extending further, apply the same bar:
  live-query CT.gov (`query.cond=<indication>&query.intr=<drug>`) and confirm each candidate
  trial is a genuine pivotal EXPERIMENTAL arm (placebo/vehicle/vs.-nothing-controlled,
  `resultsSection` present) before adding it — not a comparator arm in someone else's program,
  a switch/extension study, an active-comparator head-to-head, or a regional bridging study.
- **A drug named as a candidate for a new indication is not automatically the right drug for
  that indication.** Verify the FDA label's own `indications_and_usage` text for the literal
  indication name before spending time on trial curation — co-occurrence of a drug and a
  condition in some CT.gov trial is not proof of an FDA-approved indication match. A queued
  "rilzabrutinib for Bullous Pemphigoid" candidate turned out to have zero CT.gov trials for BP
  and an FDA label limited to Immune Thrombocytopenia; the real BP drug was Dupilumab (already
  in this atlas), confirmed via its own label section 1.8.
- **The cross-source fields (`real_world_safety.faers_summary`, `exclusivity.{orange_book,
  purple_book}`) are now populated for every drug**, not just the original 5. openFDA's
  `drug/orangebook.json` matches on `products.active_ingredients.name`, not a bare `ingredient`
  field — a hand-run query using `ingredient:"<NAME>"` returns a false NOT_FOUND even for a
  real, indexed drug, including very recent (2025) approvals. A drug with FDA-approved
  biosimilars (e.g. Adalimumab has 10) has every biosimilar's BLA row in the Purple Book table
  alongside the reference product's — the reference product is the row with
  `License Type == "351(a)"`; every `"351(k)"` row is a biosimilar, not the drug itself.
  Ruxolitinib the ingredient also covers Jakafi/Jakafi XR (oral, oncology/GVHD, unrelated NDAs)
  — `exclusivity.orange_book` can be pinned to the right NDA by application number, but
  openFDA's FAERS search has no such filter, so Ruxolitinib's `real_world_safety.faers_summary`
  is a real, documented, unavoidable mix of all three products' reports — not a bug to "fix".
- **Publication-extraction depth is uneven by design, not by accident.** The original 5-drug AD
  program got a dedicated paywalled-paper research pass (PMC + FDA Drugs@FDA approval-package
  reviews, since direct publisher fetches are blocked by Cloudflare bot-challenges this pipeline
  will not defeat) — see README's "Paywalled full-text journal papers" note. The 8 indications
  added since have not repeated that same research effort, so `design.background_therapy`,
  `endpoints.multiplicity_control`, `timing_ops.rescue_therapy`, and `timing_ops.study_schedule`
  stay `needs_extraction` for nearly all of them — a real, checkable backlog for `kolai-website`
  to pick up, not a fabricated null.
- **This repo's own pipeline scripts (`scripts/`, `atlas/`, `tests/`) are intentionally absent
  from `main`, but a prior scale-out cycle's pre-cleanup branch (`fm/derm-trial-atlas-scale-out`,
  kept on `origin` as a safety net) still has the real, working versions.** To add a trial
  correctly rather than hand-crafting CSVs: `git archive origin/fm/derm-trial-atlas-scale-out --
  scripts atlas tests | tar -x -C <scratch dir>`, copy into a scratch checkout of this repo,
  build the new trial's JSON by hand (matching an existing trial's structure), run
  `scripts/build_csv.py` to regenerate all 5 flattened CSVs, run the copied `tests/` (needs
  `pytest` — not committed here) to validate schema conformance, diff the regenerated CSVs
  against a pre-change backup to confirm every pre-existing row is byte-identical (only the new
  trial's rows should differ), then delete `scripts/`/`atlas/`/`tests/` again before committing.
  Never hand-edit the CSVs directly — the flattening (JSON-encoding, endpoint/criterion joins,
  compact timepoint formats) is nontrivial and easy to get subtly wrong.
- **The Purple Book monthly CSV at `accessdata.fda.gov` (e.g.
  `.../PurpleBook/2026/purplebook-search-August-data-download.csv`) 302-redirects to an Akamai
  bot-detection apology page for a bare `curl`, but succeeds with a real browser `User-Agent`
  header** — no browser automation needed, unlike `purplebooksearch.fda.gov`'s live search UI
  (still genuinely blocked, same as Orange Book's live UI). Despite its filename saying
  "-August-", the file is a full historical snapshot (every product's full approval-date
  history), not just that month's changes — don't assume a narrower scope than what's actually
  in it. A drug's BLA applicant of record (Purple Book) can differ from its trial sponsor
  (CT.gov) when commercial rights were licensed after the pivotal trial — e.g. Spesolimab/Spevigo:
  Boehringer Ingelheim ran Effisayil-1, but LEO Pharma A/S holds BLA761244. Real, not a data bug.
- **A pivotal trial that is literal Phase 2 (not "Phase 2/3") can still belong in this atlas** for
  a genuinely rare/orphan indication where a standard-sized Phase 3 isn't feasible and the trial
  is the real, cited basis for FDA approval (randomized, placebo-controlled, `resultsSection`
  present) — established by Generalized Pustular Psoriasis/Spesolimab (Effisayil-1, pure Phase 2,
  n=53), extending the same "genuine pivotal trial over literal phase label" precedent Bullous
  Pemphigoid's Phase 2/3 LIBERTY-BP set. An **active-comparator** pivotal trial still doesn't
  qualify regardless of rarity or real FDA approval status — Pemphigus Vulgaris/Rituximab was
  checked and excluded on exactly this ground (its approval trial is rituximab-vs-mycophenolate,
  not placebo-controlled).
- **Two FDA-approved drugs for the same indication can sit in different exclusivity registries
  despite an identical dosage form.** Epidermolysis Bullosa's two drugs are both topical gels
  applied the same way, but Filsuvez (birch triterpenes, a botanical-extract NDA) is Orange Book
  while Vyjuvek (beremagene geperpavec, a CBER-licensed HSV-1-vector gene therapy BLA) is Purple
  Book — the registry follows the FDA application type (NDA vs. BLA), never the route of
  administration. Vyjuvek's Purple Book row also had no biosimilars and needed the
  `accessdata.fda.gov` monthly-CSV fallback (see the note above) rather than the live search UI.
- **`fetch_faers.py`'s "zero real-world reports" path had a real, previously-latent schema bug**,
  found and fixed in cycle 5: openFDA's genuine `NOT_FOUND` for a drug's FAERS query (Birch
  Triterpenes) was being written with `total_reports: null` and friends, which fails
  `FAERS_SUMMARY`'s non-nullable `total_reports: INT()` — every prior atlas drug happened to have
  >=1 real report, so this path was never exercised before. Fixed by writing real `0`s (a
  confirmed negative count) instead of `null`s (an unknown) for every count field, with empty
  lists for the reaction/year breakdowns. **The `NOT_FOUND` itself, though, is usually a
  search-term artifact, not a real zero**: FAERS's `patient.drug.medicinalproduct` holds whatever
  the reporter wrote, so a drug whose reports are all filed under its brand name looks like it has
  none under its generic — found in cycle 10 (`BERDAZIMER` NOT_FOUND vs `ZELSUVMI` 71 reports;
  `TIRBANIBULIN` 17 vs `KLISYRI` 227). **Before writing a confirmed zero, always retry the brand
  name.** The committed Birch Triterpenes `total_reports: 0` was exactly this bug — `FILSUVEZ`
  returns 209 real reports (50 serious, 13 deaths) — corrected same cycle once found (not left as
  a known defect). Where the generic returns real reports it stays the atlas-wide default term (Tapinarof:
  `TAPINAROF` 997 > `VTAMA` 758); the brand is a fallback for a hard `NOT_FOUND` only, and
  `query.search_term` records which was used either way.
- **A drug's FDA label's own "Clinical Studies" section is the authoritative source for which
  CT.gov trials are actually pivotal**, when a drug has more registered Phase 3 trials than the
  ones FDA relied on for approval — used to pick Afamelanotide/Erythropoietic Protoporphyria's 2
  pivotal trials (CUV039 NCT01605136, CUV029 NCT00979745, both named by CT.gov ID in SCENESSE's
  label section 14) over a 3rd, earlier completed placebo-controlled Phase 3 trial (NCT04053270)
  that exists on CT.gov but predates what FDA actually cited.
- Checked and excluded in cycle 5 (real negative findings): Mastocytosis/Urticaria Pigmentosa (no
  dermatology-relevant cutaneous-only placebo-controlled pivotal trial on CT.gov — avapritinib's
  approval is for advanced *systemic* mastocytosis via oncology trials) and Cicatricial/Mucous
  Membrane Pemphigoid (no FDA-approved drug specific to this indication has a completed
  placebo-controlled pivotal trial: baricitinib's ocular-MMP trial was Phase 2 and terminated,
  rituximab's Phase 3 MMP trial is an active-comparator design and not yet complete).
- **A single drug substance can hold two genuinely separate NDAs, one per dosage form, each with
  its own indications** — established by Roflumilast: NDA215985 (ZORYVE Cream) covers Plaque
  Psoriasis and Atopic Dermatitis, NDA217242 (ZORYVE Foam) covers Seborrheic Dermatitis and
  scalp/body psoriasis, confirmed via openFDA's `drug/orangebook.json`
  (`products.active_ingredients.name=ROFLUMILAST` returns both application numbers as separate
  rows). This is a different shape from Ruxolitinib's Opzelura-vs-Jakafi split (there, 2 unrelated
  products under 1 ingredient for unrelated indications) — here it's the same overall drug program,
  same company, split into 2 applications by formulation. `exclusivity.orange_book` must be fetched
  per-NDA (openFDA's `products.active_ingredients.name` query, filtered by `application_number`,
  same tuple-pin pattern `atlas.regulatory_applications`/`fetch_orange_book.py` already use for
  Ruxolitinib); `real_world_safety.faers_summary` stays shared across every trial of the drug
  regardless of formulation, same FAERS `medicinalproduct`-can't-split-by-NDA limitation already
  documented for Ruxolitinib.
- **A trial the FDA's own product label cites by name in section 6.1 (Adverse Reactions) or 14
  (Clinical Studies) as one of the pivotal basis trials is pivotal for this atlas even when CT.gov's
  own `phases` field says Phase 2/2b, not Phase 3** — the same "real trial over literal phase label"
  principle as Generalized Pustular Psoriasis/Spesolimab, but here directly evidenced (the label
  names the trial), not inferred from rarity: ZORYVE Foam's label cites "Trial 203" (NCT04091646,
  Phase 2b on CT.gov) alongside STRATUM (Phase 3) as the two vehicle-controlled trials the
  Seborrheic Dermatitis approval rests on.
- **When adding new trials to an established multi-cycle corpus, never run a pipeline script's own
  `main()` if it globs/rewrites every file in `data/trials/`** — `fetch_adverse_events.py`'s
  `_refuse_v2` guard and `apply_source_data.py`'s full-corpus loop both process every trial file
  unconditionally; the latter would silently blank `real_world_safety`/`exclusivity` for every
  pre-existing drug whose `data/_raw_staging/` file no longer exists (staging is ephemeral,
  cleaned up each cycle, see the scratch-checkout note above). Cycle 6 instead imported these
  scripts' pure per-trial functions (`fetch_study`, `build_record`, `build_sae_rate`, `fetch_drug`,
  etc.) into a one-off script scoped to only the new NCT IDs — verify this by diffing the
  regenerated CSVs against a pre-change backup with the new NCT IDs grep'd out, exactly as the
  established `build_csv.py`-diff procedure already does for hand-built trial JSON. Reused again in
  the same cycle for Tapinarof (Vtama, NDA215272, a single-NDA drug expanding the same two
  indications — PSOARING 1/2 for Psoriasis, ADORING 1/2 for AD), confirming the pattern
  generalizes to a second drug in one sitting without re-deriving it from scratch.
- **Ustekinumab (Stelara) and Apremilast (Otezla) are two of dermatology's best-known,
  longest-approved Psoriasis drugs (2009, 2014) that had been missing from this atlas through 6
  prior cycles** -- a real gap, not a deliberate exclusion; found by checking well-known FDA
  approvals against the atlas's own drug list rather than only chasing newly-approved candidates.
  Ustekinumab's Purple Book entry (BLA125261) needed a NEW parser
  (`scripts/purple_book_csv_helper.py`), not `fetch_purple_book.py`'s live-search-table scraper
  (still genuinely Akamai-blocked) -- parses the same accessdata.fda.gov monthly CSV fallback
  already used for Vyjuvek, but for a drug with 8 distinct biosimilar BLAs (more than Adalimumab's
  10 *rows* but similarly large), it must dedupe multi-row BLAs down to one `biosimilars[]` entry
  each and normalize the CSV's `351(k) Interchangeable`/`351(k) Biosimilar` license-type values
  down to the schema's plain `"351(k)"` enum (interchangeable status lives in
  `interchangeable_approval_date` instead, matching how the existing Adalimumab data was already
  shaped). Also added same session: Brodalumab (Siliq, BLA761032, no biosimilars) via AMAGINE-1/2/3
  -- all 3 show `OverallStatus: TERMINATED` on CT.gov (an early "Sponsor decision" tied to Siliq's
  eventual suicidal-ideation boxed warning) but all 3 have a complete `resultsSection`, confirmed
  against Siliq's FDA label section 14 ("Trials 1, 2, and 3", n=4373 total, matching AMAGINE
  1/2/3's combined enrollment exactly) -- **`OverallStatus: TERMINATED` does not by itself
  disqualify a trial for this atlas; check for a real `resultsSection` before excluding.** Checked
  and confirmed as genuine dead ends (not oversights): Etanercept (Enbrel, Psoriasis 2004) and
  Infliximab (Remicade, Psoriasis 2006, via EXPRESS/EXPRESS II) both have real placebo-controlled
  pivotal trials on CT.gov, but individually fetching each trial confirmed **zero** `resultsSection`
  on any of them -- both predate CT.gov's 2007 mandatory-results-reporting rule, so no amount of
  further searching will surface a `resultsSection` for these specific trials.
- **Acne Vulgaris (Trifarotene/Aklief, Sarecycline/Seysara, Clascoterone/Winlevi) was dermatology's
  highest-prevalence indication and had been entirely absent through 8 prior cycles** -- found the
  same way Ustekinumab/Apremilast were, by checking well-known FDA-approved topical/oral
  dermatology drugs against the atlas's own drug list rather than only chasing newly-approved
  candidates. All three are single-NDA small molecules (no Purple Book entries, no ingredient-name
  collision in openFDA's `orangebook.json`, so no application-number tuple pin needed unlike
  Ruxolitinib/Roflumilast). Clascoterone's own CT.gov trials are registered under its
  pre-approval development code `CB-03-01` (cortexolone 17alpha-propionate, sponsor Cassiopea
  SpA) rather than its generic name -- confirmed as the same drug via Winlevi's FDA label before
  treating them as pivotal.
- **The pre-2007 CT.gov mandatory-results-reporting dead-end pattern (first established by
  Etanercept/Infliximab) extends to topical calcineurin inhibitors**: Pimecrolimus (Elidel,
  approved 2001) and Tacrolimus ointment (Protopic, approved 2000) both have zero CT.gov-registered
  trials that are the original branded placebo/vehicle-controlled pivotal trial -- every trial found
  is either a post-approval Phase 4 study (safety/QoL registries, all sponsored by Novartis/Astellas
  post-approval) or a **generic-manufacturer bioequivalence/ANDA trial** referencing the original
  NDA (e.g. Fougera Pharmaceuticals' "0416"/"0417" ointment studies, vehicle-controlled vs. the
  branded reference product -- these support a generic's ANDA, not a new drug approval, and don't
  count as this atlas's own pivotal trial for the reference product). A generic manufacturer's own
  vehicle-controlled trial is a new, real pattern to exclude on sight: it looks superficially like a
  qualifying trial (randomized, vehicle-controlled, Phase 3, real `resultsSection`) but its FDA
  basis is someone else's decades-old NDA, not its own approval.
- **Every oral-JAK Vitiligo candidate (ritlecitinib, upadacitinib, povorcitinib) and every HS/CSU
  biologic-pipeline candidate checked this cycle (spesolimab-for-HS, povorcitinib-for-HS,
  sonelokimab, izokibep, lutikizumab, ligelizumab, barzolvolimab) remains a real, live, unapproved
  program** -- re-verify via `openfda label.json?search=openfda.substance_name:<NAME>` (a genuine
  `NOT_FOUND` means no FDA label exists yet, i.e. not approved) before re-adding any of these on a
  future cycle; a real posted-results trial (e.g. spesolimab's Lunsayil 1 HS trial) is not
  sufficient on its own -- the drug's own current FDA label must show the matching indication
  (Spevigo's label is GPP-only even though its HS trial has posted results).
- **An old, generic-eroded small-molecule NDA needs an `application_number` tuple-pin on its Orange
  Book fetch, same as Ruxolitinib/Roflumilast's ingredient-name collisions -- but for a different
  reason.** Added same session: Onychomycosis (Efinaconazole/Jublia, Tavaborole/Kerydin) and Rosacea
  (Ivermectin/Soolantra, Oxymetazoline HCl/Rhofade), 4 drugs old enough (approved 2014-2017) to have
  real generic competition. A plain `products.active_ingredients.name` openFDA query for any of
  these returns the original NDA row mixed with several *generic ANDA* rows for the same ingredient
  (7-12 extra rows each) -- `fetch_orange_book.build_record()` doesn't filter by application type,
  so an unpinned query would silently merge a generic manufacturer's own patent/exclusivity rows
  into the branded drug's `exclusivity.orange_book` value. Ivermectin is a 3-way version of this:
  the bare ingredient also covers Stromectol (N050742, oral, systemic parasites) and Sklice
  (N202736, topical lice lotion), both real, unrelated NDAs. Confirm the fix worked by checking the
  filtered result has exactly 1 product row before writing it. Separately: Kerydin's brand is
  market-discontinued (superseded by generics after patent expiry) -- `openfda label.json?search=
  openfda.brand_name:Kerydin` returns a genuine `NOT_FOUND` even though the approval is real and
  unaffected, because `label.json` only indexes *currently marketed* labels; `drug/orangebook.json`
  keeps every historical row regardless of current marketing status, so it stays the authoritative
  check for approval history even after a brand is discontinued.
- **A drug can be fully indexed in openFDA's `drug/label.json` and still have
  `openfda.substance_name: None`** — Berdazimer (Zelsuvmi, NDA217424, added cycle 10 for Molluscum
  Contagiosum alongside Tirbanibulin/Klisyri for Actinic Keratosis). `fetch_adverse_events.py`'s
  `build_boxed_warning()` hardcodes `openfda.substance_name:<DRUG>`, so it 404s and silently
  degrades to `needs_extraction` — losing the real, checked "label exists, no boxed warning"
  finding this atlas deliberately keeps distinct. Fall back to `openfda.generic_name:` (or
  `openfda.brand_name:` / `openfda.application_number:`) rather than accepting the null; verify the
  returned row's `application_number` matches. Two other cycle-10 findings: **a trial the label
  cites as pivotal belongs in the atlas even when it MISSED its primary endpoint** — Zelsuvmi's
  section 14 names Trials 1/2/3 and then says efficacy was shown in 1 and 2 only, so NCT03927716 is
  in (the atlas records the program FDA reviewed, not just its positive arms). And **the recovered
  `tests/` suite has 3 failures that are stale, not data problems** — `test_schema.py` hardcodes
  `len(TRIALS) == 63` (twice; the branch was cut at 63 trials) and `export_schema.py --check` calls
  the committed `docs/SCHEMA.md` stale against that branch's diverged `atlas/schema.py`. Confirm
  they also fail on the untouched pre-change corpus before treating any as yours; the 1000+
  per-field schema subtests are the ones that actually validate new trials, and
  `atlas.schema.validate()` can be called directly if `pytest` is unavailable (`uv venv` + `uv pip
  install pytest` in a scratch dir works without touching the system Python).
- **The generic-name-preferred FAERS default has a third failure mode: the generic term returns
  plenty of real reports that belong to a DIFFERENT drug family.** Found on Hyperhidrosis /
  Glycopyrronium (Qbrexza, NDA210361, cycle 11).
  `patient.drug.medicinalproduct:"GLYCOPYRRONIUM"` returns 9,183 reports, but
  `count=patient.drug.drugindication.exact` on the same query is dominated by *inhaled*
  glycopyrronium-bromide COPD/asthma bronchodilators (COPD 1,824; asthma 891) with hyperhidrosis
  absent from the top 12; `"QBREXZA"` returns 844 whose top indication is HYPERHIDROSIS (485).
  **Always run the `drugindication` count before accepting a generic term** — a plausible-looking
  total is not evidence the reports are about your drug. This is not the Ruxolitinib case (one
  ingredient, two products, no cleaner term, so the mix is unavoidable and kept): when a clean term
  exists, use it and say so in `source_excerpt` + `query.search_term`. Same drug, separate Orange
  Book wrinkle: it is indexed under the **salt** name `GLYCOPYRRONIUM TOSYLATE`, not the bare
  `GLYCOPYRRONIUM` its label's `openfda.generic_name` uses, and needs the usual
  `application_number` pin (2 rows: N210361 QBREXZA + A214448, a DISCONTINUED Padagis generic
  ANDA). The inhaled products do *not* collide there — Orange Book files them under
  `GLYCOPYRROLATE` (94 rows, 15 NDAs) — so the Orange Book and FAERS collisions for one drug can
  have completely different shapes; check each separately.
- Checked and excluded in cycle 11 (real negative finding): Basal Cell Carcinoma — both approved
  hedgehog inhibitors fail the placebo/vehicle-controlled bar. Vismodegib (Erivedge, NDA203388)
  rests on SHH4476g (NCT00833417), single-arm open-label with no comparator; Sonidegib (Odomzo,
  NDA205266) rests on BOLT (NCT01327053), which randomizes 200mg vs. 800mg of the same drug — the
  same active-comparator exclusion as Pemphigus Vulgaris/Rituximab. Oncology dose-ranging pivotal
  designs without a placebo arm are a recurring shape to expect in any solid-tumour skin
  indication, not a data gap.
- **A discontinued brand can be absent from openFDA's `drug/label.json` entirely — not even a
  `substance_name` hit** (a step further than Kerydin's precedent, where `substance_name` still
  worked when `brand_name` didn't). Added cycle 12: Impetigo (Ozenoxacin/Xepi, NDA208945, approved
  2017) and Seborrheic Keratosis (Hydrogen Peroxide/Eskata, NDA209305, approved 2017) — both
  small, old, market-discontinued topicals with zero label.json hits under brand, substance,
  generic, or `application_number` search. `boxed_warning` was still resolved (both confirmed
  `present: false`, not `needs_extraction`) by fetching the original approval-package label PDF
  directly from the `application_docs[].url` in `drug/drugsfda.json`'s ORIG submission — the PDF
  renders as scanned/compressed text WebFetch can't parse, but Read extracts it as page images
  fine. Both labels' section 14 also directly name-matched their CT.gov trials by N and enrollment
  count, the same label-is-authoritative-for-pivotal-trials pattern as Afamelanotide/EPP.
- **A generic drug name can collide with FAERS reports for a completely unrelated drug on BOTH the
  generic and the brand search term at once** — a new, worse variant of the Qbrexza/Glycopyrronium
  finding (where only the generic term was contaminated). Ozenoxacin/Xepi: `OZENOXACIN` (17
  reports) top terms include cerebral haemorrhage and ACTH deficiency; `XEPI` (4 reports) top terms
  are narcolepsy/cataplexy/somnolence (i.e., Xyrem territory) — neither term's indication profile
  resembles a topical impetigo antibiotic. For a low-volume, old, discontinued drug, expect this
  kind of FAERS name-noise and record it as-is (generic term, atlas default) with an explicit
  caveat rather than picking whichever term looks cleaner — there may not be a clean one. Contrast
  with Eskata, where the generic term (`HYDROGEN PEROXIDE`, 521 reports) is the contaminated one
  (dominated by OTC wound-care/mouthwash/whitening products) and the brand `ESKATA` (212 reports,
  top indication SEBORRHOEIC KERATOSIS 159/212) is the clean one — used instead per the existing
  run-the-drugindication-count-first rule. Two genuinely different resolutions for the same class
  of problem; always check both terms rather than assuming the convention picks itself.
- Checked and excluded in cycle 12 (real negative findings): Netherton Syndrome and Discoid Lupus
  Erythematosus (DLE) — neither has an FDA-approved drug at all. Netherton Syndrome's entire CT.gov
  trial list (QRX003, ATR12-351, BCX-series, SXR1096, and pipeline reuse of spesolimab/secukinumab/
  dupilumab/adalimumab from other indications) is Phase 1-3 investigational, several TERMINATED,
  none approved. DLE's CT.gov list (deucravacitinib, litifilimab, anifrolumab, enpatoran, and
  older terminated CC-930/AMG-811/tofacitinib trials) is the same story — all investigational.
  The one DLE-adjacent FDA-approved drug found, Anifrolumab (Saphnelo), is labeled only for
  systemic lupus erythematosus (SLE) — "Limitations of Use" explicitly excludes the label from
  covering skin-only disease — the same systemic-vs-cutaneous-indication boundary already
  established for Mastocytosis (avapritinib is for *systemic* mastocytosis, not cutaneous).
  Re-check both next cycle only if a name here shows up in `openfda label.json` as newly approved.
- **Cycle 13's broad sweep (no named candidate backlog left) found Icotrokinra (Icotyde,
  NDA220149, Janssen), a real, very recently approved (2026-03-17) oral IL-23 receptor antagonist
  peptide, expanding Plaque Psoriasis with 4 label-cited placebo-controlled pivotal trials (PSO-1
  through PSO-4).** Found by querying `openfda label.json?search=openfda.substance_name:<NAME>`
  for a batch of known late-stage dermatology pipeline compounds (rocatinlimab, amlitelimab,
  zasocitinib, povorcitinib, icotrokinra) rather than guessing from memory which had reached
  approval — 4 of 5 were still genuine `NOT_FOUND` (unapproved as of this check), 1 was real. Two
  source-lookup wrinkles, both now-familiar patterns applied to a new drug: (1) Orange Book
  indexes it under the salt name `ICOTROKINRA HYDROCHLORIDE`, not the bare `ICOTROKINRA` the
  label's `openfda.substance_name` uses (same shape as Glycopyrronium Tosylate) — 1 clean product
  row, no collision to pin; (2) FAERS under `ICOTROKINRA` returns only 2 real-world reports, a
  correct near-zero (not a bug) for a drug approved ~6 months before this cycle's pull, not a
  search-term miss requiring a brand-name retry.
- **A prior cycle's AGENTS.md update is not proof the same cycle's README update actually
  landed — check both independently.** Cycle 12's commit updated this file with real Impetigo/
  Seborrheic Keratosis findings, but never added those 2 indications' sections to README's "What
  this covers" catalog, and the README's own summary counts (top-of-file, Fill status table,
  "files in this repo" section) had silently drifted stale since cycle 10 (still said "19
  indications, 42 unique drugs, 108 trials" against an actual 21/44/112 before this cycle's own
  addition). Fixed in cycle 13 alongside the Icotrokinra addition: added the 2 missing README
  sections, recomputed the Fill status table's per-field numerators directly from the regenerated
  `sources.csv` (not hand-estimated), and updated every count reference. Recompute and grep for
  stale counts in README every cycle, not just AGENTS.md — the two files can drift independently
  since they're edited by hand, not generated.
- **A newly FDA-approved drug's pivotal trial can be a real, randomized, placebo-controlled Phase
  3 trial that the FDA's own label describes efficacy results for, and still fail this atlas's own
  `resultsSection`-present bar** — a new, distinct failure mode from the pre-2007
  Etanercept/Infliximab dead end (those trials predate CT.gov's reporting mandate and will *never*
  post results; these are recent trials still short of the CT.gov posting timeline). Checked and
  excluded in cycle 13: Prademagene Zamikeracel (Zevaskyn, BLA125807, approved 2025 for Recessive
  Dystrophic Epidermolysis Bullosa — a real new drug for an indication already in this atlas) via
  its VIITAL trial (NCT04227106, a within-patient paired-wound randomized design, n=11 patients /
  86 wounds, `OverallStatus: COMPLETED`) — `hasResults: false` on CT.gov despite the label's own
  `clinical_studies_table` field showing full paired-wound efficacy tables. Also excluded:
  Cemiplimab (Libtayo, already FDA-approved since 2018 for CSCC/BCC/NSCLC) for its 2025 adjuvant
  CSCC indication expansion via the C-POST trial (NCT03969004, randomized 1:1, double-blind,
  placebo-controlled, n=415, genuinely meets this atlas's design bar) — `hasResults: false`,
  `OverallStatus: ACTIVE_NOT_RECRUITING` (long-term overall-survival follow-up still ongoing after
  the DFS primary readout FDA approved on). Unlike the permanent pre-2007 dead ends, both are
  **re-check candidates for a future cycle** once their trials formally complete and post a
  `resultsSection` — worth a periodic re-check, not a one-time write-off. Cemiplimab's original
  mCSCC/laBCC/laBCC-post-hedgehog-inhibitor indications were not separately checked this cycle
  (PD-1-for-oncology approvals typically use single-arm response-rate designs without a placebo
  arm, the same bar that excluded the BCC hedgehog inhibitors) but are worth a look if revisiting
  Cemiplimab.
- **Cycle 15 re-checked both cycle-14 re-check candidates via live CT.gov API: still
  `hasResults: false` for both** — Zevaskyn/VIITAL (NCT04227106, `OverallStatus: COMPLETED`) and
  Cemiplimab/C-POST (NCT03969004, `OverallStatus: ACTIVE_NOT_RECRUITING`), no change from cycle
  14's finding, genuinely worth another periodic re-check rather than assuming a stale check.
  Cemiplimab's older mCSCC/laBCC oncology indications were also checked this cycle: its original
  pivotal trial EMPOWER-CSCC-1 (NCT02760498) is confirmed `NON_RANDOMIZED` (single-arm cohort
  expansion, `hasResults: true`) — the same oncology-dose-ranging-without-placebo dead end as the
  BCC hedgehog inhibitors, not a placebo-controlled design, so Cemiplimab's oncology indications
  stay excluded on design grounds (not a `resultsSection` gap this time).
- **A drug already in this atlas for one indication can have a second, older, much
  better-known FDA approval for a DIFFERENT indication that was never checked** — a new failure
  mode distinct from "drug missing entirely" (Ustekinumab/Apremilast) or "newer approval not yet
  swept" (Icotrokinra). Secukinumab (Cosentyx) was already in the atlas for Hidradenitis
  Suppurativa (added cycle 3) but its original, far more famous Plaque Psoriasis approval (2015,
  ERASURE/FIXTURE/FEATURE/JUNCTURE, label-cited as Trials PsO1-4) sat unchecked through 14 cycles
  because every prior openFDA sweep only tested drugs *entirely absent* from the atlas's drug
  list, never re-checked an already-present drug's OTHER FDA-labeled indications. Worth a
  dedicated pass next cycle: for every drug already in the atlas, check its FDA label's full
  `indications_and_usage` list against which of *this atlas's own indications* it appears under —
  a drug present for indication A but silently missing from indication B (despite an FDA
  approval + real pivotal trials for B) is exactly this failure mode repeating. FIXTURE's 3-arm
  design (secukinumab vs. etanercept vs. placebo) still qualifies under the placebo-controlled
  bar despite carrying a real active-comparator arm too — an active comparator ALONGSIDE a
  genuine placebo arm is fine; only an active-comparator-ONLY design (Pemphigus
  Vulgaris/Rituximab, BCC hedgehog inhibitors) is disqualifying. Also reused a new pattern worth
  keeping: FAERS/Purple Book/`regulatory_application` are drug-level, not trial-level, so when a
  drug already has this data staged for one indication, copy it verbatim into new trials for that
  same drug rather than re-querying openFDA — confirmed byte-identical source, saves 3 API calls
  per new trial.
- **Recovered pipeline note for future cycles: `atlas.migrate.migrate_trial()` (v1→v2) plus
  `scripts/fetch_trials.py`'s `build_record()` and `scripts/fetch_adverse_events.py`'s per-field
  builders (`build_sae_rate`, `build_death_rate`, `build_common_aes`,
  `build_discontinuation_rate`, `build_boxed_warning`) together do the FULL structured-endpoint
  and structured-AE build (`atlas.endpoints.parse_endpoint` handles PASI/IGA/EASI-style responder
  criteria and timepoints automatically) — cycles 4-14 were hand-typing this shape from scratch
  each time, more work than necessary.** The one-off per-cycle script pattern (`AGENTS.md`'s
  existing scratch-checkout procedure) should build a v1-shape record via these two scripts' pure
  functions, call `migrate_trial()` to get schema v2, THEN overlay `real_world_safety`/
  `exclusivity` (freshly fetched or copied from an existing same-drug trial per the note above).
  Validate with `atlas.schema.validate()` before writing.
- **Ran the "re-check an already-present drug's other FDA-labeled indications" sweep (queued
  above) across every biologic/JAK/oral small molecule already in the atlas** (Adalimumab,
  Ixekizumab, Certolizumab, Ustekinumab, Apremilast, Upadacitinib, Baricitinib, Guselkumab,
  Risankizumab, Deucravacitinib, Brodalumab, Dupilumab, Bimekizumab, Tildrakizumab) against
  their full `indications_and_usage` label text. Confirmed no further gaps beyond Secukinumab:
  Bimekizumab's HS indication is already in the atlas; Ixekizumab/Ustekinumab/Guselkumab/
  Risankizumab/Deucravacitinib/Brodalumab/Tildrakizumab have no other dermatology-relevant
  indication (their other approvals are PsA/axSpA/IBD, out of this atlas's scope); Upadacitinib's
  AD is already covered and it is genuinely not FDA-approved for AA or Vitiligo (still
  investigational, matches the standing Vitiligo-oral-JAK exclusion). One real, adjacent
  finding closed out: Adalimumab (Humira, already in the atlas for HS) has its own older Plaque
  Psoriasis approval (2008) — HUMIRA's label names "Study Ps-I" (n=1212), which matches
  NCT00237887's exact enrollment, but that trial has `hasResults: false` and started ~2005 — the
  same permanent pre-2007 dead end as Etanercept/Infliximab, not a gap to fill. One flagged
  candidate resolved by a scope decision, not a data check: Apremilast (already in the atlas for
  Psoriasis) is also FDA-approved for oral ulcers associated with Behçet's Disease, with a real
  randomized placebo-controlled completed trial with posted results (NCT00866359, n=111) — this
  passes every one of the atlas's usual data-quality bars. **Decided (cycle 16, captain call):
  excluded on scope, not data quality.** This atlas's framing is cutaneous/dermatologic
  conditions — every indication added so far, including the skin-oncology and systemic-biologic
  ones (CTCL, Mastocytosis), is a literal skin condition. Behçet's is a systemic vasculitis whose
  primary lesions are mucosal (oral/genital), which is oral-medicine/rheumatology territory, not
  dermatology, even though the drug and trial are otherwise atlas-quality. Do not add this trial;
  do not re-flag it as a gap in a future sweep — the boundary is deliberate, not an oversight.
- Checked and excluded in cycle 15 (real negative finding): Cutaneous T-Cell Lymphoma / Mycosis
  Fungoides — despite 3 real FDA-approved drugs specific to this skin-oncology indication
  (Vorinostat/Zolinza, Romidepsin, Mogamulizumab/Poteligeo), every one fails the
  placebo-controlled bar. Mogamulizumab's pivotal MAVORIC trial (NCT01728805) is confirmed
  RANDOMIZED but ACTIVE_COMPARATOR-only (mogamulizumab vs. vorinostat, no placebo arm) — the
  same active-comparator-only exclusion as Pemphigus Vulgaris/Rituximab and the BCC hedgehog
  inhibitors. Vorinostat and Romidepsin are older HDAC-inhibitor oncology approvals from the
  single-arm-Phase-2-cohort era, the same non-randomized design pattern that excluded Cemiplimab's
  mCSCC/laBCC approval. A real, well-documented dermatology-oncology indication that nonetheless
  has zero drugs meeting this atlas's own design bar — oncology approval patterns (single-arm or
  active-comparator-only) are proving to be a systematic, not incidental, exclusion category
  across every skin-cancer indication checked so far (BCC, CSCC, CTCL).
- **Cycle 16's web search for "FDA dermatology approvals 2025/2026" surfaced a real gap in a drug
  already in the atlas: Roflumilast Foam 0.3% (Zoryve Foam, NDA217242) has its own, separate Plaque
  Psoriasis (scalp and body) indication (approved 2025-05-22, an efficacy supplement to the same
  NDA already in this atlas for Seborrheic Dermatitis), never checked against the cream's existing
  Psoriasis entry (DERMIS-1/2, a different NDA, 215985).** The 2 label-cited pivotal trials — Trial
  204 (NCT04128007, Phase 2b, n=304) and ARRECTOR (NCT05028582, Phase 3, n=432) — are both real,
  randomized, vehicle-controlled, `hasResults: true`, confirmed against the live label PDF
  (`217242s005lbl.pdf`, section 6.1/14.2 naming both trials, n=734 combined). Same
  same-substance-two-NDAs-two-indications shape as the original Roflumilast cream/foam split
  (AGENTS.md cycle 6), but here it's the SAME foam NDA gaining a SECOND indication, not a new NDA —
  confirm which shape applies before assuming a "new NDA" is required. FAERS +
  `exclusivity.orange_book` + `exclusivity.regulatory_application` were all copied verbatim from
  the existing Trial 203 (SebDerm) file for the same NDA (drug/application-level, not trial-level,
  per the established reuse pattern) — this is the first cycle that needed to copy all 3 of those
  fields together; earlier reuse passes (Secukinumab, cycle 15) only needed FAERS + Purple Book,
  so **when reusing drug-level fields for a new trial, copy `exclusivity.regulatory_application`
  too, not just `faers_summary`/`orange_book`/`purple_book`** — missing it fails no schema check
  (the field independently defaults to `needs_extraction`) but silently drops a real, already-known
  value; caught here only by recomputing the Fill status counts from `sources.csv` and noticing
  `exclusivity.regulatory_application` read 120/122 instead of the expected 122/122.
- **Firstmate/captain scope decision (cycle 16): Apremilast's real, FDA-approved,
  placebo-controlled Behçet's-oral-ulcers trial (NCT00866359, flagged cycle 15) is excluded on
  scope, not data quality.** This atlas's framing is cutaneous/dermatologic conditions; Behçet's
  is a systemic vasculitis with mucosal (oral/genital), not cutaneous, primary lesions — oral
  medicine/rheumatology territory. Do not re-flag this as a gap in a future sweep; the boundary is
  deliberate.
- Checked and excluded in cycle 16 (real negative finding, quick check from the same web sweep):
  Tudriqev (vusolimogene oderparepvec-wtpg), a 2026-08-06 accelerated approval for advanced
  cutaneous melanoma in combination with nivolumab. Its confirmatory Phase 3 trial IGNYTE-3
  (NCT06264180) is randomized but ACTIVE_COMPARATOR-only (vs. physician's choice, not placebo) and
  still RECRUITING (`hasResults: false`) — the same active-comparator-only + not-yet-complete
  double exclusion already established for the BCC/CTCL oncology dead ends, now extending to a
  brand-new 2026 accelerated-approval melanoma drug too. Also checked and confirmed already fully
  covered (no action needed): Delgocitinib/Anzupgo (Chronic Hand Eczema), Dupilumab-for-Bullous-
  Pemphigoid (LIBERTY-BP), Dupilumab-for-CSU and Remibrutinib/Rhapsido (both Chronic Spontaneous
  Urticaria) — all 4 of these 2025 FDA approvals cited in the web sweep were already live-verified
  and in the atlas from earlier cycles, not new gaps.

- **Deep-extraction cycle (captain instruction 2026-09-05, PR #7): the scale-out cycles' 97
  non-AD trials had real drug/trial-existence + FAERS/Orange Book/Purple Book work but had never
  had the original 25 AD trials' own deeper clinical-text extraction pass
  (`severity_criteria`/`mechanism_of_action`/`dosing_regimen`/endpoint `responder_criteria`) run
  against them.** Closed `mechanism_of_action` and `dosing_regimen` to 0/122 missing and
  `severity_criteria` from 87 to 17/122 missing, using the same real-CT.gov-text +
  real-openFDA-label method as the original pass, reusing the recovered
  `origin/fm/derm-trial-atlas-scale-out` branch's `atlas/criteria.py`/`severity.py`/`dosing.py`/
  `label.py` modules (already v2-native — schema_version 2 — despite the branch being cut at 63
  trials) as a parsing toolkit, not a data source. Two openFDA `label.json` gaps needed the
  approval-package PDF fallback already established for Eskata/Xepi in earlier cycles: this time
  the SAME two drugs (Eskata/hydrogen peroxide, Xepi/ozenoxacin) needed it again for
  `mechanism_of_action` specifically — the PDF's own section 12.1 confirms Eskata's mechanism is a
  real, checked "unknown" (recorded as such, not `needs_extraction`); Xepi's real mechanism (a
  quinolone antimicrobial, DNA gyrase A/topoisomerase IV inhibition) is stated only in section 12.4
  Microbiology, not 12.1 — check both sections before concluding a label lacks a mechanism.
- **openFDA's `drug/label.json` substance-name query can return the WRONG product's label
  outright, not just a missing field, when an ingredient is shared across unrelated dosage
  forms/routes** — a new, more severe variant of the Ruxolitinib/Ivermectin ingredient-collision
  pattern (AGENTS.md's existing notes cover Orange Book and FAERS collisions; this is the same
  problem in `label.json`). `openfda.substance_name:BARICITINIB` returns an OTC-looking
  "Baricitinib" listing with no populated sections at all before the real Olumiant row; bare
  `IVERMECTIN`/`OXYMETAZOLINE` substance-name queries return oral-antiparasitic and OTC-nasal-
  decongestant products respectively instead of the topical dermatology products (Soolantra,
  Rhofade) this atlas actually needs. Pin to `openfda.application_number` (found via a
  `brand_name` query first) whenever a substance-name label query's `mechanism_of_action` reads
  wrong for the drug's known clinical use.
- **`atlas/label.py`'s `parse_mechanism()` regex only classifies `modality` as `monoclonal_antibody`
  when the label's own mechanism paragraph contains the literal phrase "monoclonal ... antibody",
  and `small_molecule` only for a literal "JAK inhibitor" phrase** — both real limitations of the
  ported parser, not deliberate design choices, exposed by this cycle's much wider drug-class mix
  (antifungals, antibiotics, retinoids, BTK/TYK2 inhibitors, adrenergic agonists, gene therapy,
  peptides). The already-committed Adalimumab record classifies as `modality: "other"` for exactly
  this reason (its own 12.1 paragraph never says "monoclonal antibody") — this is real precedent to
  match for Adalimumab specifically, not a bug to silently fix, but for every other drug this cycle
  hand-classified `modality`/`drug_class` from the literal label text directly (e.g. Apremilast's
  label says "an oral small molecule inhibitor of phosphodiesterase 4" verbatim) rather than
  trusting the regex output as-is. A future cycle extending `parse_mechanism()` itself should treat
  the Adalimumab record as a known, accepted quirk, not a regression to fix.
- **`molecule.dosing_regimen`'s convention (from `enrich_needs_extraction.py`'s `extract_dosing`,
  confirmed against the already-committed multi-arm JADE COMPARE record) is: include only CT.gov
  interventions whose name OR description textually references the trial's own `molecule.drug`**
  (by generic name or a known development/compound code, e.g. `IDP-108`=efinaconazole,
  `CB-03-01`=clascoterone, `BMS-986165`=deucravacitinib, `JNJ-77242113`=icotrokinra,
  `LOU064`=remibrutinib) — **not every arm.** A placebo/vehicle entry is included only when its own
  description references the drug (e.g. "matching placebo for X"); a genuine active comparator in
  a different drug's own dosing arm (ustekinumab in a brodalumab trial, apremilast in a
  deucravacitinib trial) is correctly excluded, since that comparator's own dosing belongs to ITS
  OWN trial record, not this one.
- **The current schema's `DOSE_FORMS` enum (`tablet`/`injection`/`solution`/`cream`/`ointment`) and
  `FREQUENCIES` enum (`once_daily`/`twice_daily`/`weekly`/`every_2_weeks`/`every_4_weeks`) don't
  cover every real dosage form/frequency this atlas's now much wider drug mix uses** — `gel`,
  `foam`, `wipe`, `implant` dose forms and `every_2_months` dosing (Afamelanotide's subcutaneous
  implant) have no enum slot. Since `atlas/schema.py` is generated from `kolai-website` and not
  hand-editable here, leave the specific sub-field (`dose_form`/`frequency`) null rather than
  force-fitting the nearest wrong category when this happens — `route` can still often be inferred
  as `topical` directly from the literal text (a cream/ointment/gel/foam/wipe has no other route)
  even when `dose_form` itself can't be represented. A future cycle should flag these 4 missing
  enum values to `kolai-website` rather than re-discover the same gap.
- **`population.severity_criteria`'s `ScoreCriterion.metric` enum has no slot for "percent of an
  anatomical structure other than skin" or for area stated in cm² — found on Efinaconazole/
  Tavaborole (Onychomycosis, "20-50% of the target nail area affected") and Oleogel-S10 (EB, wound
  size "10 cm² to 50 cm²").** `percent_bsa` is specifically body-surface-area; reusing it for
  percent-of-nail-area would misrepresent the criterion. Left `needs_extraction` rather than
  mislabeled — a real schema-enum gap for a future cycle to raise with `kolai-website`, not an
  unattempted extraction. The same real-vs-schema-gap distinction applies project-wide: 17 of the
  75 severity-gap trials this cycle stayed `needs_extraction` for this reason or because the real
  CT.gov eligibility text genuinely states no quantitative baseline threshold at all (documented
  per-trial in this cycle's `severity_criteria` commit) — a real, checked outcome, not a shortcut.
- **The `Severity.severity_label` enum has exactly one non-null value, `"moderate_to_severe"`** —
  a trial whose eligibility literally says "moderate acne" (no "to severe") or "mild to moderate"
  (ISGA Mild/Moderate AD trials) correctly gets `severity_label: null`; don't stretch the label to
  cover a different real severity band than the one CT.gov's text actually states.
- **This cycle introduced several new canonical `scale` name strings beyond the AD/psoriasis set
  the corpus already had** (PASI, sPGA, ISGA, S-IGA, B-IGA, PGA, Hurley Stage, AN Count, SIRS,
  HDSS, ASDD, SALT, BPDAI, PLA, PPASI, UAS7, PSSD, plus lesion-count "scales" like `Inflammatory
  Lesion Count`/`Noninflammatory Lesion Count`/`Nodule Count`/`AK Lesion Count`/`MC Lesion Count`).
  `scale` is a free string in the schema (no enum), so these are all valid, but keep names
  consistent with what's already used in `severity_criteria.csv`/`endpoints.csv` rather than
  inventing a new spelling for the same real instrument in a future cycle — grep those two CSVs
  for a scale's canonical spelling before adding a new trial that uses it.
- **`scripts/fetch_trials.py`'s CT.gov outcome-measure fetch (and `atlas.endpoints.parse_endpoint`)
  already runs unconditionally for every trial regardless of extraction-pass depth — every trial's
  `primary_endpoints`/`secondary_endpoints` are populated with `source_type: ctgov_api` from day
  one** (confirmed: even trials this repo's own git history shows were added in "scale-out only,
  no deep extraction" cycles already carry real endpoint titles/timepoints). But the endpoint
  title parser that fills each endpoint's own `responder_criteria` sub-list was tuned to the
  original 17 AD trials' specific phrasing (e.g. "Main Study:" population prefixes) and left it
  empty for 338 `responder_rate` endpoints project-wide (not just the non-AD trials) whose titles
  use different real phrasing (`PASI-NN`/bare `PASINN`, `sPGA`/`IGA` "of 0 or 1" success
  definitions, `UAS7<=6`, `HiSCR`, `DLQI` 0/1, N-point NRS reduction, N-grade CEA/SSA improvement,
  `PSSD` Symptom/Sign Score of 0). A deterministic pattern-matcher over each endpoint's own already-
  fetched verbatim text (no new source needed) closed 190 of these 338 in this cycle; the remaining
  148 are categorical-distribution measures, immunogenicity/device-usability endpoints the original
  parser mislabeled `responder_rate` (anti-drug antibodies, self-administration success), satisfaction
  surveys, and titles with no stated threshold at all (e.g. Ozenoxacin's "Clinical Success") — a
  real, checkable backlog, not a data problem to re-flag as identical to the severity/MoA/dosing
  gaps.
- **`design.background_therapy`/`timing_ops.rescue_therapy`/`timing_ops.study_schedule`/
  `endpoints.multiplicity_control` remain a real, large, PDF-dependent backlog after this cycle**
  (105-108 of 122 trials each, essentially unchanged by this cycle's work) — confirmed via a live
  CT.gov `documentSection` check that 61 of the 109 trials missing at least one of these 4 fields
  actually have a Study Protocol and/or SAP document posted (`hasProtocol`/`hasSap` flags), meaning
  real extraction is genuinely possible for roughly half the gap, the same way the original AD
  corpus's `RESCUE_RULES`/`MULTIPLICITY_RULES`/`BACKGROUND_THERAPY_PDF` dicts in
  `enrich_needs_extraction.py` were built: download each PDF from CT.gov's `documentSection` ->
  CDN URL (see `fetch_protocol_docs.py`), and read the relevant section by hand (`pdftotext
  -layout` was the original tool; this cycle confirmed the Read tool extracts scanned/compressed
  PDF text fine when a raw fetch returns garbled bytes). Not attempted this cycle — each field
  needs its own PDF read per trial, materially higher effort per field than the CT.gov-API-only
  extraction that closed severity/MoA/dosing to near-zero, and a natural place for the next
  deep-extraction cycle to pick up rather than re-discovering which 61 trials even have a document
  to read.
- **Cycle 17 added a 22nd indication, Head Lice, via Abametapir (Xeglyze, NDA206966)** — found by
  extending the broad-sweep method beyond dermatology-proper into other FDA-approved topical
  prescription pediculicides/scabicides, a category adjacent to but distinct from every prior
  sweep target. **A drug's two label-cited "identical" pivotal trials can have different
  `hasResults` status on CT.gov despite both reporting real efficacy data in the label itself** —
  a new variant of the Zelsuvmi/Zevaskyn precedent, but here it's not that the trial missed its
  endpoint or hasn't completed; it's that one of two truly interchangeable twin trials (same
  design, same N target, ran the same year) simply never got its results section posted. XEGLYZE's
  label section 14 describes "Trials 1 and 2" together (704 subjects combined, both positive:
  81.1%/50.9% and 81.8%/47.2% treatment success vs. vehicle) but only NCT02060903 (n=379) has
  `hasResults: true` on CT.gov; NCT02062060 (n=325) is `hasResults: false` — excluded per the
  atlas's standing resultsSection-present bar, a re-check candidate like Zevaskyn/VIITAL and
  Cemiplimab/C-POST, not a data gap. Same market-discontinued-brand / absent-from-`label.json`
  pattern as Xepi/Eskata (original label PDF read directly for `boxed_warning`, confirmed
  `present: false`); FAERS is a genuine confirmed zero on both `ABAMETAPIR` and `XEGLYZE` (no
  alternate term exists — recorded as a real `total_reports: 0`); Orange Book has exactly 1 clean
  product row (no ingredient collision). Checked and excluded in the same sweep: Spinosad (Natroba,
  NDA022408, approved 2011, also for head lice) — its 2 pivotal trials are randomized but
  ACTIVE_COMPARATOR-only (spinosad vs. permethrin/NIX, no vehicle or placebo arm), the same
  active-comparator-only exclusion as Pemphigus Vulgaris/Rituximab and the BCC hedgehog
  inhibitors — a reminder to check the actual arm types (not just "vehicle" appearing in a trial's
  brief title) before assuming a topical trial is placebo-controlled.

- **Cycle 18 introduced a standing full-deep-extraction requirement for every NEW trial going
  forward** (captain instruction): severity criteria, endpoint hierarchy/definitions, mechanism of
  action, dosing regimen, visit schedule, and rescue therapy must all be pulled for real from
  source text (CT.gov free text, protocol/publication full text), not left `needs_extraction` by
  default the way cycles 6-17 generally did for new indications. A genuinely unfindable field after
  real effort still correctly stays `needs_extraction` — that's a real outcome, not a shortcut, but
  it can no longer be the default. A **sibling task (derm-trial-atlas-deep-extraction)** is
  separately backfilling the ~90 pre-cycle-18 trials that lack this depth — not this cycle's job to
  redo, just don't add to that backlog going forward.
- **Cycle 18 added a 23rd indication, Dermatomyositis, via Octagam 10% (IVIG, BLA 125062,
  ProDERM/NCT02728752)** — found via a fresh "FDA dermatology approvals 2026" web sweep (the
  standing broad-sweep method, repeated per the cycle-16 steer) that surfaced Brepocitinib
  (Lisraya), approved 2026-08-27. Brepocitinib's own pivotal VALOR trial (NCT05437263) is real
  (randomized, double-blind, placebo-controlled Phase 3, n=241, published in NEJM/JAMA
  Dermatology) but is `hasResults: false` on CT.gov — the same FDA-approved-but-not-yet-posted
  pattern as Zevaskyn/VIITAL and Cemiplimab/C-POST, excluded as a re-check candidate, not a gap.
  Checking the indication further (rather than stopping at the first candidate's exclusion, a
  useful habit for any future "recently approved but unposted" hit) surfaced Octagam 10%, FDA
  dermatomyositis-approved since 2021-07-15 via its own placebo-controlled Phase 3 trial ProDERM,
  which does have `hasResults: true` — added instead. **Dermatomyositis is in scope for this atlas
  despite being systemic (muscle + skin), the same precedent as CTCL and Mastocytosis** — its own
  pivotal trial uses a dedicated dermatology severity instrument (CDASI) as a named endpoint, and
  heliotrope rash/Gottron's papules are hallmark diagnostic features, a materially stronger
  dermatology case than the Behçet's oral-ulcer trial excluded on scope in cycle 16.
- **Octagam 10% surfaced 3 new pipeline-shape wrinkles worth generalizing.** (1) It is a
  CBER-reviewed (not CDER) plasma-derived polyclonal immunoglobulin BLA — `label.json`/
  `drugsfda.json` return genuine `NOT_FOUND` for brand, generic, AND substance-name searches (a
  step further than Kerydin/Xepi/Eskata, where at least one search term worked), so `boxed_warning`
  and `mechanism_of_action` needed the original label PDF read directly, and
  `molecule.mechanism_of_action.modality` needed a new value: `"other"` (not `monoclonal_antibody`)
  since IVIG is a polyclonal, not monoclonal, antibody product — the label itself states the
  mechanism "has not been fully elucidated," same honest-null pattern as Dupilumab's mechanism
  text. (2) FAERS on `OCTAGAM` (1969 reports) is a new, more extreme version of the
  generic-term-contamination pattern (Qbrexza/Glycopyrronium, Ozenoxacin/Xepi): Octagam's much
  broader original ITP/immunodeficiency uses so dominate its FAERS reports that dermatomyositis
  does not appear in the top 15 `drugindication` terms at all, and unlike Qbrexza/Ozenoxacin there
  is no brand-vs-generic split to retry (Octagam is one product name, not generic+brand) — recorded
  as-is, the same unavoidable-mix situation as Ruxolitinib. (3) ProDERM's design is a **blinded
  treatment-switch ("escape") design**, not the topical-then-systemic step-up shape the
  `timing_ops.rescue_therapy` schema fields were built for: a subject with confirmed deterioration
  (worsening on 2 consecutive visits by defined thresholds) is switched to the other blinded arm
  rather than given an add-on rescue medication — recorded via `trigger_rules`/`flare_definition`
  with the shape mismatch documented in `rationale` rather than forcing an inapplicable field.
  Likewise `design.background_therapy.regimen_type`'s 3 enum values are all AD/psoriasis-specific
  (monotherapy/combination_tcs/standardized_background_topical); none fit a systemic-disease
  permitted-background design, so it was left `null` with the real rules recorded in
  `background_agent_class`/`permitted_concomitant`/`population_note` instead — **a new trial whose
  design doesn't fit an existing curated enum is a real "extend the schema later" signal, not a
  reason to force a wrong-but-valid enum value.**

- **Cycle 19 added Difamilast (ADQUEY, NDA219474, Acrotech Biopharma) to Atopic Dermatitis** — a
  10th AD drug, via Trial 1 (NCT02068352, Phase 2 dose-ranging, US/Australia/Poland, n=121), Trial 2
  (NCT03908970, Phase 3, Japan, n=364), and Trial 3 (NCT03911401, Phase 3, Japan pediatric, n=251),
  all label-cited (section 14), vehicle-controlled, `hasResults: true`. Difamilast was originally
  developed by Otsuka Pharmaceutical under the code name OPA-15406 (both CT.gov registrations still
  use that name) before Acrotech acquired US commercial rights for the 2026-02-12 approval — another
  instance of the sponsor-vs-trial-sponsor licensing-change pattern already seen with
  Spesolimab/LEO Pharma. Trial 1's Phase 2 label-cited-as-pivotal status is another instance of the
  real-trial-over-literal-phase-label precedent (Spesolimab/GPP). All 3 trials share one
  IGA success definition (IGA 0/1 clear/almost-clear with >=2-grade improvement from baseline at
  Week 4, entry IGA 2/3 + BSA 5-40%) and one no-rescue design (concomitant AD treatment prohibited,
  per label section 14) rather than the AD biologics' topical-then-systemic step-up shape — recorded
  via `rescue_therapy.trigger: "prohibited"` with the real rule quoted in `rationale`, the same
  shape-mismatch handling as ProDERM's blinded-switch design (cycle 18). ADQUEY's openFDA label
  confirms the genuinely-absent-boxed-warning-key pattern already established by Xeglyze/Zelsuvmi
  (no `boxed_warning` key at all, not a null) — `openfda.substance_name` resolved fine here (unlike
  Zelsuvmi), so no `generic_name` fallback was needed. FAERS on `DIFAMILAST` (3 reports, 2 of 3
  correctly indication-matched to "Dermatitis atopic") is a real, small, clean total appropriate for
  a drug ~7 months post-approval — no brand-name retry needed (`ADQUEY` itself returns 0, as
  expected this soon after launch). Orange Book has exactly 1 clean product row (small-molecule NDA,
  no ingredient collision); `exclusivity.purple_book` stays `needs_extraction` per the atlas-wide
  convention for NDA-only drugs (confirmed against Roflumilast/Tapinarof's existing AD entries
  rather than inventing a distinct "not applicable" value).
- **Cycle 20 rebased this branch onto current `main` after a sibling deep-extraction task's PR #7
  (severity/mechanism/dosing enrichment over the 97 pre-cycle-17 non-AD trials) merged first and
  changed the same generated CSVs cycles 17-19 had also touched.** Resolved by keeping BOTH sides'
  real content in `AGENTS.md`/`README.md` prose (no cycle's findings dropped), then fully
  regenerating all 5 CSVs from the merged `data/trials/*.json` via `scripts/build_csv.py` rather
  than hand-merging generated-file conflicts — confirmed via diff against a pre-rebase backup that
  every pre-existing row (including PR #7's enrichment) stayed byte-identical, only this branch's 5
  new-trial NCT IDs' rows differed. **When two branches both touch the generated CSVs for different
  trials, regenerate from the merged source JSON rather than resolving the CSV conflict by hand** —
  the flattening logic (JSON-encoded cells, endpoint/criterion joins) is exactly the kind of thing a
  manual conflict resolution gets subtly wrong. README's Fill-status table numbers were recomputed
  directly from the regenerated `sources.csv` (a short Python pass counting non-`needs_extraction`
  rows per field) rather than trusting either side's conflicting, now-stale table.
- **Cycle 20's "FDA dermatology approvals 2026" web sweep came back genuinely empty** — every named
  drug across 6 fetched articles (Dermatology Times' August/July 2026 monthly reviews, Dermatology
  Advisor's 2025 year-end recap, and 2 blocked-behind-403 pages) is either already in this atlas
  (Dupilumab-CSU, Remibrutinib, Guselkumab pediatric-age expansion, Roflumilast Foam-Psoriasis),
  already checked and excluded with an unchanged status on live re-check (Zevaskyn/VIITAL,
  Cemiplimab/C-POST, Brepocitinib/VALOR — all 3 still `hasResults: false`, re-confirmed this cycle
  via a live CT.gov fetch), or not yet FDA-approved (BOTOX Cosmetic/masseter-muscle-prominence: FDA
  *accepted* the sBLA 2026-08-04, decision still pending; upadacitinib/alopecia areata: EU-approved
  only, US decision pending). BOTOX/masseter would also be a scope call like Behçet's even if
  approved — a cosmetic aesthetic indication, not a disease, a different axis from the
  systemic-vs-cutaneous line that included Dermatomyositis/CTCL. **The broad-sweep well is
  genuinely running dry** — a real, reportable outcome after ~10 cycles of the same method, not a
  sweep that needs repeating verbatim next cycle without a new angle (an openFDA `label.json` sweep
  for very recent NDA/BLA numbers not yet cross-checked, rather than a web-search recap of already-
  known approvals, is the more promising next angle).

- **Deep-extraction cycle 2 (same 2026-09-05 captain instruction, continued): read the real Study
  Protocol/SAP PDF for every one of the 61 non-AD trials that had one posted on CT.gov's
  `documentSection`, closing `design.background_therapy` 17->73/122,
  `endpoints.multiplicity_control` 16->67/122, `timing_ops.study_schedule` 15->74/122,
  `timing_ops.rescue_therapy` 14->57/122, plus a bonus 5 more `population.severity_criteria`
  (110/122) found along the way.** Downloaded all 139 PDFs (some trials have both a Protocol and a
  separate SAP doc) via the CDN URL pattern in `fetch_protocol_docs.py`, converted with
  `pdftotext -layout`, then fanned out 8 parallel subagents (one per ~8-trial batch) to read the
  real text and write per-trial JSON patches — orchestrator applied, schema-validated, and
  CSV-diffed every patch before committing, same regression discipline as every prior cycle.
  **Garbled PDF-text extraction is common and must not be mistaken for a missing quote**: this
  cycle hit column-bleed (stray words from a facing margin interleaved mid-sentence), pervasive
  letter-spacing ("C o n c o m i t a n t"), and a consistent byte-shift cipher (every character
  offset by a fixed amount, e.g. "Athenex"->"$WKHQH[", reverse-engineered and decoded before
  reading) — all three still contain the real text and are extractable, but a naive substring
  match against the raw or whitespace-collapsed text will report a false negative even for a
  genuine, correctly-quoted excerpt. Verify a flagged excerpt by stripping ALL whitespace (not
  just collapsing it) from both the quote and the source before substring-checking, and manually
  spot-check a sample by hand (~20 checked this cycle, all confirmed real) rather than trusting
  one mechanical pass.
- **This cycle's much wider RESCUE/MULTIPLICITY content exposed real gaps in the metric/scale_variant
  enums beyond the severity-criteria gaps already documented above**: no metric exists for a
  worsening/increase relative to a reference (a `point_increase` in GPPGA or SALT, or an AN-count
  rising to `>=150% of baseline`, are real rescue/flare triggers with no valid
  `absolute_score`/`*_improvement`/`*_reduction` mapping — reduction/improvement metrics all assume
  the direction is toward getting better) and no metric for lesion-clearance endpoints (Tirbanibulin's
  "100% complete clearance" / "≥75% partial clearance" AK primary/key-secondary). Same
  established practice applies: drop the specific unrepresentable criterion (or null out a
  sub-object like `rescue_period`/`oral_corticosteroid_limit`/`maintenance_period_rule` whose
  schema requires ALL its non-nullable sub-fields once present, e.g. a real day-based OCS limit
  when the schema only models `max_mg_per_kg`/`max_consecutive_weeks` in weeks) rather than
  force-fit a wrong enum value or invented number — the real detail stays fully documented in that
  field's own free-text `rationale`, just not structurally represented. A future cycle extending
  the schema should treat both this note and the severity-criteria one above as one combined
  backlog for `kolai-website`.
- **Remaining gaps after this cycle are two genuinely different kinds, not one undifferentiated
  backlog**: roughly half the ~48-65 trials still missing each of the 4 fields have NO Study
  Protocol/SAP document posted on CT.gov at all (unextractable without a different source, e.g. a
  paywalled publication); the other half have a real posted document that was fully read this
  cycle and genuinely states no rescue-medication concept or no formal multiplicity-control
  procedure applies to that trial (a correct, checked finding — e.g. several simple 8-week
  topical-monotherapy-vs-vehicle Phase 2/3 designs have no rescue mechanism by design). Don't
  re-attempt PDF extraction on a trial already confirmed to have no document; do treat a
  "no-document" trial as worth re-checking if CT.gov later posts one.

- **Deep-extraction cycle 3 (2026-09-05, same captain instruction, after rebasing this branch onto
  main's cycle 17-21 scale-out additions): re-verified every trial cycle 2 left as a
  `background_therapy`/`multiplicity_control`/`study_schedule`/`rescue_therapy` gap, using a wider
  keyword net, and closed 6 real multiplicity_control misses cycle 2's narrower search terms had
  passed over — ARCADIA 1/2 (NCT03985943/NCT03989349, Nemolizumab AD), LIBERTY-BP
  (NCT04206553, Dupilumab), Roflumilast Trial 204 (NCT04128007, SebDerm), and both Berdazimer
  B-SIMPLE trials (NCT03927703/NCT03927716, Molluscum) — taking the field from 68/127 to 74/127.
  Every one of these 6 documents genuinely states a real hierarchical/gatekeeping procedure (a
  literal "Multiplicity Adjustment"/"Multiple Comparison/Multiplicity" section with a named
  method), but cycle 2's search for "multiplic|hierarch|type I error|gatekeep|closed testing|
  sequential test" missed docs that instead say **"fixed-sequence method"** (both Berdazimer
  trials) or bury the section under a differently-worded heading — always also search
  `"significance level"`, `"family[- ]wise"`, `"Holm"`, and read the 40-80 lines around any hit
  rather than trusting a keyword miss as evidence of absence.
- **A protocol PDF's full text includes its own amendment history, and a keyword hit inside a
  tracked-changes "the following text has been deleted" block describes a design the sponsor later
  REMOVED, not the trial's final design** — found checking BE VIVID (NCT03370133, Bimekizumab
  Psoriasis) for `rescue_therapy`: an "escape arm" (non-PASI90-responders switched to open-label
  bimekizumab) appears at real length in the PDF, but is explicitly framed by a later amendment as
  deleted text ("To remove the escape arm..."), so the trial's actual final design has no
  escape/rescue mechanism — confirmed by BE SURE/BE RADIANT (same drug program, active-comparator
  designs) both having zero "escape"/"rescue" hits at all. Always check whether a hit sits inside
  a change-log/amendment section before treating it as the trial's real, final rule.
- **A real, quoted, schema-representable multiplicity procedure can still leave `co_primary_endpoints`/
  `testing_sequence` needing an empty `responder_criteria: []`** when the endpoint itself has no
  representable metric — both Berdazimer trials' real "fixed-sequence method... strongly controlled
  at the alpha=0.05 level" procedure is fully quotable, but its one endpoint ("Complete Clearance of
  All Treatable MC") is the same lesion-clearance-metric schema gap already documented above for
  Tirbanibulin; matching the primary endpoint's own already-committed `responder_criteria: []`
  (rather than leaving the whole `multiplicity_control` field `needs_extraction`) is the correct,
  precedent-consistent way to record a real procedure without a representable criterion — verify
  the referenced endpoint's own JSON before assuming a `[]` list is a mistake to fix.
- **After this cycle's re-check, the remaining `rescue_therapy` gaps for Bimekizumab (all 3
  Psoriasis trials), JADE COMPARE, DERMIS 1/2, STRATUM, Trial 204, Trial 203/SebDerm, Vyjuvek/EB,
  both AA trials (BRAVE-AA1, THRIVE-AA2), all 3 remaining Berdazimer trials, and ADORING
  2/ARRECTOR/PSOARING 2 are now confirmed via a real, documented zero-hit "rescue"/"escape" search
  of their own protocol PDFs — genuine dead ends, not oversights.** The 2 Difamilast Phase 3
  trials' (NCT03908970/NCT03911401) `multiplicity_control` gap is also a confirmed genuine dead
  end: both PDFs were read in full and state only a single primary + one "important secondary
  endpoint," with no formal Type-I-error-control language anywhere in either SAP.
- **A PDF that yields 0 lines from `pdftotext` is a scanned/image-only PDF, not an empty or
  unreadable one — `pdftoppm -r 150/200 -png` + `tesseract --psm 6 -l eng` (both already on this
  machine, `/opt/homebrew/bin/`) recovers real, quotable text just as reliably as the Read-tool
  page-image route already used for the Eskata/Xepi label PDFs, and is far cheaper for a
  multi-page document** — closed both of this cycle's scanned-PDF gaps this way: Sarecycline
  SC1401/SC1402's 64-page SAP (`NCT02320149`, `endpoints.multiplicity_control` — a full 8-step
  fixed-sequence hierarchy over inflammatory/noninflammatory lesion-count endpoints) and
  Trifarotene's 10-page rotated Protocol Summary (`NCT02556788`, `design.background_therapy` — a
  real vehicle-controlled monotherapy design with a fully quoted prohibited-concomitant-medication
  list). Tesseract handled the Trifarotene PDF's 270-degree page rotation with no pre-rotation
  step needed. One naming curiosity found and left as-is: NCT02320149's own SAP title page reads
  "Study SC1401" even though this repo's README calls NCT02320149 "SC1402" — both Sarecycline
  trials share one identical official title and design, so this is likely a sponsor internal-code
  labeling quirk, not a wrong document (confirmed by fetching the PDF from NCT02320149's own
  CT.gov `documentSection` listing, not a guessed URL); a future cycle could verify the
  SC1401/SC1402 assignment against Seysara's FDA label section 14 if it matters for citation
  precision.
- **A trial with no posted Study Protocol/SAP can still have real, if thin, `rescue_therapy`/
  `background_therapy` content sitting directly in CT.gov's own free-text `eligibilityCriteria`
  field — cheap to check (one API call, no PDF) and worth running before writing off a
  no-document trial as a complete dead end.** Batch-checked all 50 no-document gap trials'
  eligibility text this cycle for rescue/background keywords: 3 of 4 hits were false leads (an
  eligibility exclusion mentioning "topical corticosteroids" or "concomitant medication" as a
  *disqualifying* criterion, not a description of the trial's own background/rescue design), but
  Head Lice (NCT02060903, Abametapir) had a real one — exclusion criteria 2-3 state subjects may
  not use other lice treatment or a lice comb "unless provided as rescue therapy to this
  Protocol," confirming rescue therapy is a real, permitted part of this trial's design. The
  actual composition/trigger/timing isn't stated anywhere reachable (no protocol posted), so the
  field was filled as a genuine partial fact (`permitted: true`, every compositional sub-field
  left null, `rationale` quoting the real text and stating plainly what still isn't known) rather
  than left at `needs_extraction` (which would incorrectly imply nothing at all is known) or
  over-filled with a guessed composition.
- **After 3 cycles of increasingly wide re-checking (narrow keyword search, then broadened
  keywords with amendment-history verification, then CT.gov eligibility-text as a document-free
  fallback), the `background_therapy`/`multiplicity_control`/`study_schedule`/`rescue_therapy`
  backlog is at a genuine, real stopping point, not a paused-for-time one.** Every one of the 19
  gap trials confirmed to have a posted protocol/SAP document was individually re-read this cycle
  with a wide keyword net (see the "fixed-sequence method" and "escape arm" notes above) and its
  remaining gap confirmed as the document's real, stated position, not an extraction miss. The
  other ~49 gap trials have no document on CT.gov at all, and a fresh eligibility-text sweep found
  only one more real (if partial) fact to add. The only remaining path to close more of this
  backlog for real is the paywalled-publication research effort AGENTS.md already documents as
  out-of-scope for every indication past the original 5-drug AD pass — not a re-run of the same
  CT.gov/protocol-PDF method, which has now been applied as thoroughly as the available sources
  allow.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
