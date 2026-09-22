#!/usr/bin/env python3
"""Deterministic, source-bound evidence candidates. Python standard library only."""
import argparse
import json
import re
import unicodedata
from pathlib import Path


def collapse(text):
    return " ".join(text.split())


def is_double_quote(char):
    # Include fullwidth quotes (NFKC), curly quotes and less common quotation marks.
    return char == '"' or '"' in unicodedata.normalize("NFKC", char) or (
        char in '“”„‟«»〝〞〟❝❞'
    )


def unquote(text):
    return "".join(c for c in text if not is_double_quote(c))


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{path}: duplicate JSON key {key!r}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"{path}: non-finite JSON number {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=unique, parse_constant=invalid)


def file_key(file):
    return re.sub(r"[^A-Z0-9_]+", "_", Path(file).stem.upper()).strip("_")


def string_leaves(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            suffix = "." + key if re.fullmatch(r"[A-Za-z_]\w*", key) else "[" + json.dumps(key) + "]"
            yield from string_leaves(child, path + suffix)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from string_leaves(child, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, value


def fragments(text):
    """Split, never rewrite: tags, quotes, and sentence boundaries are cuts."""
    # Tag boundaries keep HTML cells/rows separate; entities are never decoded.
    for raw in re.split(r"</?[A-Za-z][^>]*>|<!--.*?-->", text):
        start = 0
        for i, char in enumerate(raw):
            if is_double_quote(char):
                yield from sentences(raw[start:i])
                start = i + 1
        yield from sentences(raw[start:])


def sentences(text):
    # Decimal points remain intact; abbreviation splits are conservative extra cuts.
    for part in re.split(r"(?<=[.!?])\s+(?=\S)", text):
        part = collapse(part)
        if part:
            yield part


def segments(text, section):
    # Every physical line is a hard boundary: safe even for ambiguous PDF tables,
    # headings and list items. Wrapped sentences require multiple span selections.
    for line_no, line in enumerate(text.splitlines(), 1):
        clean = collapse(line)
        if not clean:
            continue
        heading = (clean.startswith("#") or clean.endswith(":") or
                   (len(clean) < 140 and clean.isupper()) or
                   re.match(r"^\d+(?:\.\d+)*\s+[A-Z][A-Za-z /,&-]{2,100}$", clean))
        if heading:
            section = clean
        for part in fragments(line):
            yield part, line_no, section


def candidates(job):
    """Return {file_key: records}; used again at assembly to reject stale/tampered spans."""
    job = Path(job)
    files = sorted(p.relative_to(job).as_posix() for p in (job / "sources").glob("*.txt"))
    if (job / "ctgov.json").exists():
        files.append("ctgov.json")
    result = {}
    for file in files:
        key = file_key(file)
        if not key or key in result:
            raise ValueError(f"file_key collision for {file}; rename the source and its manifest entry")
        records = []
        leaves = string_leaves(read_json(job / file)) if file == "ctgov.json" else [
            (None, (job / file).read_text(encoding="utf-8"))
        ]
        for json_path, text in leaves:
            for part, line_no, section in segments(text, json_path or file):
                # For JSON, always retain the leaf path, even under a local heading.
                if json_path and section != json_path:
                    section = f"{json_path} / {section}"
                records.append({"id": f"{key}:{len(records) + 1:04d}", "file": file,
                                "text": part, "line": line_no, "section": section})
        result[key] = records
    return result


def build(job):
    data = candidates(job)
    out = Path(job) / "spans"
    out.mkdir(exist_ok=True)
    for key, records in data.items():
        target = out / f"{key}.jsonl"
        temp = target.with_suffix(".jsonl.tmp")
        temp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        temp.replace(target)
    # Remove obsolete generated files so searches cannot return removed evidence.
    for path in out.glob("*.jsonl"):
        if path.stem not in data:
            path.unlink()
    return data


def load(job):
    expected = candidates(job)
    actual_keys = {p.stem for p in (Path(job) / "spans").glob("*.jsonl")}
    if actual_keys != set(expected):
        raise ValueError("missing/stale spans; run spans.py build <job>")
    for key, records in expected.items():
        path = Path(job) / "spans" / f"{key}.jsonl"
        actual = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if actual != records:
            raise ValueError(f"{path}: stale or altered spans; rebuild and reselect evidence")
    return {r["id"]: r for records in expected.values() for r in records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="build spans/*.jsonl").add_argument("job", type=Path)
    search = sub.add_parser("search", help="search text and section/path (case insensitive)")
    search.add_argument("job", type=Path)
    search.add_argument("regex")
    args = parser.parse_args()
    try:
        if args.command == "build":
            for key, records in build(args.job).items():
                print(f"{key}: {len(records)} spans")
        else:
            pattern = re.compile(args.regex, re.I)
            for record in load(args.job).values():
                if pattern.search(record["text"]) or pattern.search(record["section"]):
                    print(f'{record["id"]}\t{record["file"]}:{record["line"]}\t'
                          f'{record["section"]}\t{record["text"]}')
    except (OSError, ValueError, re.error) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
