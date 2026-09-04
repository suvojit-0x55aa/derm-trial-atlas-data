"""
Structured values for the two openFDA-label fields:

molecule.mechanism_of_action
    {
      "modality": "monoclonal_antibody" | "small_molecule",
      "drug_class": "IL-4Rα antagonist" | "IL-13 antagonist" | "JAK inhibitor" | ...,
      "antibody_isotype": "IgG4" | null,
      "binding_targets": ["IL-4Rα"],           # what the molecule physically binds to
      "pathway_cytokines": ["IL-4", "IL-13"],  # cytokines named in the label's mechanism text
      "receptor_subunits": ["IL-4Rα"],         # receptor subunits named
      "kinases_inhibited": ["JAK1"],           # for kinase inhibitors: the kinase(s) it inhibits
      "selectivity": [{"over": "JAK2", "fold": 28}],   # only when the label states fold-selectivity
      "reversible": true | null,
      "mechanism_established": false | null,   # label says "not definitively established"
      "label_section": "12.1"
    }

adverse_events.boxed_warning
    {
      "present": true | false,
      "title": "SERIOUS INFECTIONS, MORTALITY, MALIGNANCY, ...",
      "warning_categories": ["serious_infections", "mortality", "malignancy", "mace", "thrombosis"],
      "referenced_label_sections": ["5.1", "5.2", ...],
      "product_names": ["CIBINQO"]
    }

The full label text stays in `source_excerpt` as provenance.
"""
import re

MODALITIES = ("monoclonal_antibody", "small_molecule", "fusion_protein", "other")
WARNING_CATEGORIES = {
    "serious_infections": r"SERIOUS INFECTIONS",
    "mortality": r"MORTALITY",
    "malignancy": r"MALIGNANC",
    "mace": r"MAJOR ADVERSE CARDIOVASCULAR EVENTS|\bMACE\b",
    "thrombosis": r"THROMBOSIS",
    "suicidal_ideation": r"SUICID",
    "hepatotoxicity": r"HEPATOTOXICITY",
    "embryo_fetal_toxicity": r"EMBRYO-?FETAL",
}
TARGET_TOKENS = [
    "IL-4Rα", "IL-13Rα1", "IL-13Rα2", "IL-13", "IL-4", "IL-31RA", "IL-31", "IL-17A", "IL-17F",
    "IL-23", "IL-12", "IL-36R", "OX40L", "OX40", "TSLP", "TNF", "JAK1", "JAK2", "JAK3", "TYK2",
    "PDE4", "AhR", "IgE", "S1P", "CD20",
]


def _entities(sentence):
    found = []
    for tok in TARGET_TOKENS:
        if re.search(re.escape(tok) + r"(?![A-Za-z0-9α])", sentence) and tok not in found:
            found.append(tok)
    return found


def _normalize_entities(body):
    body = re.sub(r"interleukin \(IL\)-(\d+)", r"IL-\1", body)
    body = re.sub(r"interleukin-(\d+)", r"IL-\1", body)
    return body


def parse_mechanism(text: str) -> dict:
    t = text.replace("\n", " ")
    section = re.match(r"\s*(\d+\.\d+)\s+Mechanism of Action", t)
    body = _normalize_entities(t[section.end():] if section else t)
    mab = bool(re.search(r"monoclonal (?:\w+ )?antibody", body, re.I))
    jak = bool(re.search(r"Janus kinase \(JAK\) inhibitor|JAK inhibitor", body))
    iso = re.search(r"\b(IgG[1-4])\b", body)
    bind = re.search(r"\bbind(?:s|ing)?\b(?: with [^.]*?)? to (?:the )?(?:human )?([^ ,.]+)", body)
    binding = [e for e in _entities(bind.group(1)) if bind] if bind else []
    cytokines = [e for e in _entities(body) if re.match(r"IL-\d+$|TSLP|TNF|IgE", e)]
    receptors = [e for e in _entities(body) if "R" in e and e.startswith(("IL-", "OX40", "PDE", "AhR"))]
    kin = re.search(r"(?:inhibits|inhibitory potency at|selective for) ((?:JAK\d|TYK2)(?:(?:,| and) (?:JAK\d|TYK2))*)", body)
    kinases = _entities(kin.group(1)) if kin else []
    selectivity = [
        {"over": (m.group(1)).replace("tyrosine kinase (TYK) 2", "TYK2"),
         "fold": int(m.group(2).lstrip("><")),
         "comparator": ">" if m.group(2).startswith(">") else "=="}
        for m in re.finditer(r"(?:over )?(JAK\d|tyrosine kinase \(TYK\) 2|TYK2) \(([><]?\d+)-fold\)", body)
    ]
    if mab:
        modality = "monoclonal_antibody"
        drug_class = f"{binding[0]} antagonist" if binding else "monoclonal antibody"
    elif jak:
        modality, drug_class = "small_molecule", "JAK inhibitor"
    else:
        modality, drug_class = "other", None
    return {
        "modality": modality,
        "drug_class": drug_class,
        "antibody_isotype": iso.group(1) if iso else None,
        "binding_targets": binding,
        "pathway_cytokines": cytokines,
        "receptor_subunits": receptors,
        "kinases_inhibited": kinases,
        "selectivity": selectivity,
        "reversible": True if re.search(r"reversibly inhibits", body) else None,
        "mechanism_established": False if re.search(r"not (?:been )?definitively established|not currently known", body) else None,
        "label_section": section.group(1) if section else None,
    }


def parse_boxed_warning(text) -> dict:
    if text is None:
        return {"present": False, "title": None, "warning_categories": [],
                "referenced_label_sections": [], "product_names": []}
    t = text.replace("\n", " ")
    words = t.split()
    title_words = []
    for w in words[1:] if words and words[0].startswith("WARNING") else words:
        if w == "and" or w.startswith("(") or re.fullmatch(r"[A-Z][A-Z,()]*,?", w):
            title_words.append(w)
        else:
            break
    plain = [w.rstrip(",") for w in title_words]
    for i in range(1, len(plain)):
        if plain[i:i + 2] == plain[0:2]:
            title_words = title_words[:i]
            break
    while title_words and title_words[-1].rstrip(":") == "WARNING":
        title_words.pop()
    title = " ".join(title_words).strip() or None
    cats = [c for c, pat in WARNING_CATEGORIES.items() if re.search(pat, title or t[:400])]
    sections = []
    for m in re.finditer(r"\(\s*(5\.\d+)\s*\)", t):
        if m.group(1) not in sections:
            sections.append(m.group(1))
    products = []
    for m in re.finditer(r"\b([A-Z]{4,}(?: LQ)?)\b", t):
        name = m.group(1)
        if name in ("WARNING", "SERIOUS", "INFECTIONS", "MORTALITY", "MALIGNANCY", "MALIGNANCIES", "MAJOR", "ADVERSE", "CARDIOVASCULAR", "EVENTS", "THROMBOSIS", "MACE", "NMSC"):
            continue
        if name not in products:
            products.append(name)
    return {
        "present": True,
        "title": title,
        "warning_categories": cats,
        "referenced_label_sections": sections,
        "product_names": products,
    }
