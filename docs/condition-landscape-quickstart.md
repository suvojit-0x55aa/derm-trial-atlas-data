# Condition Landscape Quickstart

This is a standalone tool in this repo. It has nothing to do with the
curated trial atlas in `data/trials/` (that dataset is a hand-verified,
23-cycle curation of completed, placebo-controlled, FDA-approval-pivotal
trials only -- see `AGENTS.md` if you're curious). This tool does the
opposite: given a dermatology condition, it pulls **every** matching trial
on ClinicalTrials.gov, in every status (recruiting, completed, terminated,
withdrawn, not yet recruiting, whatever), with no curation and no
FDA-approval filter. It's raw landscape data, not a hand-picked dataset.

You do not need any special access, API key, or prior context about this
repo to use it. This page is the only thing you need to read.

## What you need installed

- Python 3.10 or newer (`python3 --version`). No third-party packages are
  required -- the script only uses the Python standard library.
- (Optional) `pdftotext`, from the `poppler` package, only if you want the
  script to also download and convert trial protocol/SAP PDFs to text.
  On macOS: `brew install poppler`. On Debian/Ubuntu: `apt install
  poppler-utils`. If it isn't installed, the script still works -- it
  just skips the PDF-to-text conversion step and leaves the PDFs
  un-downloaded unless you ask for them (see below).
- Internet access to `clinicaltrials.gov` (a public API, no key needed).

## Run it

From the root of this repo:

```bash
python3 scripts/fetch_condition_landscape.py --condition psoriasis
```

That's it. It will:

1. Query the live ClinicalTrials.gov API for every trial matching
   "psoriasis" (any status), paginating automatically.
2. For each trial, fetch its linked publications and posted document list
   (Protocol / SAP / Informed Consent Form, if any exist).
3. Write everything to `data/condition_landscape/psoriasis/`.

A run for a common condition like "psoriasis" (thousands of trials on
CT.gov) can take 15-30 minutes because of the polite delay between API
requests -- this is intentional (see "Being polite to the API" below), not
a bug. A narrower condition (e.g. "hidradenitis suppurativa") finishes in
well under a minute.

### Multiple conditions in one run

```bash
python3 scripts/fetch_condition_landscape.py --condition psoriasis --condition eczema
# or, equivalently:
python3 scripts/fetch_condition_landscape.py --condition "psoriasis,eczema"
```

Each condition gets its own output folder under `data/condition_landscape/`.

### Useful flags

| Flag | What it does |
|---|---|
| `--max-trials N` | Stop after N trials for this condition -- use this for a quick test run before committing to a full pull on a common condition. |
| `--skip-supplementary` | Skip the per-trial publications/documents lookup. Much faster, listing data only. |
| `--fetch-protocol-pdfs` | Also download and convert (via `pdftotext`) any posted Study Protocol / SAP / ICF PDFs. Off by default, since a common condition can have hundreds of trials with posted documents and these PDFs are often multiple megabytes each. |
| `--max-protocol-pdfs N` | Cap on how many PDFs `--fetch-protocol-pdfs` will download for a single condition (default 25). |
| `--out-dir PATH` | Write somewhere other than `data/condition_landscape/`. |
| `--sleep SECONDS` | Delay between API requests (default ~0.34s). Raise this if you hit errors from the API; lower it at your own risk. |

Example: a quick 10-trial smoke test with everything (docs included):

```bash
python3 scripts/fetch_condition_landscape.py \
  --condition "hidradenitis suppurativa" \
  --max-trials 10 \
  --fetch-protocol-pdfs
```

## What "condition" means as input

It's passed straight through to ClinicalTrials.gov's own
`query.cond=<condition>` search parameter -- the same free-text condition
search you'd use on clinicaltrials.gov's website. Use a plain, common
name: `psoriasis`, `atopic dermatitis`, `eczema`, `hidradenitis
suppurativa`, `alopecia areata`, `vitiligo`. There's no fixed list to pick
from and no validation against a controlled vocabulary -- if CT.gov's own
search would find trials for it, so will this script. A misspelled or
overly narrow condition name will just return zero or very few trials, not
an error; if that happens, try the term you'd type into
clinicaltrials.gov's own search box.

## What you get out

```
data/condition_landscape/<condition-slug>/
    manifest.json           # this run: condition, fetch date, trial count, status breakdown
    drugs.json               # every distinct drug/biologic tested across these trials
    trials/<NCT_ID>.json      # one file per trial
    documents/<NCT_ID>/       # only present with --fetch-protocol-pdfs
        Prot_000.pdf
        Prot_000.txt          # only if pdftotext is installed
```

`manifest.json` is the run summary -- open this first:

```json
{
  "condition": "Psoriasis",
  "trial_count": 2551,
  "status_breakdown": {"COMPLETED": 1400, "RECRUITING": 380, "TERMINATED": 210, "...": "..."},
  "drug_count": 340,
  "fetched_at": "2026-09-16T08:53:35Z"
}
```

`drugs.json` lists every distinct drug/biologic intervention found across
every trial for the condition, with which trials tested it:

```json
{
  "drugs": [
    {"name": "Dupilumab", "trial_count": 12, "nct_ids": ["NCT...", "..."]}
  ]
}
```

This is **not** filtered to FDA-approved drugs. An in-flight, terminated,
or long-abandoned drug program shows up here exactly the same as an
approved one -- that's the point of this tool. If you want to know whether
a drug in this list is FDA-approved, that's a separate question this tool
doesn't answer (the curated atlas in `data/trials/` does, but only for the
drugs it has already individually verified).

Each `trials/<NCT_ID>.json` is one trial: its status (including
`why_stopped` for terminated/withdrawn trials), sponsor, phase, every
intervention arm, eligibility criteria (full free text, not parsed),
primary/secondary outcome measures, enrollment, locations, and whatever
linked publications and posted documents CT.gov has for it. A field is
either what the live API actually returned or `null` -- there's no
placeholder value meaning "needs follow-up," because this tool doesn't do
follow-up extraction. A trial that's still recruiting will have a lot of
`null`s (no results, no completion date yet) -- that's correct, not
missing data.

## Being polite to the API

ClinicalTrials.gov is a free public service with no API key or hard rate
limit, but the script sleeps briefly (~0.34s by default) between requests
so it doesn't hammer it, especially for a common condition with hundreds
or thousands of trials. Don't set `--sleep` to 0 for a large condition.

## Re-running

Re-running the same condition overwrites its output folder's trial files,
`drugs.json`, and `manifest.json` with a fresh pull (new `fetched_at`
timestamps) -- CT.gov trial statuses change over time (a RECRUITING trial
today may be COMPLETED next month), so there's no incremental/diff mode.
Downloaded protocol PDFs (`--fetch-protocol-pdfs`) are cached by filename
and not re-downloaded on a re-run.

## Running the tests

If you want to verify the fetcher's parsing/pagination logic without
hitting the live API:

```bash
python3 -m unittest tests.test_condition_landscape -v
```

These tests mock the ClinicalTrials.gov API entirely -- no network access
needed to run them.

## Example prompt for your own coding agent

If you're handing this repo to someone else's coding agent (any brand, not
just Claude), this is a self-contained prompt that should work with zero
extra context beyond this file:

> Run `python3 scripts/fetch_condition_landscape.py --condition psoriasis
> --condition eczema` in this repo (see
> `docs/condition-landscape-quickstart.md` for what it does and what flags
> are available), then tell me what it produced: how many trials per
> condition, the status breakdown, and how many distinct drugs it found.
