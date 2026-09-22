"""Mechanical check of a Luna/Asta patch: quotes exist in sources, schema-valid, provenance rules."""
import json, re, sys, unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # repo root (scripts/extraction/verify.py)
sys.path.insert(0, str(ROOT))
from atlas.schema import FIELD_DOCS, validate, DRUG

SPEC = {p: s for p, s, _ in FIELD_DOCS}
DRUG_SPEC = {"mechanism_of_action": DRUG["properties"]["mechanism_of_action"]["properties"]["value"]}

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("−", "-").replace("­", "")
    s = s.replace("≥", ">=").replace("≤", "<=").replace("≥", ">=").replace("≤", "<=")
    return re.sub(r"[\s\"'`]+", "", s).lower()

def corpus(job):
    parts = [p.read_text(errors="ignore") for p in (job / "sources").glob("*.txt")]
    if (job / "ctgov.json").exists():
        def walk(o):
            if isinstance(o, dict):
                for v in o.values(): yield from walk(v)
            elif isinstance(o, list):
                for v in o: yield from walk(v)
            elif isinstance(o, str): yield o
        parts.extend(walk(json.loads((job / "ctgov.json").read_text())))
    return norm("\n".join(parts))

def quotes(excerpt):
    qs = re.findall(r'"([^"]{12,})"', excerpt or "") + re.findall(r"“([^”]{12,})”", excerpt or "")
    out = []
    for q in qs:  # an ellipsis splits one quote into separately-checkable pieces
        out.extend(p for p in re.split(r"\.\.\.|…|\[\.\.\.\]", q) if len(p.strip()) >= 12)
    return out

def check(job, patch):
    job = Path(job); C = corpus(job)
    urls = {v["url"] for v in json.loads((job / "sources.json").read_text()).values()} if (job / "sources.json").exists() else set()
    urls.add(f"https://clinicaltrials.gov/api/v2/studies/{job.name}")
    lbl = (job / "sources" / "label.txt")
    if lbl.exists():
        m = re.search(r"SOURCE URL: (\S+)", lbl.read_text()); urls.add(m.group(1))
    report = {}
    for path, sv in patch.get("fields", {}).items():
        issues = []
        spec = SPEC.get(path) or DRUG_SPEC.get(path)
        if spec is None: issues.append("unknown field path")
        else:
            errs = validate(sv.get("value"), spec, path)
            if errs: issues.append("schema: " + "; ".join(errs[:4]))
        if set(sv) != {"value", "source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence"}:
            issues.append(f"envelope keys {sorted(sv)}")
        if sv.get("reviewed_by") is not None: issues.append("reviewed_by not null")
        if sv.get("source_type") != "ctgov_api" and not (isinstance(sv.get("confidence"), (int, float)) and sv["confidence"] < 1.0):
            issues.append("confidence must be < 1.0")
        if sv.get("value") is None: issues.append("null value in fields (should be in not_found)")
        if sv.get("source_url") not in urls: issues.append(f"source_url not a job source: {sv.get('source_url')}")
        qs = quotes(sv.get("source_excerpt"))
        missing = [q for q in qs if norm(q) not in C]
        if not qs: issues.append("no verbatim quote in excerpt")
        if missing: issues.append(f"{len(missing)}/{len(qs)} quotes not found: " + " | ".join(m[:90] for m in missing[:3]))
        report[path] = issues
    return report

if __name__ == "__main__":
    job = Path(sys.argv[1]); patch = json.loads((job / (sys.argv[2] if len(sys.argv) > 2 else "patch.json")).read_text())
    for k, v in check(job, patch).items():
        print(("PASS " if not v else "FAIL ") + k, *(["\n     - " + i for i in v]))
    print("not_found:", json.dumps(patch.get("not_found", {}), indent=1)[:2000])
