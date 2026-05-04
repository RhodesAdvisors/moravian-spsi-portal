#!/usr/bin/env python3
"""Parse notion-fetch tool responses (one JSON object per line on stdin) and
emit a single JSON dict keyed by 32-hex page_id matching the deliverables.json schema."""
import json
import re
import sys


def extract_id(url: str):
    if not url:
        return None
    m = re.search(r"([0-9a-f]{32})", url)
    return m.group(1) if m else None


def parse_response(resp: dict) -> dict:
    text = resp.get("text", "") or ""
    url = resp.get("url", "") or ""
    page_id = extract_id(url)
    title = resp.get("title", "") or ""

    # Properties
    props = {}
    m = re.search(r"<properties>\s*(\{.*?\})\s*</properties>", text, re.DOTALL)
    if m:
        try:
            props = json.loads(m.group(1))
        except Exception:
            props = {}

    if (not title) or title == "Untitled":
        title = props.get("Deliverable") or title

    # Owner: first user:// in Owner array
    owner_id = ""
    owners = props.get("Owner")
    if isinstance(owners, str):
        try:
            owners = json.loads(owners)
        except Exception:
            owners = [owners]
    if owners:
        first = str(owners[0])
        mu = re.search(r"user://[a-f0-9-]+", first)
        if mu:
            owner_id = mu.group(0)

    # Departments (Function/Team in deliverables; Department fallback)
    deps = props.get("Function/Team") or props.get("Department") or []
    if isinstance(deps, str):
        try:
            deps = json.loads(deps)
        except Exception:
            deps = []
    if not isinstance(deps, list):
        deps = []

    status = props.get("Status") or ""
    start = props.get("date:Start date:start") or ""
    end = props.get("date:End date:start") or ""

    # Characteristics
    characteristics = ""
    cm = re.search(r"<content>(.*)</content>", text, re.DOTALL)
    if cm:
        content = cm.group(1)
        # Match Characteristics first; fall back to About project only if no Characteristics
        hm = re.search(
            r"#{2,}\s+Characteristics of the Deliverable",
            content,
            re.IGNORECASE,
        )
        if not hm:
            hm = re.search(
                r"#{2,}\s+About project",
                content,
                re.IGNORECASE,
            )
        if hm:
            after = content[hm.end():]
            nm = re.search(r"\n#{2,}\s+", after)
            section = after[: nm.start()] if nm else after

            # Strip noisy XML-like tags
            section = re.sub(r"<empty-block\s*/>", "", section)
            section = re.sub(r"<unknown[^>]*/>", "", section)
            section = re.sub(r"<unknown[^>]*>.*?</unknown>", "", section, flags=re.DOTALL)
            section = re.sub(r"<pdf[^>]*></pdf>", "", section)
            section = re.sub(r"<pdf[^>]*/>", "", section)
            section = re.sub(r"<file[^>]*/>", "", section)
            section = re.sub(r"<details>.*?</details>", "", section, flags=re.DOTALL)
            section = re.sub(r"<span[^>]*>.*?</span>", "", section, flags=re.DOTALL)

            # Detect bullet vs prose: count lines starting with a bullet marker
            raw_lines = section.split("\n")
            bullet_re = re.compile(r"^[\s\t]*[-*•]\s+")
            bullet_lines = []
            non_bullet_lines = []
            for ln in raw_lines:
                if bullet_re.match(ln):
                    stripped = bullet_re.sub("", ln).strip()
                    # Skip empty/placeholder bullets
                    if stripped and stripped not in ("-", "*", "•"):
                        bullet_lines.append(stripped)
                else:
                    if ln.strip():
                        non_bullet_lines.append(ln.strip())

            if bullet_lines:
                # Join bullets with period+space, add trailing period
                joined = []
                for b in bullet_lines:
                    b2 = b.rstrip(" .")
                    if b2:
                        joined.append(b2)
                if joined:
                    section = ". ".join(joined) + "."
                else:
                    section = ""
            else:
                # Prose: collapse whitespace
                section = " ".join(non_bullet_lines)
                section = re.sub(r"\s+", " ", section).strip()

            # Skip placeholder/boilerplate text from About project section
            placeholder = "Provide an overview of the project's goals and context"
            if section == placeholder or section.replace("'", "’") == placeholder.replace("'", "’"):
                section = ""

            characteristics = section

    return {
        "page_id": page_id,
        "title": title or "",
        "characteristics": characteristics,
        "status": status,
        "owner_id": owner_id,
        "departments": deps,
        "start": start,
        "end": end,
    }


def main():
    raw = sys.stdin.read()
    out = {}
    # Each non-empty line is a JSON response object
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            resp = json.loads(line)
        except Exception as e:
            print(f"ERROR parsing line: {e}", file=sys.stderr)
            continue
        rec = parse_response(resp)
        pid = rec.pop("page_id")
        if pid:
            out[pid] = rec
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
