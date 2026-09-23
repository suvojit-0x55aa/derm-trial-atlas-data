# Open Derm Trial Atlas — Data (schema v4)

Structured, sourced trial-design, safety, and results data for dermatology
drug trials. This repo holds **both** the data (`data/trials/*.json`, the
flattened CSVs) and the pipeline that produces it (`scripts/`, `atlas/`,
`tests/`) — as of the 2026-09 repo consolidation, `kolai-website` is no
longer part of this project. There are exactly two repos now:
`open-derm-trial-atlas` (the portal UI) and this one.

## What this covers

Real, live-pulled pivotal Phase III trials (adult / adult+adolescent,
systemic therapy), from the [ClinicalTrials.gov API
v2](https://clinicaltrials.gov/data-api/api) (`/api/v2/studies`, no API
key required), across **27 indications, 59 unique drugs, 151 trials**
(all three counts recomputed from `data/trials/*.json` each cycle):

### Atopic Dermatitis (10 drugs, 28 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | SOLO 1 (NCT02277743), SOLO 2 (NCT02277769), CHRONOS (NCT02260986), CAFE (NCT02755649) |
| Lebrikizumab | ADvocate1 (NCT04146363), ADvocate2 (NCT04178967), ADhere (NCT04250337) |
| Tralokinumab | ECZTRA 1 (NCT03131648), ECZTRA 2 (NCT03160885), ECZTRA 3 (NCT03363854) |
| Abrocitinib | JADE MONO-1 (NCT03349060), JADE MONO-2 (NCT03575871), JADE COMPARE (NCT03720470), JADE REGIMEN (NCT03627767) |
| Upadacitinib | Measure Up 1 (NCT03569293), Measure Up 2 (NCT03607422), AD Up (NCT03568318) |
| Nemolizumab | ARCADIA 1 (NCT03985943), ARCADIA 2 (NCT03989349) — FDA-approved for AD Jan 2025 |
| Roflumilast (topical cream) | INTEGUMENT-1 (NCT04773587), INTEGUMENT-2 (NCT04773600) — FDA-approved (Zoryve cream 0.15%/0.05%, NDA 215985) 2024-07-09, extended to ages 2-5 2025-10-04 |
| Tapinarof (topical cream) | ADORING 1 (NCT05014568), ADORING 2 (NCT05032859) — FDA-approved (Vtama, NDA 215272) via a 2024-12-12 efficacy supplement, for ages 2 and older |
| Crisaborole (topical ointment) | AD-301 (NCT02118792), AD-302 (NCT02118766) — FDA-approved (Eucrisa, NDA 207695) 2016-12-14, for ages 3 months and older |
| Difamilast (topical ointment) | Trial 1 (NCT02068352, Phase 2, n=121), Trial 2 (NCT03908970, Phase 3, n=364), Trial 3 (NCT03911401, Phase 3, n=251) — FDA-approved (ADQUEY, NDA 219474, Acrotech Biopharma) 2026-02-12, for ages 2 and older |

### Plaque Psoriasis (14 drugs, 38 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Guselkumab | VOYAGE 1 (NCT02207231), VOYAGE 2 (NCT02207244) |
| Risankizumab | UltIMMa-1 (NCT02684370), UltIMMa-2 (NCT02684357) |
| Tildrakizumab | reSURFACE 1 (NCT01722331), reSURFACE 2 (NCT01729754) |
| Bimekizumab | BE VIVID (NCT03370133), BE SURE (NCT03412747), BE RADIANT (NCT03536884) |
| Deucravacitinib | POETYK-PSO-1 (NCT03624127), POETYK-PSO-2 (NCT03611751) |
| Ixekizumab | UNCOVER-1 (NCT01474512), UNCOVER-2 (NCT01597245), UNCOVER-3 (NCT01646177) — FDA-approved 2016 |
| Certolizumab | CIMPASI-1 (NCT02326298), CIMPASI-2 (NCT02326272), CIMPACT (NCT02346240) — FDA-approved 2018 |
| Roflumilast (topical cream) | DERMIS-1 (NCT04211363), DERMIS-2 (NCT04211389) — FDA-approved (Zoryve cream 0.3%, NDA 215985) 2022-07-29 |
| Roflumilast (topical foam, scalp/body) | Trial 204 (NCT04128007, n=304, Phase 2b), ARRECTOR (NCT05028582, n=432, Phase 3) — FDA-approved (Zoryve foam 0.3%, NDA 217242 supplement) 2025-05-22, a separate application from the cream above |
| Tapinarof (topical cream) | PSOARING 1 (NCT03956355), PSOARING 2 (NCT03983980) — FDA-approved (Vtama, NDA 215272) 2022-05-23, its original approval |
| Ustekinumab | PHOENIX 1 (NCT00267969), PHOENIX 2 (NCT00307437) — FDA-approved (Stelara, BLA 125261) 2009-09-25 |
| Apremilast | ESTEEM 1 (NCT01194219), ESTEEM 2 (NCT01232283) — FDA-approved (Otezla, NDA 205437) 2014-03-21 |
| Brodalumab | AMAGINE-1 (NCT01708590, n=661), AMAGINE-2 (NCT01708603, n=1831), AMAGINE-3 (NCT01708629, n=1881) — FDA-approved (Siliq, BLA 761032) 2017-02-15 |
| Icotrokinra (oral, once daily) | Trial PSO-1 (NCT06143878, n=774), Trial PSO-2 (NCT06220604, n=731), Trial PSO-3 (NCT06095115, n=684), Trial PSO-4 (NCT06095102, n=311, scalp/genital/hands-feet subpopulation) — FDA-approved (Icotyde, NDA 220149, Janssen) 2026-03-17 |
| Secukinumab | ERASURE / Trial PsO1 (NCT01365455, n=738), FIXTURE / Trial PsO2 (NCT01358578, n=1306, active-comparator arm vs. etanercept alongside placebo), FEATURE / Trial PsO3 (NCT01555125, n=177), JUNCTURE / Trial PsO4 (NCT01636687, n=182) — FDA-approved (Cosentyx, BLA 125504) 2015-01-21 |

Excluded during curation (not pivotal registrational trials): NCT02203032
"NAVIGATE" (guselkumab ustekinumab-inadequate-responder switch study),
NCT03162796 "Discover-1" (guselkumab, but this trial is actually Psoriatic
Arthritis — a different indication), NCT04102007 (single-arm open-label
risankizumab post-switch study).

Icotrokinra, added cycle 13 (2026-09-05), is a real new oral IL-23
receptor antagonist peptide (not an injectable biologic like the other 12
drugs in this table) — FDA-approved 2026-03-17, found via a broad openFDA
`label.json` sweep for dermatology NDA/BLA approvals not yet
cross-checked against this atlas's drug list (the same method that found
the Ustekinumab/Apremilast/Acne-Vulgaris gaps). All 4 pivotal trials are
individually confirmed placebo-controlled and label-cited (ICOTYDE's own
section 14 names all 4 by trial ID and NCT number); PSO-1/PSO-2 also carry
deucravacitinib as an active-comparator arm alongside placebo, and PSO-4
enrolls a scalp/genital/hands-feet subpopulation specifically. Orange Book
indexes the drug under its salt name `ICOTROKINRA HYDROCHLORIDE`, not the
bare `ICOTROKINRA` the FDA label's `openfda.substance_name` uses (same
salt-name pattern as Glycopyrronium Tosylate) — the ingredient query
returns exactly 1 product row (NDA 220149), no collision to pin. FAERS
under `ICOTROKINRA` returns only 2 real-world reports — expected and
correct, not a bug, for a drug approved roughly 6 months before this
cycle's pull.

Ustekinumab, Apremilast, and Brodalumab are three of dermatology's
best-known, longest-approved Psoriasis drugs (2009, 2014, 2017
respectively) — a real gap in prior cycles' curation, closed this cycle.
All 3 AMAGINE trials show `OverallStatus: TERMINATED` on CT.gov (an early
"Sponsor decision" tied to Siliq's eventual suicidal-ideation boxed
warning) but all 3 have a real, complete `resultsSection` — confirmed
against Siliq's own FDA label section 14, which describes "Trials 1, 2,
and 3" totalling n=4373, matching AMAGINE 1/2/3's combined enrollment
exactly; termination doesn't disqualify a trial under this atlas's own
bar, only a missing `resultsSection` does. Two older biologics checked but
still not added, queued for a future cycle: Etanercept (Enbrel, approved
for Psoriasis 2004) and Infliximab (Remicade, approved 2006) both have
real placebo-controlled pivotal trials on CT.gov (EXPRESS/EXPRESS II for
Infliximab), but both predate CT.gov's 2007 mandatory-results-reporting
rule and were individually confirmed to have **no** `resultsSection` at
all — a genuine dead end for this atlas's `adverse_events` field group,
not an oversight.

Adalimumab (Humira, already in this atlas for Hidradenitis Suppurativa)
was checked for its own, older Plaque Psoriasis approval (2008) the same
way Secukinumab was, cycle 15 — real but excluded: HUMIRA's label cites
"Study Ps-I" (n=1212) as its pivotal Psoriasis trial, matching
NCT00237887's exact enrollment count, so the trial is identified with
confidence, but that trial has `hasResults: false` on CT.gov and was
started c. 2005 — the same permanent pre-2007 dead end as Etanercept and
Infliximab (Adalimumab's own HS trials, already in the atlas, are a
decade newer and do have posted results).

Secukinumab (Cosentyx), added cycle 15 (2026-09-05), was already in this
atlas for Hidradenitis Suppurativa but was missing its own, much
better-known Plaque Psoriasis approval (2015, one of dermatology's
original anti-IL-17 biologics) — a real 14-cycle gap, found the same way
as the Ustekinumab/Apremilast gap: checking a well-known FDA-approved
dermatology drug already present in the atlas for OTHER indications it
might also cover, rather than only chasing brand-new approvals.
COSENTYX's own FDA label section 14 names all 4 pivotal trials by
CT.gov ID under the codes Trial PsO1-PsO4 ("Four multicenter, randomized,
double-blind, placebo-controlled trials... enrolled 2,403 subjects"),
matching this atlas's existing "label-cited trial is pivotal" precedent —
FEATURE and JUNCTURE are smaller (n=177, n=182) device-usability studies
(pre-filled syringe, then autoinjector) rather than the primary efficacy
trials, but the label frames all 4 together as one 4-trial evidence base,
so all 4 are included, matching the precedent already set for
Icotrokinra's 4 label-cited trials. FIXTURE is a 3-arm design (secukinumab
vs. etanercept vs. placebo) — a real active-comparator arm alongside a
genuine placebo arm, not an active-comparator-only trial, so it still
qualifies under this atlas's placebo-controlled bar. FAERS and Purple
Book data were already staged for Secukinumab from its HS addition
(cycle 3) and are drug-level, not trial-level, so they were reused
verbatim for these 4 new trials rather than re-fetched.

### Hidradenitis Suppurativa (3 drugs, 6 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Adalimumab | PIONEER I (NCT01468207), PIONEER II (NCT01468233) |
| Secukinumab | SUNSHINE (NCT03713619), SUNRISE (NCT03713632) |
| Bimekizumab | BE HEARD I (NCT04242446), BE HEARD II (NCT04242498) |

### Alopecia Areata (3 drugs, 5 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Baricitinib | BRAVE-AA1 (NCT03570749), BRAVE-AA2 (NCT03899259) |
| Ritlecitinib | ALLEGRO-2b/3 (NCT03732807) |
| Deuruxolitinib | THRIVE-AA1 (NCT04518995), THRIVE-AA2 (NCT04797650) — registered on CT.gov under the pre-approval compound code CTP-543 |

### Chronic Spontaneous Urticaria (3 drugs, 6 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Omalizumab | ASTERIA I (NCT01287117), ASTERIA II (NCT01292473), GLACIAL (NCT01264939) — acronyms per literature, CT.gov's own `acronym` field is empty for these 3 |
| Dupilumab | LIBERTY-CSU CUPID (NCT04180488) — master protocol, 3 sub-studies; CSU is a real, separate FDA-approved indication for dupilumab (confirmed via the live openFDA label, section 1.7), distinct from the AD trials above |
| Remibrutinib | REMIX-1 (NCT05030311), REMIX-2 (NCT05032157) — FDA-approved (Rhapsido, NDA 218436) 2025-09-30. Excluded as non-pivotal: NCT05048342 "BISCUIT" (Japan-only open-label regional bridging study, n=71), NCT06868212 "RECLAIM" (active-comparator vs. dupilumab, not yet complete) |

### Prurigo Nodularis (2 drugs, 4 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | PRIME (NCT04183335), PRIME2 (NCT04202679) — FDA-approved for PN Sept 2022 |
| Nemolizumab | OLYMPIA 1 (NCT04501679), OLYMPIA 2 (NCT04501666) — FDA-approved for PN Aug 2024 |

CT.gov maps these trials' condition to "Neurodermatitis" (a MeSH-adjacent
synonym), not the literal string "Prurigo Nodularis" — confirmed as the
correct indication via each trial's title and the sponsor's own registry
page, not assumed from the condition field alone.

### Vitiligo (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Ruxolitinib (topical cream) | TRuE-V1 (NCT04052425), TRuE-V2 (NCT04057573) — FDA-approved (Opzelura) July 2022 |

Thin (1 drug) but real: Opzelura cream is the only FDA-approved
repigmentation therapy for vitiligo as of this pass. A separate,
previously-investigated 3-drug **oral**-JAK systemic Phase III program
(ritlecitinib "Tranquillo", upadacitinib "Viti-Up", povorcitinib
"STOP-V1/V2") remains excluded: every trial in that program still has
zero posted results — none can populate the `adverse_events` field group
yet.

Ruxolitinib the ingredient also covers Jakafi/Jakafi XR (oral tablets,
NDA 202192/217180, oncology/GVHD use) under separate NDAs from Opzelura
(NDA 215309, this atlas's drug) — `exclusivity.orange_book` is pinned to
215309 specifically, but openFDA's FAERS `medicinalproduct` search field
can't distinguish formulation/route, so `real_world_safety.faers_summary`
for Ruxolitinib is a mix of Opzelura and Jakafi(XR) reports, not
Opzelura-only — a real, documented limitation of FAERS's report-level
data, not a pipeline bug.

### Chronic Hand Eczema (1 drug, 3 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Delgocitinib (topical cream) | DELTA 1 (NCT04871711), DELTA 2 (NCT04872101), DELTA TEEN (NCT05355818) — FDA-approved (Anzupgo, NDA 219155) 2025-07-23 |

DELTA 1/2 are the twin global vehicle-controlled adult pivotal trials;
DELTA TEEN extends the same registrational program to adolescents 12-17
(vehicle-controlled, not an open-label extension). Excluded as non-pivotal:
NCT05259722 "DELTA FORCE" (active-comparator vs. Toctino/alitretinoin, not
placebo/vehicle-controlled), NCT04949841 (open-label extension of DELTA
1/2), NCT06004050 (Phase III, no posted results yet).

### Bullous Pemphigoid (1 drug, 1 trial)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | LIBERTY-BP (NCT04206553) — Phase 2/3 combined trial, n=106; BP is a real, separate FDA-approved indication for dupilumab (confirmed via the live openFDA label, section 1.8) |

Thinnest indication in the atlas (1 drug, 1 trial), but real and verified —
same precedent as Vitiligo's inclusion. A drug initially proposed as a
candidate for this indication, rilzabrutinib (Wayrilz), does **not** hold
up: it has zero CT.gov trials for Bullous Pemphigoid and its FDA label
indications are Immune Thrombocytopenia only — a wrong lead, not a real BP
drug. Also checked and excluded: efgartigimod (Vyvgart) has a completed BP
Phase 2/3 trial (NCT05267600) but its FDA label indications are gMG and
CIDP only, not BP.

### Generalized Pustular Psoriasis (1 drug, 1 trial)

| Drug | Pivotal Phase III trials |
|---|---|
| Spesolimab | Effisayil™ 1 (NCT03782792) — Phase 2 pivotal trial, n=53; FDA-approved (Spevigo, BLA761244) Sept 2022 |

Officially a Phase II trial (GPP is an ultra-rare orphan indication —
randomized placebo-controlled trials of this size are the norm for its
approvals), same "genuine pivotal trial, not literal-Phase-3-only"
precedent already established by Bullous Pemphigoid's Phase 2/3 LIBERTY-BP
above. Randomized, double-blind, placebo-controlled, results posted —
confirmed as the real basis for Spevigo's FDA approval via the live
openFDA label (section 1). Checked and excluded as non-pivotal for GPP:
NCT04399837 (Phase 2 flare-prevention trial, not the registrational
flare-treatment trial) and the Palmoplantar Pustulosis extension of the
same program (NCT03135548, NCT04493424 — different indication, and the
long-term trial was terminated). Spevigo's Purple Book applicant is LEO
Pharma A/S, not trial-sponsor Boehringer Ingelheim — BI ran the pivotal
trial and originated the molecule, but licensed US commercial/regulatory
rights to LEO Pharma before approval; a real BLA-holder-vs-sponsor split,
not a data error. Also checked as candidates and excluded: Netherton
Syndrome (multiple real Phase 2/3 programs in progress — QRX003, spesolimab,
dupilumab — but zero FDA-approved systemic therapy exists yet, so no
pivotal trial qualifies) and Discoid/Cutaneous Lupus Erythematosus
(anifrolumab, litifilimab, enpatoran trials all still active/recruiting
with no posted results and no CLE/DLE-specific FDA approval yet).
Pemphigus Vulgaris was also checked: Rituximab is genuinely FDA-approved
for the indication (label section 1.5), but its pivotal trial (NCT02383589,
"Ritux 3") is Rituximab-vs-Mycophenolate-Mofetil — an active-comparator
head-to-head, not placebo/vehicle-controlled — so it fails this atlas's own
inclusion bar and was excluded, not added.

### Epidermolysis Bullosa (2 drugs, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Birch Triterpenes (Filsuvez, topical gel) | EASE (NCT03068780), n=223 — FDA-approved (NDA 215064, Chiesi) 2023-12-18, for wounds in dystrophic/junctional EB |
| Beremagene Geperpavec (Vyjuvek, topical gel) | GEM-3 (NCT04491604), n=31 — FDA-approved (BLA 125774, Krystal Biotech) 2023-05-19, an HSV-1 vector-based gene therapy for wounds in dystrophic EB with COL7A1 mutations |

12th indication, added 2026-09-05 (cycle 5). Both are genuinely distinct,
FDA-approved, placebo/vehicle-controlled pivotal trials, not one drug
counted twice — Filsuvez is a small-molecule-adjacent botanical extract
(Orange Book, NDA), Vyjuvek is a CBER-licensed biologic gene therapy
(Purple Book, BLA) despite both being topical gels. Checked and excluded
as non-pivotal/non-approved: FCX-007 (dabocemagene autoficel) is
ACTIVE_NOT_RECRUITING, not yet FDA-approved.

### Erythropoietic Protoporphyria (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Afamelanotide (Scenesse, subcutaneous implant) | CUV039 (NCT01605136, EU, n=93), CUV029 (NCT00979745, US, n=74) — FDA-approved (NDA 210797, Clinuvel) 2019-10-08 |

12th indication, added 2026-09-05 (cycle 5). Thin (1 drug) but real: the
FDA label's own Clinical Studies section (14) names exactly these two
trials by CT.gov ID as the basis for approval. A third, earlier Clinuvel
Phase III trial (NCT04053270, "CUV1647", n=100, 2007–2009) exists on
CT.gov but is not cited in the label's clinical-studies section — excluded
as non-pivotal (predates the trials FDA actually relied on).

Checked and excluded this cycle (real negative findings, not omissions):
Mastocytosis / Urticaria Pigmentosa (avapritinib's FDA approval is for
advanced *systemic* mastocytosis via oncology/hematology trials —
PIONEER/EXPLORER/PATHFINDER — with no dermatology-relevant cutaneous-only
placebo-controlled pivotal trial found on CT.gov) and Cicatricial/Mucous
Membrane Pemphigoid (no FDA-approved drug specific to this indication with
a completed placebo-controlled pivotal trial — baricitinib's ocular MMP
trial was Phase 2 and terminated; rituximab's Phase 3 MMP trial is an
active-comparator, not yet complete).

### Seborrheic Dermatitis (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Roflumilast (topical foam) | Trial 203 (NCT04091646, n=226), STRATUM (NCT04973228, n=457) — FDA-approved (Zoryve foam 0.3%, NDA 217242) 2023-12-15 |

13th indication, added 2026-09-05 (cycle 6). Roflumilast (Zoryve) is a
genuine two-NDA drug — Arcutis holds a *separate* NDA per dosage form, not
one NDA with several products: NDA 215985 (cream) covers the Plaque
Psoriasis and Atopic Dermatitis trials above, NDA 217242 (foam) covers
these two Seborrheic Dermatitis trials. Trial 203 (NCT04091646) is
literally registered as Phase 2b on CT.gov, but ZORYVE foam's own FDA
label section 6.1 names it, alongside STRATUM, as one of the two
vehicle-controlled trials the seborrheic-dermatitis approval rests on —
same "real pivotal trial over literal phase label" precedent already
established by Generalized Pustular Psoriasis/Spesolimab, and here backed
by an even more direct citation (the trial is named in the product's own
label, not inferred). `real_world_safety.faers_summary` is shared across
all 6 Roflumilast trials (cream + foam): openFDA's FAERS
`medicinalproduct` search matches the ingredient name regardless of
formulation, so it can't be split by NDA — the same documented limitation
already noted for Ruxolitinib/Opzelura above.

Also added this cycle: Tapinarof (Vtama), a second topical AhR-agonist
expanding both Plaque Psoriasis (+PSOARING 1/2, its original 2022-05-23
approval) and Atopic Dermatitis (+ADORING 1/2, added via a 2024-12-12
efficacy supplement) — see those two indications' tables above. Unlike
Roflumilast, Tapinarof is a single-NDA drug (NDA 215272, Organon LLC):
both indications share one Orange Book application, no split needed.

### Acne Vulgaris (6 drugs, 12 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Trifarotene (topical cream) | NCT02556788 (n=1212), NCT02566369 (n=1208), both vehicle-controlled — FDA-approved (Aklief, NDA 211527) 2019-10-04 |
| Sarecycline (oral tablet) | SC1401 (NCT02322866, n=1034), SC1402 (NCT02320149, n=968), both placebo-controlled — FDA-approved (Seysara, NDA 209521) 2018-10-01 |
| Clascoterone (topical cream) | CB-03-01 Study 25/26 (NCT02608450 n=708, NCT02608476 n=732), both vehicle-controlled — FDA-approved (Winlevi, NDA 213433) 2020-08-26 |
| Minocycline (topical foam 4%) | NCT02815267 (n=466), NCT02815280 (n=495), NCT03271021 "Study 3" (n=1488, long-term safety), all vehicle-controlled — FDA-approved (Amzeeq, NDA 212379) 2019-10-18 |
| Tretinoin and Benzoyl Peroxide (topical cream) | NCT03761784 (n=424), NCT03761810 (n=434), both vehicle-controlled — FDA-approved (Twyneo, NDA 214902) 2021-07-26 |
| Clindamycin Phosphate/Benzoyl Peroxide/Adapalene (topical gel) | NCT04214639 (n=183), NCT04214652 (n=180), both vehicle-controlled — FDA-approved (Cabtreo, NDA 216632) 2023-10-20 |

Minocycline, Tretinoin+Benzoyl Peroxide, and Clindamycin+Benzoyl
Peroxide+Adapalene added cycle 23 (2026-09), found via the same
well-known-drug-class sweep that found the original 3. Minocycline
topical foam is FDA-approved under **two separate NDAs at two different
strengths for two different indications** — Amzeeq (NDA 212379, 4%,
Acne Vulgaris) and Zilxi (NDA 213690, 1.5%, Rosacea, see below) — a new,
sharper variant of the Roflumilast cream/foam split: here it's the same
molecule, same aerosol-foam dosage form, same applicant (Journey
Medical), differing only in strength and indication. `data/drugs/
minocycline.json` holds both applications keyed by `application_number`
(the established Ruxolitinib/Roflumilast tuple-pin pattern) rather than
being force-merged into one. Twyneo's Orange Book applicant (Mayne
Pharma) differs from its FDA label/CT.gov sponsor (Sol-Gel
Technologies/Galderma) — a real post-approval commercial-rights
transfer chain (Sol-Gel → Galderma → Mayne Pharma), not a data
inconsistency, the same shape as Spesolimab/LEO Pharma and
Difamilast/Acrotech. Cabtreo's NCT04214639/NCT04214652 pair has 0
`effect_estimates` each — their CT.gov `resultsSection` genuinely
carries no `analyses[]` statistical-comparison block for any outcome
measure, confirmed by inspecting the raw cache directly, not a build
gap.

14th indication, added 2026-09-05 (cycle 9). Acne Vulgaris is dermatology's
highest-prevalence indication and had been entirely absent through 8 prior
cycles — a real gap, not a deliberate exclusion, found the same way
Ustekinumab/Apremilast were: checking well-known FDA-approved topical/oral
dermatology drugs against the atlas's own drug list. All three are
single-NDA small-molecule drugs (no Purple Book entries); Clascoterone's
trials were registered under its original development code CB-03-01
(cortexolone 17α-propionate), confirmed as the same drug approved as
Winlevi via its FDA label. This cycle also re-checked, and confirmed
**still real negatives** (no change from prior cycles): Vitiligo's three
oral-JAK candidates (ritlecitinib Tranquillo NCT05583526, upadacitinib
NCT06118411, povorcitinib STOP-V1/V2) all remain `ACTIVE_NOT_RECRUITING`/
`COMPLETED` with zero posted results and no FDA vitiligo indication yet;
and Pimecrolimus (Elidel)/Tacrolimus (Protopic) for Atopic Dermatitis hit
the same pre-2007 dead-end pattern as Etanercept/Infliximab — every
CT.gov-registered trial for either drug is a post-approval Phase 4 study
or a generic-manufacturer bioequivalence/ANDA trial (e.g. Fougera's
"0416"/"0417" ointment studies), never the original branded pivotal trial
(Protopic approved 2000, Elidel 2001, both pre-dating CT.gov's 2007
mandatory-results-reporting rule). Also re-checked and confirmed still
unapproved: povorcitinib/sonelokimab/izokibep/lutikizumab for HS (real
Phase 2b/3 programs, none with an FDA label yet — including spesolimab's
own real, posted-results HS trial Lunsayil 1, since Spevigo's FDA label
is GPP-only), and ligelizumab/barzolvolimab for CSU.

### Onychomycosis (2 drugs, 4 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Efinaconazole (topical solution) | NCT01007708 (n=780), NCT01008033 (n=870), both vehicle-controlled (development code IDP-108) — FDA-approved (Jublia, NDA 203567) 2014-06-06 |
| Tavaborole (topical solution) | NCT01270971 (n=594), NCT01302119 (n=604), both vehicle-controlled (development code AN2690) — FDA-approved (Kerydin, NDA 204427) 2014-07-07, brand since discontinued (many generic ANDAs remain on market) |

### Rosacea (4 drugs, 8 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Ivermectin (topical cream) | NCT01493687 (n=683), NCT01494467 (n=688), both vehicle-controlled (development code CD5024) — FDA-approved (Soolantra, NDA 206255) 2014-12-19 |
| Oxymetazoline HCl (topical cream) | NCT02131636 (n=440), NCT02132117 (n=445), both vehicle-controlled (development code AGN-199201) — FDA-approved (Rhofade, NDA 208552) 2017-01-18 |
| Benzoyl Peroxide (topical cream 5%) | NCT03448939 (n=361), NCT03564119 (n=372), both vehicle-controlled — FDA-approved (Epsolay, NDA 214510) 2022-04-22 |
| Minocycline (topical foam 1.5%) | NCT03142451 (n=751), NCT04608500 (n=771), both vehicle-controlled — FDA-approved (Zilxi, NDA 213690) 2020-05-28 |

Benzoyl Peroxide and Minocycline added cycle 23 (2026-09) — see the
Acne Vulgaris section above for the Zilxi/Amzeeq shared-molecule,
two-NDA finding. Epsolay's NCT03564119 has 0 `effect_estimates` (its
CT.gov `resultsSection` has no `analyses[]` block for any outcome
measure, a real design gap, not a build one — same as Cabtreo's pair
above).

15th and 16th indications, added 2026-09-05 (cycle 9, same session as Acne
Vulgaris). Both found the same way: checking well-known, decades-familiar
dermatology drug classes (antifungals, rosacea topicals) against the
atlas's own list rather than only chasing newly-approved candidates. All
4 drugs are single-NDA small molecules old enough to have real generic
competition on the market — a genuinely new wrinkle for this atlas's
Orange Book fetch: a plain `products.active_ingredients.name` search on
openFDA now returns the original NDA row mixed with several generic
ANDA rows for the *same* ingredient (Efinaconazole: 7 ANDA generics;
Tavaborole: 8; Ivermectin: 12, including two *other* NDAs for the same
ingredient — Stromectol/oral and Sklice/lice lotion — a 3-way collision
worse than Ruxolitinib's 2-way one; Oxymetazoline HCl: 1). Every one of
these 4 drugs needed an `application_number` tuple-pin (the
Ruxolitinib/Roflumilast precedent) before calling
`fetch_orange_book.build_record()`, confirmed by checking each result
came back with exactly 1 product row after filtering — an unpinned query
would have silently merged another applicant's patents/exclusivities
into the wrong drug's `exclusivity.orange_book` value. Kerydin's brand
label lookup via `openfda label.json?search=openfda.brand_name:Kerydin`
returns `NOT_FOUND` (brand discontinued, superseded by generics) even
though the drug's own NDA approval is real and unaffected — a real,
documented edge case: `openfda.brand_name` label search only returns
*currently marketed* labels, so a discontinued-but-real approval needs
`drug/orangebook.json` (which keeps every historical row regardless of
current marketing status) as the authoritative check instead.

### Actinic Keratosis (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Tirbanibulin (topical ointment 1%) | NCT03285477 "AK003" (n=351), NCT03285490 (n=351), both vehicle-controlled (development code KX2-391) — FDA-approved (Klisyri, NDA 213189) 2020-12-14 |

### Molluscum Contagiosum (1 drug, 3 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Berdazimer (topical gel 10.3%) | NCT04535531 "B-SIMPLE4" (n=891), NCT03927703 "B-SIMPLE2" (n=355), NCT03927716 (n=352), all vehicle-controlled (development code SB206) — FDA-approved (Zelsuvmi, NDA 217424) 2024-01-05 |

17th and 18th indications, added 2026-09-05 (cycle 10). Both drugs' pivotal
sets were taken straight from the FDA label's own section 14, which names
every trial by CT.gov ID — Klisyri cites "NCT03285477 and NCT03285490";
Zelsuvmi cites "Trials 1, 2, and 3; NCT04535531, NCT03927703, and
NCT03927716, respectively". Both are registered on CT.gov under their
pre-approval development codes (KX2-391, SB206) rather than their generic
names, the same Clascoterone/`CB-03-01` pattern already documented above.

All three Berdazimer trials are included even though Zelsuvmi's own label
says "Efficacy was demonstrated in Trials 1 and 2" — Trial 3 (NCT03927716)
missed its primary endpoint, but the label's Clinical Studies section
presents all three as the pivotal program, and this atlas records the
program FDA actually reviewed, not only its positive arms. Molluscum
contagiosum is also this atlas's first indication whose pivotal program is
essentially entirely pediatric: all three trials enrol from 6 months of
age and the label reports 96% of subjects were 2–17 years old.

Neither drug needed an `application_number` tuple-pin on its Orange Book
fetch (unlike the Onychomycosis/Rosacea drugs above): both are recent
enough to have no generic ANDAs, and each
`products.active_ingredients.name` query returned exactly 1 product row,
checked before writing. Berdazimer did need a fallback on **both** openFDA
lookups, for two unrelated reasons — see the note in `AGENTS.md`:
`drug/label.json` indexes it with `openfda.substance_name: None` (so the
pipeline's default `openfda.substance_name:` query 404s and
`openfda.generic_name:BERDAZIMER` is needed to record the real,
confirmed-absent boxed warning), and its FAERS reports are all filed under
the brand name — `patient.drug.medicinalproduct:"BERDAZIMER"` returns a
hard `NOT_FOUND` while `"ZELSUVMI"` returns 71 real reports, so
`real_world_safety.faers_summary` is recorded on the brand term with
`query.search_term` saying so.

### Hyperhidrosis (2 drugs, 4 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Glycopyrronium (topical cloth, 2.4%) | NCT02530281 (Trial 1, n=344), NCT02530294 (Trial 2, n=353), both vehicle-controlled — FDA-approved (Qbrexza, NDA 210361) 2018-06-28 |
| Sofpironium Bromide (topical gel 12.45%) | NCT03836287 (n=350), NCT03948646 (n=351), both vehicle-controlled — FDA-approved (Sofdra, NDA 217347) 2024-06-18 |

Sofpironium Bromide added cycle 23 (2026-09), both trials for axillary
hyperhidrosis, vehicle-controlled, `hasResults: true`. Its Orange Book
entry carries a real, populated NCE (New Chemical Entity) exclusivity
(expires 2029-06-18) — the first drug in this cycle's batch with a
non-empty `exclusivities` array.

19th indication, added 2026-09-05 (cycle 11). Both trials are named in
QBREXZA's own FDA label section 14.1 as Trial 1 and Trial 2, and both were
individually confirmed live: Phase 3, `COMPLETED`, randomized
double-blind vehicle-controlled, glycopyrronium in the `EXPERIMENTAL` arm,
condition `Hyperhidrosis`, `resultsSection` present with 2 adverse-event
groups. The Orange Book application of record and the CT.gov lead sponsor
agree (Journey Medical) because Journey acquired the NDA from Dermira,
which originated it in 2018 and ran these trials.

Two source lookups needed care, for two different reasons:

- **Orange Book** indexes the drug under the salt name `GLYCOPYRRONIUM
  TOSYLATE`, not the bare `GLYCOPYRRONIUM` the FDA label's
  `openfda.generic_name` uses. The ingredient query returns 2 rows —
  N210361 (QBREXZA, reference-listed) and A214448 (a `DISCONTINUED`
  Padagis US generic ANDA) — so `exclusivity.orange_book` is pinned to
  210361, the same generic-ANDA collision already documented for the
  Onychomycosis/Rosacea drugs. The unrelated *inhaled* glycopyrronium COPD
  products (Seebri, Lonhala, Utibron) do **not** collide here: Orange Book
  files them under the ingredient name `GLYCOPYRROLATE`.
- **FAERS** is the exception to this atlas's generic-name-preferred default,
  and the first case where the generic term is real but points at the wrong
  drug family. `patient.drug.medicinalproduct:"GLYCOPYRRONIUM"` returns
  9,183 reports, but a `count=patient.drug.drugindication.exact` on that
  same query is dominated by inhaled glycopyrronium-bromide bronchodilators
  (COPD 1,824; asthma 891; dyspnoea 135; emphysema 118) with hyperhidrosis
  absent from the top 12 — those reports are about a different product
  family, not a different formulation of this one.
  `"QBREXZA"` returns 844 reports whose top indication is `HYPERHIDROSIS`
  (485 of 844), so `real_world_safety.faers_summary` is recorded on the
  brand term with `query.search_term` and `source_excerpt` saying exactly
  that. This is deliberately *not* handled the way Ruxolitinib's
  Opzelura/Jakafi mix is: that mix is unavoidable (one ingredient, no
  cleaner term), while here a clean, correct term exists.

Checked and excluded this cycle (real negative findings, not omissions):
Basal Cell Carcinoma, both of whose FDA-approved hedgehog-pathway
inhibitors fail this atlas's placebo/vehicle-controlled bar — Vismodegib
(Erivedge, NDA 203388) rests on SHH4476g (NCT00833417), a single-arm
open-label trial with no comparator at all, and Sonidegib (Odomzo, NDA
205266) rests on BOLT (NCT01327053), which randomizes between two dose
levels of the same drug (200 mg vs. 800 mg) rather than drug vs. placebo —
the same active-comparator-style exclusion already applied to Pemphigus
Vulgaris/Rituximab. Both drugs treat locally-advanced/metastatic disease
with oral systemic therapy at doses selected without a placebo arm, a
standard oncology-trial design rather than a data-quality gap, so BCC is a
confirmed dead end for this atlas, not an oversight.

### Impetigo (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Ozenoxacin (topical cream, 1%) | NCT01397461 (n=465), NCT02090764 (n=412), both vehicle-controlled — FDA-approved (Xepi, NDA 208945) 2017-12-11 |

20th indication, added cycle 12 (2026-09-05). Both trials are named in
XEPI's own FDA label section 14. Xepi's brand is market-discontinued and
absent from openFDA `label.json` under brand, substance, generic, or
`application_number` search — worse than the Kerydin precedent, where
`substance_name` still worked. `boxed_warning` was resolved anyway
(confirmed `present: false`) by reading the original approval-package
label PDF directly from `drug/drugsfda.json`'s ORIG submission
`application_docs[].url`. FAERS is contaminated on both the generic and
brand search terms at once — a new, worse variant of the
Glycopyrronium/Qbrexza finding (where only the generic term was
contaminated): `OZENOXACIN` (17 reports) skews toward cerebral haemorrhage
and ACTH deficiency, `XEPI` (4 reports) skews toward narcolepsy/cataplexy
(Xyrem territory) — neither resembles a topical antibiotic's real profile.
Recorded as-is (generic term, atlas default) with this caveat rather than
picking whichever term looks cleaner, since neither is clean for a
low-volume, old, discontinued drug.

### Seborrheic Keratosis (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Hydrogen Peroxide (topical solution, 40%) | THERAPEUTIC-1 (NCT02667236, n=450), THERAPEUTIC-2 (NCT02667275, n=487), both vehicle-controlled — FDA-approved (Eskata, NDA 209305) 2017-12-14 |

21st indication, added cycle 12 (2026-09-05). Both trials are named in
ESKATA's own FDA label section 14. Same market-discontinued-brand /
absent-from-`label.json` situation as Ozenoxacin above; `boxed_warning`
resolved the same way (original approval-package label PDF, confirmed
`present: false`). FAERS here is the opposite shape from Ozenoxacin: the
generic term `HYDROGEN PEROXIDE` (521 reports) is the contaminated one
(dominated by OTC wound-care/mouthwash/teeth-whitening products), while
the brand `ESKATA` (212 reports, top indication `SEBORRHOEIC KERATOSIS`
159/212) is clean — used instead per the atlas's standard
run-the-`drugindication`-count-first rule, with `query.search_term`
recording the override.

### Head Lice (1 drug, 1 trial)

| Drug | Pivotal Phase III trials |
|---|---|
| Abametapir (topical lotion, 0.74%) | NCT02060903 (n=379), vehicle-controlled — FDA-approved (Xeglyze, NDA 206966) 2020-07-24 |

22nd indication, added cycle 17. FDA's label names "Trials 1 and 2" as
the two identical randomized, double-blind, vehicle-controlled pivotal
trials (704 subjects combined) behind Xeglyze's approval; only Trial 1
(NCT02060903) has a posted `resultsSection` on CT.gov, so only it is
included. Trial 2 (NCT02062060, n=325) is a real, label-cited,
efficacy-positive trial with no posted results — a re-check candidate for
a future cycle, same category as Zevaskyn/VIITAL and Cemiplimab/C-POST,
not a data gap. Same market-discontinued-brand / absent-from-`label.json`
situation as Ozenoxacin/Xepi and Hydrogen Peroxide/Eskata; `boxed_warning`
resolved the same way (original approval-package label PDF, confirmed
`present: false`). FAERS is a genuine confirmed zero on both the generic
(`ABAMETAPIR`) and brand (`XEGLYZE`) terms — no alternate term exists, so
recorded as a real `total_reports: 0`, not a `null`. Orange Book has a
single clean product row (no ingredient-name collision). Checked and
excluded in the same sweep: Spinosad (Natroba, NDA022408, approved 2011,
also for head lice) — its 2 pivotal trials (NCT00545168, NCT00545753) are
randomized but ACTIVE_COMPARATOR-only (spinosad vs. permethrin/NIX, no
vehicle or placebo arm) — the same active-comparator-only exclusion
pattern as Pemphigus Vulgaris/Rituximab and the BCC hedgehog inhibitors.

### Dermatomyositis (1 drug, 1 trial)

| Drug | Pivotal Phase III trials |
|---|---|
| Immune Globulin Intravenous (Human) (Octagam 10%) | ProDERM (NCT02728752, n=95), placebo-controlled — FDA-approved (Octagam 10%, BLA 125062, efficacy supplement) 2021-07-15 |

23rd indication, added cycle 18. Found via a fresh "FDA dermatology
approvals 2026" web sweep that surfaced Brepocitinib (Lisraya), a newly
approved (2026-08-27) oral drug for dermatomyositis — its own pivotal
VALOR trial (NCT05437263) is real (randomized, double-blind,
placebo-controlled Phase 3, n=241, published in NEJM and JAMA
Dermatology) but has `hasResults: false` on CT.gov, the same
FDA-approved-but-not-yet-posted-results pattern as Zevaskyn/VIITAL and
Cemiplimab/C-POST — excluded, a re-check candidate for a future cycle,
not a data gap. Checking the indication further for an
already-posted-results alternative surfaced Octagam 10% (IVIG), FDA
dermatomyositis-approved since 2021 via its own placebo-controlled
Phase 3 trial ProDERM, which does have `hasResults: true` — added
instead. Dermatomyositis is in scope for this atlas despite being a
systemic autoimmune disease (muscle + skin) rather than a skin-only
condition, the same precedent as CTCL and Mastocytosis: the trial's own
primary and secondary endpoints include a dedicated dermatology severity
instrument (CDASI, Cutaneous Dermatomyositis Disease Area and Severity
Index) and heliotrope rash/Gottron's papules are hallmark diagnostic
features — a materially stronger dermatology case than the Behçet's
oral-ulcer trial excluded on scope in cycle 16.

Deep-extraction notes (first trial added under the cycle-18 standing
full-extraction requirement): ProDERM's design does not fit this
schema's `rescue_therapy` shape built for the AD trials (topical-then-
systemic step-up) — it is instead a blinded treatment-switch ("escape")
design where confirmed deterioration (worsening on 2 consecutive visits
by defined thresholds) switches a subject to the other blinded arm
rather than adding a rescue medication; recorded via `trigger_rules` /
`flare_definition` with the mismatch explained in `rationale`. Likewise
`design.background_therapy.regimen_type`'s 3 enum values
(monotherapy/combination_tcs/standardized_background_topical) are all
AD/psoriasis-specific and none fit a systemic-disease permitted-
background design — left `null` with the real background-therapy rules
(stable-dose corticosteroids/immunosuppressants, per-agent dose caps and
washouts) recorded in `background_agent_class`/`permitted_concomitant`/
`population_note` instead of forcing an inapplicable enum value. Octagam
is a CBER-reviewed (not CDER) plasma-derived polyclonal immunoglobulin
BLA — `molecule.mechanism_of_action.modality` is `"other"` (not
`monoclonal_antibody`), and the label itself states the mechanism "has
not been fully elucidated." FAERS on `OCTAGAM` (1969 reports) is a new,
more extreme version of the generic-term-contamination pattern already
documented for Qbrexza/Glycopyrronium: Octagam's broad original ITP/
immunodeficiency uses dominate every top FAERS indication term, and
dermatomyositis does not appear in the top 15 at all — recorded as-is
(no brand-vs-generic split exists to retry, the same unavoidable-mix
situation as Ruxolitinib). CT.gov's AE results report only 2 event
groups ("First Period Placebo" n=48 and "Overall Period Octagam" n=95,
not a clean per-arm split) because of the crossover/escape design —
documented in `source_excerpt` rather than presented as a like-for-like
comparison.

### Scabies (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Spinosad (topical suspension, 0.9%) | Trial 1 (NCT02485717, n=291) and Trial 2 (NCT02485704, n=280), vehicle-controlled, both COMPLETED — FDA-approved for scabies (Natroba, NDA 022408, efficacy supplement S-010) 2021-04-28 |

24th indication, added cycle 25. Natroba's own label section 14.2 names
both trials by NCT id ("Trial 1 [NCT02485717] and Trial 2 [NCT02485704]").
Both posted a Study Protocol and SAP on CT.gov, read for the deep fields;
FDA's unireview of the scabies supplement covers both. The same drug was
excluded for Head Lice in cycle 17, because its head-lice trials are
active-comparator-only (vs. permethrin). The scabies trials are
vehicle-controlled, so the drug qualifies here. AE discontinuation is a
computed 0 per arm: every non-completer is accounted for by a posted
`dropWithdraws` reason and none is an adverse event (arithmetic in
`source_excerpt`). NCT02485717 posts `frequencyThreshold` 0 with no
non-serious events, so `most_common_adverse_events` is a real empty list.
Status spread on CT.gov (cycle-25 sweep, all statuses): no
active/recruiting or stopped placebo-controlled trial of an FDA-approved
scabies drug exists. Ivermectin/permethrin/moxidectin studies there are
active-comparator, Phase 1/2, or mass-drug-administration designs.

### Interdigital Tinea Pedis (3 drugs, 5 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Naftifine (gel, 2%) | NCT01290341 (n=860) and NCT01289015 (n=855), NAFT-600, vehicle-controlled, COMPLETED — FDA-approved (Naftin Gel 2%, NDA 204286) 2013-06-27 |
| Naftifine (cream, 2%) | NCT00750139 (n=707), NAFT-500, 4 arms: NAFT-500 2 weeks and Naftin 1% 4 weeks, each with its own placebo, COMPLETED — FDA-approved (Naftin Cream 2%, NDA 019599 S-011) 2012-01-13 |
| Econazole (topical foam, 1%) | NCT01353976 (n=264), vehicle-controlled, COMPLETED — FDA-approved (Ecoza, NDA 205175) 2013-10-24 |
| Ketoconazole (cream, 2%) | NCT01110330 (n=583), placebo-controlled, **TERMINATED** (whyStopped: "Unexpected discordant results between the KOH microscopy and mycological culture tests at three study sites in the UK."), has posted results |

25th indication, added cycle 25. Naftifine's two trial-backed applications here are separate NDAs (cream
019599, gel 204286), the same shape as Roflumilast. NAFT-500's Naftin 1%
arm is a positive control alongside real placebo arms (FIXTURE
precedent); it is role-curated `active_comparator`. Econazole foam's
second label-cited trial, NCT01358240, has no posted results. It is
excluded as a re-check candidate (Xeglyze precedent).

The Ketoconazole trial is the first **stopped** trial added under the
cycle-25 status-spectrum rule. It is a randomized, placebo-controlled
Phase 3 of a drug FDA-approved for this indication (ketoconazole 2%
cream: tinea pedis per its label), stopped early, with whatever it posted
captured. It compared the marketed Nizoral cream (F012) with a new
formulation (F126); both arms are role-curated investigational (CT.gov
marks both EXPERIMENTAL). The reference NDA 019084 (Nizoral cream) is
discontinued, so the label cited is Teva's generic ketoconazole 2% cream
label (ANDA 075581); generic labeling must match the reference product's.

Ketoconazole's FAERS search term (`KETOCONAZOLE`, 15,791 reports) cannot
be made cream-specific. It mixes every ketoconazole product and route,
and the brand `NIZORAL` is dominated by shampoo reports, so it is recorded
as an unavoidable mix (Ruxolitinib precedent). Checked and excluded:
Luliconazole (Luzu) has no pivotal tinea pedis trial with posted results
on CT.gov. No active/recruiting pivotal trial exists for any approved
tinea pedis drug; the other stopped trials are unapproved drugs
(Sol-Gel, DermBiont), Phase 1 bioequivalence, or active-comparator-only
designs.

### Infantile Hemangioma (1 drug, 2 trials)

| Drug | Pivotal / placebo-controlled trials |
|---|---|
| Propranolol (oral solution) | NCT01056341 (n=512 enrolled, adaptive Phase II/III, 4 regimens vs placebo), COMPLETED — FDA-approved (Hemangeol, NDA 205410) 2014-03-14 |
| Propranolol (oral) | NCT00744185 (n=14, Phase 2/3, 30 days propranolol vs placebo, CHU Bordeaux), **TERMINATED** (whyStopped: "Study halted prematurely due to some difficulties in recruitment of patients"), no posted results |

26th indication, added cycle 25. Hemangeol's label section 14 describes
exactly NCT01056341's design (4 regimens of 1.2 or 3.4 mg/kg/day for 3
or 6 months vs placebo, blinded central photo assessment at Week 24).
FAERS uses the brand term `HEMANGEOL` (4,389 reports, top indications
haemangioma / infantile haemangioma). The generic `PROPRANOLOL` (62,621
reports) is dominated by the oral cardiovascular and migraine products;
this is the Qbrexza/Glycopyrronium precedent. NCT00744185 is included
under the cycle-25 stopped-trial rule. It has no `resultsSection`
(`results_status: not_yet_reported`), and its results letter (Br J
Dermatol 2013, PMID 23301692) is paywalled, so its results/AE fields stay
`needs_extraction` with that reason. Excluded from the same sweep: every
other stopped or recruiting hemangioma trial. They are
active-comparator-only (propranolol vs atenolol / acebutolol /
prednisolone / nadolol), device/laser, Phase 1, or unapproved drugs
(timolol, sirolimus, imiquimod, vincristine).

### External Genital Warts (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Imiquimod (cream, 3.75%; each trial also had a 2.5% arm) | NCT00674739 (n=470) and NCT00735462 (n=511), placebo-controlled, COMPLETED — FDA-approved for external genital and perianal warts (Zyclara 3.75%, NDA 022483 S-001 / NDA 201153) 2011-03-24 |

27th indication, added cycle 25. Zyclara's label section 14.2 describes
the 3.75%-vs-vehicle comparison across both trials (601 subjects). The
2.5% arms are real, randomized, and posted, and are kept in `results.*`.
Imiquimod's generic FAERS term (`IMIQUIMOD`, 2,167 reports) covers Aldara
5% and generics as well as Zyclara. It is one topical molecule whose top
indications (BCC/AK/anogenital warts) are all imiquimod-cream uses, so it
is kept as an inherent mix. Sinecatechins (Veregen) remains a pre-2007
dead end (cycle 21). The CT.gov status sweep found no active/recruiting
or stopped placebo-controlled treatment trial of an FDA-approved
genital-wart drug. The placebo-controlled trials there are HPV-vaccine
*prevention* trials, out of scope.

Every NCT ID above was pulled live from the API during curation — none
were guessed or reused from memory (see `data/trials/*.json` →
`source_url` on every field for the exact API call), and every drug/trial
inclusion followed the same hand-curation discipline throughout: query by
indication + intervention, then individually fetch and confirm each
candidate is a real pivotal arm (not a comparator, switch study,
active-comparator head-to-head, regional bridging study, or
wrong-indication trial) before adding it.

## Data model

One JSON file per trial at `data/trials/<NCT_ID>.json` (**schema v4**),
organized into 10 field groups (46 fields), plus one JSON file per drug at
`data/drugs/<slug>.json` (59 files) for the 7 fields that are facts about
the DRUG, not any one trial — see "Drug-level records" below. Every field
value is an object, never a bare scalar:

```json
{
  "value": "SOLO 1",
  "source_type": "ctgov_api",
  "source_url": "https://clinicaltrials.gov/api/v2/studies/NCT02277743",
  "source_excerpt": "protocolSection.identificationModule.acronym",
  "extracted_by": "fetch_trials.py (ctgov_api v2, v1 pass)",
  "reviewed_by": null,
  "confidence": 1.0
}
```

`source_type` is one of:

- `ctgov_api` — read directly from a structured field in the live CT.gov
  API v2 JSON response (including simple arithmetic over structured counts,
  e.g. an adverse-event rate computed from `numAffected`/`numAtRisk`).
  `source_excerpt` is the JSON path read.
- `ctgov_text_extraction` — parsed from a CT.gov API *free-text* field
  (`eligibilityCriteria`, an `intervention.description`) by regex + review,
  not a clean structured field. `source_excerpt` is the matched text.
- `protocol_pdf_extraction` — parsed from a trial's own Study Protocol or
  Statistical Analysis Plan PDF (linked from CT.gov's `documentSection`).
  `source_url` is the exact CDN PDF link; `source_excerpt` names the
  section the excerpt came from.
- `publication_extraction` — parsed from a full-text journal publication
  (fetched via PMC when available) or an FDA Drugs@FDA approval-package
  review (Medical/Multi-Discipline/Integrated Review; not CT.gov-linked,
  which is what distinguishes this from `protocol_pdf_extraction`).
  `source_url` is the exact PMC or accessdata.fda.gov PDF link;
  `source_excerpt` names the section/table the excerpt came from, quoting
  the source text directly wherever practical.
- `openfda_label` — pulled from the openFDA structured drug-label API
  (`api.fda.gov/drug/label.json`). Drug-level: this is `molecule.
  mechanism_of_action`'s and `adverse_events.boxed_warning`'s own
  `source_type` on `data/drugs/<slug>.json`, not on the trial (see
  "Drug-level records" below). A `null` value with this `source_type`
  means the label was checked and the field (e.g. `boxed_warning`)
  genuinely isn't present — a confirmed absence, not a gap.
- `needs_extraction` — not available in any of the sources above after
  real effort (still only in full protocol tables/appendices, a paywalled
  paper genuinely unreachable, or not published at all). `value` is
  `null` and stays `null` until human QA can fill it — this pipeline never
  guesses a plausible-sounding clinical number.
- `openfda_faers` — openFDA adverse-event API, drug-level real-world
  report summary; lives on `data/drugs/<slug>.json`'s own
  `faers_summary`, not the trial's.
- `orange_book` — FDA Orange Book data (via openFDA's mirror),
  small-molecule NDAs only; lives on `data/drugs/<slug>.json`'s own
  `applications[].orange_book`, keyed by `application_number` (almost
  every drug has exactly 1 application; Roflumilast has 2 — cream NDA
  215985, foam NDA 217242).
- `purple_book` — FDA Purple Book live search table, biologic BLAs only;
  lives on `data/drugs/<slug>.json`'s own `purple_book`.
- `drug_level_ref` — a trial's OWN copy of one of the 6 drug-level fields
  above: not the fact, a pointer to it (`{"drug", "application_number"}`).
  `source_url`/`source_excerpt`/`extracted_by`/`confidence` are all `null`
  on the pointer itself — the real citation is the drug record's own field,
  resolved by joining on `drug` (see "Drug-level records" below).

### Schema v4: typed, atomic values, drug-level references

Every `value` is a typed structure that can be filtered and compared
directly — no re-parsing prose at read time. The full field-by-field
reference is `docs/SCHEMA.md` (human-readable) / `schema/trial.schema.json`
(JSON Schema draft-07), both generated from `atlas/schema.py` — this repo's
own spec, run `python3 scripts/export_schema.py` after any change to keep
them in sync (checked by `tests/test_schema.py`). v3 added one field group,
`results` (`arms`/`arm_results`/`effect_estimates`/`published_results`):
normalized per-arm CT.gov results and pairwise effect estimates, each
referencing the existing `endpoints.*` objects by `(rank, position,
verbatim_sha1)` rather than re-describing the endpoint. v4 moves 6
drug-level fields (`molecule.mechanism_of_action`, `adverse_events.
boxed_warning`, `real_world_safety.faers_summary`, `exclusivity.
{regulatory_application,orange_book,purple_book}`) off the trial record
onto `data/drugs/<slug>.json`, referenced by a `drug_level_ref` pointer
instead of re-described per trial — see "Drug-level records" below. The
schema is indication-agnostic: adding 18 more indications beyond the original AD
set required zero schema changes — `severity_definition`/severity criteria
and the endpoint-measure fields are free text sized for any indication's
own severity/endpoint vocabulary (PASI/sPGA for psoriasis, HiSCR/IHS4 for
HS, SALT for AA, UAS7 for CSU, IGA PN-S/Worst Itch NRS for PN, VASI for
vitiligo, and so on).

The one atomic building block is **`ScoreCriterion`** — a threshold on a
named clinical scale (`{scale, metric, comparator, value, unit,
assessed_at, …}`) — reused by eligibility severity thresholds, endpoint
responder definitions, endpoint subgroups, rescue triggers, and flare
definitions. So "EASI-75 at week 16" is the same row shape wherever it
occurs, and a `results.arm_results`/`effect_estimates` row can point at it
by reference instead of re-describing it. What was free text in v1 is
typed in v2/v3/v4 (full list in `docs/SCHEMA.md`); the v1 prose survives as
provenance in `source_excerpt` (or an endpoint's `verbatim` / an
intervention's `description`) — it is never the queryable value. This
repo's own `tests/test_migration_lossless.py` proves the v1→v2 migration
is lossless (deterministic, byte-identical on re-run, every v1 fact
traceable in the v2 value, every gap preserved, nothing invented); v2→v3
is a separate, pure no-op (new fields only, no existing value touched).
v3→v4 (`scripts/split_drug_level_fields.py`) is lossless a different way:
every trial's own value for the 6 moved fields still resolves to the exact
same content via `atlas.drugs.resolve_trial_record` — checked directly by
`tests/test_drugs.py`, not just asserted.

### Drug-level records (data/drugs/<slug>.json)

`molecule.mechanism_of_action`, `adverse_events.boxed_warning`,
`real_world_safety.faers_summary`, and `exclusivity.{regulatory_application,
orange_book,purple_book}` are facts about a DRUG, not about any one trial.
Before v4, every trial of a drug carried an independently-extracted,
byte-identical copy of each — a dataset pass across this 127-trial corpus
found 1,588 verbatim-duplicated `(source_excerpt, value)` pairs this way (a
drug used across N indications paid the cost N times: Dupilumab ×8,
Roflumilast ×8, Secukinumab ×6, Bimekizumab ×5, Abrocitinib/Tapinarof/
Nemolizumab/Icotrokinra ×4 each, ...). v4 extracts each of these 6 fields
**once** per drug into `data/drugs/<slug>.json`, referenced (never copied)
by every trial of that drug — a trial's own copy is a small pointer,
`{"drug": "<name>", "application_number": "<NDA/BLA or null>"}`, with
`source_type: "drug_level_ref"`. `application_number` disambiguates the two
fields (`regulatory_application`, `orange_book`) that can genuinely differ
within one drug — Roflumilast holds 2 real FDA applications (cream NDA
215985, foam NDA 217242) — everything else is a single value per drug.
`identity.sponsor` looks drug-level too but is deliberately **not** moved:
it genuinely differs across a drug's own trials when development/commercial
rights changed hands mid-program (Dupilumab's trials split Regeneron/
Sanofi; Difamilast's split two distinct Otsuka legal entities) — collapsing
it to one drug-wide value would be a real loss, not a dedup; see
`atlas/drugs.py`'s module docstring and AGENTS.md for how this was checked
before deciding the field list, not assumed.

The extraction *pipeline* changed the same way, not just the storage: a
future one-off per-cycle script (the existing scratch-checkout convention,
see AGENTS.md) discovering a new trial calls `atlas.drugs.ensure_drug_record`
once per drug — it returns the already-committed record with zero
re-fetching/re-extraction if the drug is already known, and only calls the
label/FAERS/Orange-Book/Purple-Book fetch functions the FIRST time a drug is
seen. `scripts/apply_source_data.py` (the FAERS/Orange/Purple Book
integration step) was updated the same way.

Cross-source field groups, now populated for every one of the 59 drugs in
the atlas:

- `real_world_safety.faers_summary` — openFDA FAERS report counts,
  seriousness breakdown, top MedDRA reaction terms, reports by year.
  Report volume varies enormously with market exposure time (Adalimumab:
  46,072 reports; Birch Triterpenes, approved 2023-12-18: 0 reports under
  its generic name) — a real finding, not an error. Zero reports is
  recorded as a genuine, confirmed `total_reports: 0` (openFDA's own
  `NOT_FOUND` response for the query), never `null` — `null`/
  `needs_extraction` means "not looked up," not "looked up and found
  none."
- `real_world_safety.drug_characterization` — added cycle 22-23: a
  per-report FAERS `drugcharacterization` breakdown (1=suspect,
  2=concomitant, 3=interacting), computed by pulling every individual
  report and tallying the drug's own array-entry code — a plain
  aggregate `count=` query is wrong here, since openFDA's flattened
  multi-drug-array indexing mixes in co-listed drugs' own codes for any
  report listing more than one drug (see AGENTS.md). Fully filled,
  59/59.
- `exclusivity.regulatory_application` — the NDA/BLA number, the join key
  the other two need.
- `exclusivity.orange_book` — products, patents (number, expiry, use code,
  claims), exclusivity codes with dates; NDAs only (41 small molecules).
- `exclusivity.purple_book` — licensure, BPCIA reference-product /
  interchangeable / orphan exclusivity dates, biosimilars; BLAs only
  (18 biologics; separate shape from Orange Book because BLA exclusivity
  rules differ).

**Every non-`ctgov_api` value here is machine/LLM-extracted, not
hand-verified.** `reviewed_by` is `null` and `confidence` is `< 1.0` on all
of them — they still need the human clinical QA pass (captain + Garvita)
called for in the project brief before being treated as authoritative for
publication.

**Paywalled full-text journal papers were explicitly in scope for the
original 5-drug AD pass.** Each of those trials' primary results
publication was identified (via CT.gov's own `referencesModule` where
present, or PubMed search by trial acronym/author/journal otherwise,
always confirmed against the live API) and a direct fetch was attempted
for every one. Every publisher/repository host tried — NEJM, Wiley, JAMA
Network, JAAD/Elsevier, and a university repository mirror — sits behind a
Cloudflare bot-challenge, one of which escalates to an interactive "Verify
you are human" Turnstile CAPTCHA; this pipeline does not solve that
(defeating an anti-bot check to scrape paywalled content is out of bounds
regardless of the paywall). Two other routes did work: **PMC** (free full
text for 4 of the 13 unique primary-publication PMIDs, via NCBI's
`elink`/`efetch` — not Cloudflare-protected) and **FDA Drugs@FDA
approval-package reviews** (accessdata.fda.gov, also not
Cloudflare-protected, often more granular on protocol detail than the
paper itself). The 22 indications added after that pass did not repeat this
same paywalled-paper research effort — their `publication_extraction`
fills remain confined to the original 17 AD trials. A later deep-extraction
cycle (captain instruction 2026-09-05) did close their real,
non-paywalled `molecule.mechanism_of_action`/`molecule.dosing_regimen`
(openFDA label + CT.gov intervention text) and most of
`population.severity_criteria` (CT.gov eligibility text) gaps to near-zero
without needing paywalled sources — see the Fill status table below. A
second deep-extraction cycle (same captain instruction, continued
2026-09-05) then read the real Study Protocol/SAP PDF posted on CT.gov's
`documentSection` for every one of the 61 non-AD trials that had one
(downloaded via the CDN URL pattern documented in AGENTS.md,
`pdftotext -layout` to convert), and extracted whatever
`design.background_therapy`/`timing_ops.rescue_therapy`/
`timing_ops.study_schedule`/`endpoints.multiplicity_control` content that
real text actually supported — closing 53-64 more trials per field (see the
Fill status table). The remaining gaps split into two real categories: a
trial with no Study Protocol/SAP document posted on CT.gov at all (roughly
half of the corpus), and a trial whose real posted text genuinely states no
rescue-medication concept or no formal multiplicity procedure applies (a
correct finding, not a miss) — both confirmed per-trial, not assumed.

### Trial status (cycle 25)

Three trial-level `ctgov_api` fields record where each trial stands on
CT.gov, so active and non-active trials can be compared per indication:

- `identity.overall_status`: CT.gov `statusModule.overallStatus`,
  verbatim, using CT.gov's own enum (COMPLETED, TERMINATED,
  ACTIVE_NOT_RECRUITING, RECRUITING, ...). No bucketing is applied.
  `source_excerpt` records the fetch date, because a registry status
  changes over time.
- `identity.results_status`: `reported` when CT.gov `hasResults` is true,
  `not_yet_reported` otherwise. An empty `results.*` group is therefore
  never mistaken for a missing extraction.
- `identity.why_stopped`: `statusModule.whyStopped` verbatim for a
  TERMINATED/WITHDRAWN/SUSPENDED trial; a real `null` when the trial did
  not stop early.

Current spread across the 151 trials: 141 COMPLETED, 5 TERMINATED (the 3
Brodalumab AMAGINE trials, "Sponsor decision"; Ketoconazole NCT01110330;
Propranolol NCT00744185), and 5 ACTIVE_NOT_RECRUITING (long-term follow-up
still running after a posted primary readout).

The cycle-25 sweep of RECRUITING / NOT_YET_RECRUITING /
ENROLLING_BY_INVITATION / ACTIVE_NOT_RECRUITING / SUSPENDED / WITHDRAWN
trials for the 4 new indications found none that meets the atlas bar. The
bar is a randomized, placebo/vehicle-controlled Phase 2/3+ trial of a
drug FDA-approved for that indication. That is a real negative finding,
recorded per indication above.

Stopped trials are now in scope under that same design bar, with whatever
they actually posted captured. The pivotal-with-results bar is unchanged
for COMPLETED trials.

### LLM extraction pipeline (cycle 25, `scripts/extraction/`)

Cycle 25's deep fields were extracted by "Luna" (`gpt-6-luna`, via the
Codex CLI) and checked by "Asta" (`gpt-6-astra`). The work ran in three
sequential phases.

1. **Design (Asta).** `spans.py` cuts every source (FDA review/label text,
   protocol/SAP text, CT.gov string leaves) into exact-substring candidate
   spans, with no span crossing a heading, table-row or line boundary.
   `assemble.py` builds each field's sourced value from the span ids Luna
   *selects*. The model never types a quote, a URL or a `source_type`. It
   then runs the mechanical gate (`verify.py`: every quote is verbatim in
   the cited source; the value is schema-valid) before writing
   `patch.json`. Guards added after the first gate pass:
   - `published_results` must be label- or review-sourced;
   - intervention descriptions must equal CT.gov's own;
   - endpoint keys must exist.
2. **Extraction (Luna).** Every target trial, in parallel, following
   `LUNA_INSTRUCTIONS.md`.
3. **Verification (Asta).** One consolidated semantic pass per
   `ASTA_INSTRUCTIONS.md`: arm/dose/timepoint attribution, trial mapping,
   enum choice, and truthful absence. A FAIL or UNCERTAIN verdict reverts
   the field to `needs_extraction`.

Results:
- First pass: 62 fields filled, 41 passed, 21 reverted. All 58 trial and
  drug fields in that run were mechanically clean.
- One redesign-then-re-extract cycle on the 28 rejected or wrongly-absent
  fields: 19 of 22 re-filled fields passed.
- Final: 60 LLM-extracted fields kept, 9 reverted.

An Asta PASS is automated QA only. `reviewed_by` stays `null` on every
field until the human clinical review (captain + Garvita).

### Fill status (all 151 trials, 47 fields each — 7097 sourced values)

Fields fully or near-fully filled across every trial (`ctgov_api` for the
identity/population/design/endpoints/timing_ops/adverse_events core):
`nct_id`, `trial_name`, `official_title`, `sponsor`, `phase`, `drug`,
`intervention_names`, `intervention_type`, `condition`, `min_age_years`,
`max_age_years`, `sex`, `enrollment_count`, `study_type`, `allocation`,
`intervention_model`, `masking`, `number_of_arms`, `primary_endpoints`,
`secondary_endpoints`, `start_date`, `primary_completion_date`,
`completion_date`.

7 fields (`molecule.mechanism_of_action`, `adverse_events.boxed_warning`,
`real_world_safety.{faers_summary,drug_characterization}`,
`exclusivity.{regulatory_application,orange_book,purple_book}`) are
**drug-level `drug_level_ref` pointers as of schema v4** (cycle 23 added
`drug_characterization` as the 7th, following the original 6 from
PR #11) — always "filled" from a trial's own point of view (a pointer
always points somewhere), so their real fill status is now a property of
the DRUG, not the trial; see "Drug-level fill status" below rather than
reading these as 151/151 trial fills.

Fields with real, checkable gaps (numerator = filled, out of 151 trials;
every count below recomputed from `sources.csv` this cycle):

| Field | Filled | Gap reason |
|---|---|---|
| `molecule.dosing_regimen` | 150/151 | real CT.gov intervention description text, matched to each trial's own drug by generic name or known development/compound code, for every trial except one whose intervention text doesn't state a regimen |
| `population.severity_criteria` | 131/151 | real CT.gov eligibility-criteria text now covers PASI/sPGA/ISGA/S-IGA/B-IGA/PGA (psoriasis family), Hurley Stage + AN Count (HS), SIRS (impetigo), HDSS/ASDD (hyperhidrosis), SALT (AA), BPDAI (bullous pemphigoid), GPPGA (GPP), CDASI (dermatomyositis), and lesion-count ranges (acne/rosacea/molluscum/AK) in addition to the original EASI/IGA/BSA (AD); the remaining trials genuinely state no quantitative baseline threshold in their CT.gov text, or their real number uses a unit the current schema has no metric for (percent-of-nail-area, wound size in cm²) |
| `design.background_therapy` | 98/151 | real protocol/SAP PDF text (CT.gov `documentSection`, including a scanned Protocol Summary and one scanned protocol OCR'd with tesseract) covers every indication with a posted Study Protocol/SAP, plus one document-free fallback fill from CT.gov eligibility-criteria text alone (Head Lice/Abametapir); the remaining gap trials have no protocol/SAP document posted on CT.gov at all and no fillable eligibility-text content, so real extraction isn't possible without a different source |
| `endpoints.multiplicity_control` | 91/151 | same PDF-extraction pass closed the real testing-hierarchy/alpha-control text it could, plus a cycle-3 re-read (wider keyword net, one scanned SAP OCR'd with tesseract) and cycle-24's pass over the 13 new Rosacea/Hyperhidrosis/Acne-combo trials (found real serial-gatekeeping/fixed-sequence procedures the first pass's narrower keyword search missed, including one — Zilxi — stated only in the Protocol, not the SAP); remaining gaps are genuine — either no posted document, or the document states no formal multiplicity procedure was used |
| `timing_ops.study_schedule` | 101/151 | same pass closed the real screening/treatment/follow-up period breakdown from every posted protocol; remaining gaps have no protocol/SAP document posted |
| `timing_ops.rescue_therapy` | 78/151 | same pass closed the real rescue-medication rules it could (including trials whose real finding is "rescue explicitly prohibited"), plus one partial fill from CT.gov eligibility-criteria text alone (no posted protocol) confirming rescue therapy is permitted without stating its composition; remaining gaps are a mix of no-posted-document trials and trials whose protocol genuinely states no rescue-medication concept applies (e.g. simple 8-week monotherapy-vs-vehicle designs, or an "escape arm" that a later amendment removed) |
| `adverse_events.serious_adverse_event_rate` | 148/151 | CT.gov posts `eventGroups[]` without per-arm serious counts for a few trials (a genuine gap in what was posted, not a computable zero) |
| `adverse_events.death_rate` | 116/151 | some trials report zero deaths as a genuine null-count edge case in CT.gov's `resultsSection`, not a missing value |
| `adverse_events.discontinuation_due_to_ae_rate` | 112/151 | CT.gov `resultsSection` gap for several trials whose `participantFlowModule` posts milestones only, no `dropWithdraws` section |
| `adverse_events.most_common_adverse_events` | 135/151 | CT.gov `resultsSection` gap for a few trials |
| `results.arms` / `results.arm_results` / `results.effect_estimates` | 148/151 each | schema v3, backfilled from live CT.gov `resultsSection` data for every `hasResults:true` trial; the other 3 (both Efinaconazole/Onychomycosis trials, and the terminated Propranolol pilot NCT00744185) genuinely have no posted results (`identity.results_status: not_yet_reported`). 4 of the 138 filled trials (cycle 23's Cabtreo x2, Epsolay's NCT03564119, Amzeeq's NCT03271021, Twyneo's NCT03761810) have 0 `effect_estimates` — their `resultsSection` genuinely posts no `analyses[]` block for any outcome measure, confirmed against the raw cache, not a build gap |
| `results.published_results` | 8/151 | still out of scope for the CT.gov backfill; cycle 25 filled it for 8 new trials from the FDA label section 14 or FDA review efficacy tables only (never CT.gov registry numbers, which stay in `arm_results` -- enforced by `tests/test_results_backfill.py`), each row joined to its endpoint by `EndpointKey` |
| `identity.overall_status` / `results_status` / `why_stopped` | 151/151 each | cycle 25: CT.gov `statusModule.overallStatus` verbatim, `hasResults` as `reported`/`not_yet_reported`, and `whyStopped` verbatim (a real `null` when the trial did not stop early) -- see "Trial status" below |

**5538 of 6040 genuinely trial-level sourced values are filled with real
data (91.7%); 502 remain `needs_extraction`** (excludes the 7 now-drug-level
fields' 1057 pointer rows, which are always "filled" and would otherwise
inflate this number without measuring anything real; excluding the 3
always-filled cycle-25 status fields too, it is 5085 of 5587, 91.0%) — see `sources.csv`
for the per-trial, per-field breakdown.

#### Drug-level fill status (59 drugs, data/drugs/*.json — see drug_sources.csv)

| Field | Filled | Gap reason |
|---|---|---|
| `mechanism_of_action` | 59/59 | fully filled — real openFDA structured label text for every drug (a few drugs needed the approval-package label PDF fallback since they have no `label.json` entry at all) |
| `boxed_warning` | 59/59 | fully filled — the last 2 gaps (Filsuvez, Vyjuvek) needed a fallback openFDA query term (substance_name/brand_name) since the default term either returned a differently-keyed result or failed outright |
| `faers_summary` | 59/59 | fully filled — every drug has a real, checked FAERS query result, including a confirmed genuine `total_reports: 0` where that's what openFDA returns |
| `drug_characterization` | 59/59 | fully filled (cycle 22-23) — real per-report FAERS `drugcharacterization` (suspect/concomitant/interacting) breakdown for every drug, computed by pulling every individual report and tallying the drug's own array-entry code (a plain aggregate `count=` query cannot do this correctly — see AGENTS.md) |
| `regulatory_application` | 62/62 applications | fully filled — every drug's NDA/BLA join key is on file (Roflumilast's 2 real applications each have their own row) |
| `orange_book` | 44/62 applications | only the NDA small-molecule applications get this field (BLA biologics use `purple_book` instead) |
| `purple_book` | 18/59 | only the BLA biologic drugs get this field (NDA small molecules use `orange_book` instead) |

Every non-`ctgov_api` fill (trial- or drug-level) was produced by
LLM-assisted reading of a real, cited source (CT.gov free text, a
downloaded protocol/SAP PDF, CT.gov's structured results tables, a PMC
full-text paper, an FDA approval-package review, the openFDA label, or a
live openFDA/FDA registry query) — this repo's own pipeline (`scripts/`,
`atlas/`) records exactly which excerpt backs which field — and every one
is `reviewed_by: null` pending the human clinical QA pass (captain +
Garvita) before it's treated as authoritative for publication.

## The files in this repo

Data and pipeline both live here now (post-consolidation):

- `data/trials/<NCT_ID>.json` — one file per trial (151 files), the
  sourced-value format described above (schema v4). 7 fields hold a
  `drug_level_ref` pointer instead of the fact — see `data/drugs/`.
- `data/drugs/<slug>.json` — one file per drug (59 files): the 7 drug-level
  facts, extracted once, referenced by every trial of that drug — see
  "Drug-level records" above.
- `trials.csv` — one row per trial, one column per field (the field's
  `value`, JSON-encoded when structured; `needs_extraction` fields blank;
  the 7 drug-level fields hold their `drug_level_ref` pointer value — join
  `drugs.csv`/`drug_applications.csv` on `drug` to resolve it).
  `results.arm_results`/`results.effect_estimates` are excluded from this
  file's per-trial blob (they have their own dedicated CSVs below — a
  trial's full list can run past Python's csv module field-size limit).
- `sources.csv` — one row per sourced value: `nct_id`, `field`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`,
  `reviewed_by`, `confidence`. 151 trials × 47 fields = 7097 rows (7 of
  those 47 fields are now `drug_level_ref` pointer rows -- see
  `drug_sources.csv` for the real citation).
- `endpoints.csv` — one row per outcome measure × criterion: `measure_type`,
  `scale`, `timepoints`, `analysis_population`, and the `ScoreCriterion`
  columns, so "EASI-75 responders at week 16" is a column filter.
- `severity_criteria.csv` — one row per baseline-severity `ScoreCriterion`.
- `adverse_event_rates.csv` — one row per (trial, arm, measure[, MedDRA
  term]).
- `arm_results.csv` — one row per endpoint × timepoint × arm CT.gov results
  measurement (9,490 rows); keyed on `nct_id` + `endpoint_rank` +
  `endpoint_position` to join `endpoints.csv`'s `rank`/`position` columns.
- `effect_estimates.csv` — one row per endpoint × timepoint × pairwise arm
  comparison (2,804 rows); same join key as `arm_results.csv`.
- `drugs.csv` — one row per drug (59 rows): `mechanism_of_action`,
  `boxed_warning`, `faers_summary`, `drug_characterization`,
  `purple_book`, `trial_ids`.
- `drug_applications.csv` — one row per (drug, application_number) (62
  rows, since Roflumilast, Minocycline and Naftifine each have 2): `regulatory_application`, `orange_book`.
- `drug_sources.csv` — one row per drug-level sourced value: `drug`,
  `field`, `source_type`, `source_url`, `source_excerpt`, `extracted_by`,
  `reviewed_by`, `confidence` (419 rows) — the single citation now backing
  every trial of that drug.
- `docs/SCHEMA.md` / `schema/trial.schema.json` / `schema/drug.schema.json`
  — generated snapshots of the schema v4 field reference (trial and drug
  records; regenerate with `python3 scripts/export_schema.py` after any
  `atlas/schema.py` change).
- `scripts/extraction/` — the cycle-25 span-selection LLM extraction
  pipeline (`spans.py`, `assemble.py`, `verify.py`) and the Luna/Asta
  instructions it runs with (see "LLM extraction pipeline" above).
- `scripts/` / `atlas/` / `tests/` — the fetch/extraction/migration/build
  pipeline, the schema spec, and its test suite (`python3 -m pytest
  tests/`, needs `pytest`).

## Out of scope for this pass

- The human QA pass on top of the LLM-assisted extraction (captain +
  Garvita review of every non-`ctgov_api` value).
- The 502 trial-level fields plus 59 drug-level fields that remain
  `needs_extraction` (see the fill-status tables above) — a mix of
  genuinely unreachable sources (paywalled papers behind Cloudflare, PDF
  tables that don't extract reliably), real, un-worked backlog (a subset of
  endpoints whose title states a responder threshold but the parser hasn't
  classified as `responder_rate` yet — see `AGENTS.md`), and
  `results.published_results` (deliberately, permanently
  out of scope for the CT.gov results backfill — see `AGENTS.md`).
- Further indication candidates not yet live-verified (this is explicitly
  an ongoing effort, not a one-shot; each addition to date was checked
  against real ClinicalTrials.gov and openFDA data before being added, not
  assumed).
- AACT bulk-seeding (a possible future bulk source, not integrated here).
- Any change to the atlas portal UI (`open-derm-trial-atlas` repo).
