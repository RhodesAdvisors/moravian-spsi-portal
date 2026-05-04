"""
build_site.py — Rebuild index.html for the SPSI Project Portal.

Reads:
  - projects_from_notion.json   (live snapshot from Notion)
  - deliverables.json           (fetched deliverable pages with characteristics)
  - user_id_to_name_map.json    (Notion user IDs -> display names)
  - _template.html              (the site template; created automatically on first run from current index.html)

Writes:
  - index.html                  (deployable single-file site)

Usage:
  python3 build_site.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_FILE = os.path.join(HERE, "projects_from_notion.json")
DELIV_FILE = os.path.join(HERE, "deliverables.json")
USER_FILE = os.path.join(HERE, "user_id_to_name_map.json")
TEMPLATE_FILE = os.path.join(HERE, "_template.html")
OUT_FILE = os.path.join(HERE, "index.html")


def url_to_id(u: str) -> str:
    """Extract the 32-hex page ID from a Notion URL."""
    if not u:
        return ""
    m = re.search(r"/p/([a-f0-9]{32})", u)
    if m:
        return m.group(1)
    m = re.search(r"/p/([a-f0-9-]+)", u)
    if m:
        return m.group(1).replace("-", "")
    # Fallback: any 32-hex run anywhere in the URL (notion.so/HEX format)
    m = re.search(r"([a-f0-9]{32})", u)
    if m:
        return m.group(1)
    return ""


def to_mdY(iso: str) -> str:
    """ISO YYYY-MM-DD -> MM/DD/YYYY (matches existing site format). Returns '' for empty input."""
    if not iso:
        return ""
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return d.strftime("%m/%d/%Y")
    except Exception:
        return ""


def name_for(user_id: str, user_map: dict) -> str:
    """Resolve a user:// or space_permission_group- ID to a display name."""
    if not user_id:
        return ""
    if user_id in user_map:
        return user_map[user_id]
    # Heuristic for permission groups not in map
    if user_id.startswith("space_permission_group"):
        return "Team"
    return ""


def build_projects(projects_raw, deliverables, user_map):
    """Convert the raw Notion snapshot into the PROJECTS array the site consumes."""
    out = []
    for p in projects_raw:
        owner_name = name_for(p.get("owner_id", ""), user_map)

        deliv_records = []
        for url in p.get("deliverables", []):
            did = url_to_id(url)
            d = deliverables.get(did)
            if not d:
                # Page exists in projects' deliverable list but isn't in cache.
                # Show the URL stub as title so the project still renders.
                deliv_records.append({"title": "(deliverable not cached)", "characteristics": ""})
                continue
            deliv_records.append({
                "title": d.get("title") or "",
                "characteristics": d.get("characteristics") or "",
            })

        out.append({
            "name": p.get("name", ""),
            "status": p.get("status", ""),
            "start": to_mdY(p.get("start", "")),
            "end": to_mdY(p.get("end", "")),
            "owner": owner_name,
            "departments": sorted(p.get("departments", [])),
            "project_description": p.get("project_description", ""),
            "deliverables": deliv_records,
        })
    return out


# -----------------------------------------------------------------------------
# Template handling
# -----------------------------------------------------------------------------
# Single-line, non-greedy: the PROJECTS = [...] declaration sits on one line in the template.
# Using DOTALL+greedy here would eat the rest of the JS (drawer code, etc.) up to the LAST `];`.
PROJECTS_LINE_RE = re.compile(r"^const\s+PROJECTS\s*=\s*\[.*?\];\s*$", re.MULTILINE)

# Patches the openDrawer function to render Project Description (above the meta grid)
# and a small italic Characteristics paragraph beneath each deliverable title.
DRAWER_PATCH_MARKER = "/* drawer:project-desc-and-characteristics-patch v1 */"

DRAWER_PATCH = """/* drawer:project-desc-and-characteristics-patch v1 */
.drawer-project-desc {
  font-style: italic;
  color: var(--ink-mute);
  font-size: 14px;
  line-height: 1.55;
  padding: 14px 0 22px;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 22px;
}
.deliv-item .deliv-characteristics {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  font-style: italic;
  color: var(--ink-mute);
  line-height: 1.5;
}
"""

NEW_DELIV_RENDER = (
    "  const delivHTML = p.deliverables.length\n"
    "    ? `<ul class=\"deliv-list\">${p.deliverables.map(d => `\n"
    "        <li class=\"deliv-item\">\n"
    "          <span class=\"bullet\"></span>\n"
    "          <span class=\"text\">${escHTML(d.title)}${d.characteristics ? `<span class=\"deliv-characteristics\">${escHTML(d.characteristics)}</span>` : ''}</span>\n"
    "        </li>`).join('')}</ul>`\n"
    "    : `<div class=\"no-delivs\">No deliverables tracked for this project.</div>`;"
)

OLD_DELIV_RENDER_RE = re.compile(
    r"  const delivHTML = p\.deliverables\.length\n"
    r"    \? `<ul class=\"deliv-list\">\$\{p\.deliverables\.map\(d => `\n"
    r"        <li class=\"deliv-item\">\n"
    r"          <span class=\"bullet\"></span>\n"
    r"          <span class=\"text\">\$\{escHTML\(d\.title\)\}</span>\n"
    r"        </li>`\)\.join\(''\)\}</ul>`\n"
    r"    : `<div class=\"no-delivs\">No deliverables tracked for this project\.</div>`;"
)

# We add the Project Description block right at the top of drawer-body innerHTML.
# Insert just after `document.getElementById('drawer-body').innerHTML = ` `\n` and before `<div class="drawer-meta-grid">`
OLD_DRAWER_HEAD_RE = re.compile(
    r"(document\.getElementById\('drawer-body'\)\.innerHTML\s*=\s*`\s*\n\s*)<div class=\"drawer-meta-grid\">"
)
# Use a callable replacement so we don't have to escape `\1`/quotes inside a raw string.
def _new_drawer_head(match):
    return (
        match.group(1)
        + '${p.project_description ? `<div class="drawer-project-desc">${escHTML(p.project_description)}</div>` : \'\'}\n'
        + '    <div class="drawer-meta-grid">'
    )


def patch_template(html: str) -> str:
    """Idempotently apply the drawer patch to the template HTML."""
    if DRAWER_PATCH_MARKER in html:
        return html  # already patched

    # Inject CSS just before the closing </style> tag
    html = re.sub(r"(</style>)", DRAWER_PATCH + r"\1", html, count=1)

    # Replace the deliverable render block
    if not OLD_DELIV_RENDER_RE.search(html):
        raise SystemExit("Template missing the expected deliverable render block. "
                         "Either the template was already modified by hand or the source "
                         "site changed shape. Aborting.")
    html = OLD_DELIV_RENDER_RE.sub(NEW_DELIV_RENDER, html, count=1)

    # Inject Project Description above the meta grid
    if not OLD_DRAWER_HEAD_RE.search(html):
        raise SystemExit("Template missing the drawer head opener. Aborting.")
    html = OLD_DRAWER_HEAD_RE.sub(_new_drawer_head, html, count=1)

    return html


def replace_projects_block(html: str, projects) -> str:
    """Swap in the new const PROJECTS = [...]; line."""
    new_line = "const PROJECTS = " + json.dumps(projects, ensure_ascii=False) + ";"
    if not PROJECTS_LINE_RE.search(html):
        raise SystemExit("Could not find `const PROJECTS = [...]` in template. Aborting.")
    return PROJECTS_LINE_RE.sub(new_line, html, count=1)


def stamp_refresh_date(html: str) -> str:
    """Update the hardcoded TODAY date constant so 'Last refreshed' shows today.

    The original site has: `const TODAY = new Date(2026, 3, 28);`
    We replace it with today's date.
    """
    today = datetime.now()
    new_today = f"const TODAY = new Date({today.year}, {today.month - 1}, {today.day});"
    return re.sub(r"const\s+TODAY\s*=\s*new\s+Date\([^)]+\);", new_today, html, count=1)


def main():
    if not os.path.exists(TEMPLATE_FILE):
        # First-time bootstrap: copy the current index.html to _template.html as the canonical template.
        if not os.path.exists(OUT_FILE):
            sys.exit(f"No template found at {TEMPLATE_FILE} and no existing index.html to bootstrap from.")
        with open(OUT_FILE) as f:
            tpl = f.read()
        with open(TEMPLATE_FILE, "w") as f:
            f.write(tpl)
        print(f"Bootstrapped template from existing index.html -> {TEMPLATE_FILE}")

    with open(TEMPLATE_FILE) as f:
        template = f.read()

    with open(PROJ_FILE) as f:
        projects_raw = json.load(f)
    with open(DELIV_FILE) as f:
        deliverables = json.load(f)
    with open(USER_FILE) as f:
        user_map = json.load(f)

    projects = build_projects(projects_raw, deliverables, user_map)

    html = patch_template(template)
    html = replace_projects_block(html, projects)
    html = stamp_refresh_date(html)

    with open(OUT_FILE, "w") as f:
        f.write(html)

    deliv_count = sum(len(p["deliverables"]) for p in projects)
    char_count = sum(1 for p in projects for d in p["deliverables"] if d["characteristics"])
    print(f"Wrote {OUT_FILE}")
    print(f"  Projects: {len(projects)}")
    print(f"  Deliverables: {deliv_count}")
    print(f"  Deliverables with Characteristics text: {char_count}")
    print(f"  Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
