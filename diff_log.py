"""
diff_log.py — compute a human-readable changelog between two snapshots of
projects_from_notion.json + deliverables.json, and emit Notion-flavored Markdown.

Inputs (all in this folder):
  - projects_from_notion.json.previous   (yesterday's projects snapshot)
  - projects_from_notion.json            (today's projects snapshot)
  - deliverables.json.previous           (yesterday's deliverables cache)
  - deliverables.json                    (today's deliverables cache)
  - user_id_to_name_map.json             (for resolving owner IDs to names)

Output:
  - prints the markdown to stdout (the scheduled task captures it)
  - if no changes, prints exactly "NO_CHANGES" so the task can branch on it
"""

import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path, default):
    p = os.path.join(HERE, path)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def url_to_id(u):
    if not u:
        return ""
    m = re.search(r"/p/([a-f0-9]{32})", u)
    if m:
        return m.group(1)
    m = re.search(r"/p/([a-f0-9-]+)", u)
    if m:
        return m.group(1).replace("-", "")
    return ""


def display_project(name):
    """Strip the "Moravian - " / "SPSI - " prefixes for readability."""
    n = name.replace(" ", " ").strip()
    n = re.sub(r"^Moravian\s*-\s*", "", n)
    n = re.sub(r"^SPSI\s*-\s*", "", n)
    return n


def fmt_date(s):
    return s if s else "(no date)"


def main():
    old_projects = load("projects_from_notion.json.previous", [])
    new_projects = load("projects_from_notion.json", [])
    old_delivs = load("deliverables.json.previous", {})
    new_delivs = load("deliverables.json", {})
    user_map = load("user_id_to_name_map.json", {})

    def name_for(uid):
        if not uid:
            return "(no owner)"
        return user_map.get(uid, "(unknown)")

    # Index by project name (used as stable key)
    old_by_name = {p["name"]: p for p in old_projects}
    new_by_name = {p["name"]: p for p in new_projects}

    added_projects = [p for n, p in new_by_name.items() if n not in old_by_name]
    removed_projects = [p for n, p in old_by_name.items() if n not in new_by_name]

    project_changes = []
    deliverable_link_changes = []  # (parent_project, kind, deliv_title)
    for n, np in new_by_name.items():
        op = old_by_name.get(n)
        if not op:
            continue

        changes = []

        if op.get("status") != np.get("status"):
            changes.append(("status", op.get("status") or "(empty)", np.get("status") or "(empty)"))

        if op.get("start") != np.get("start"):
            changes.append(("start date", fmt_date(op.get("start")), fmt_date(np.get("start"))))
        if op.get("end") != np.get("end"):
            changes.append(("end date", fmt_date(op.get("end")), fmt_date(np.get("end"))))

        if op.get("owner_id") != np.get("owner_id"):
            changes.append(("owner", name_for(op.get("owner_id")), name_for(np.get("owner_id"))))

        if set(op.get("departments", [])) != set(np.get("departments", [])):
            changes.append((
                "departments",
                ", ".join(sorted(op.get("departments", []))) or "(none)",
                ", ".join(sorted(np.get("departments", []))) or "(none)",
            ))

        if op.get("project_description", "") != np.get("project_description", ""):
            old_desc = (op.get("project_description") or "").strip()
            new_desc = (np.get("project_description") or "").strip()
            if not old_desc and new_desc:
                changes.append(("description", "(added)", new_desc[:140] + ("…" if len(new_desc) > 140 else "")))
            elif old_desc and not new_desc:
                changes.append(("description", old_desc[:80] + "…", "(removed)"))
            else:
                changes.append(("description", "(updated)", new_desc[:140] + ("…" if len(new_desc) > 140 else "")))

        if changes:
            project_changes.append((n, changes))

        # Deliverable link changes (added/removed at the project level)
        old_links = set(op.get("deliverables", []))
        new_links = set(np.get("deliverables", []))
        for url in sorted(new_links - old_links):
            did = url_to_id(url)
            title = (new_delivs.get(did) or {}).get("title") or "(untitled deliverable)"
            deliverable_link_changes.append((n, "added", title))
        for url in sorted(old_links - new_links):
            did = url_to_id(url)
            title = (old_delivs.get(did) or {}).get("title") or "(untitled deliverable)"
            deliverable_link_changes.append((n, "removed", title))

    # Internal changes to existing deliverable pages
    deliv_field_changes = []  # (deliv_title, [(field, old, new), ...])
    for did, nd in new_delivs.items():
        od = old_delivs.get(did)
        if not od:
            continue  # already counted as new via project link
        changes = []
        if od.get("title") != nd.get("title"):
            changes.append(("title", od.get("title") or "(empty)", nd.get("title") or "(empty)"))
        if od.get("status") != nd.get("status"):
            changes.append(("status", od.get("status") or "(empty)", nd.get("status") or "(empty)"))
        if od.get("start") != nd.get("start"):
            changes.append(("start date", fmt_date(od.get("start")), fmt_date(nd.get("start"))))
        if od.get("end") != nd.get("end"):
            changes.append(("end date", fmt_date(od.get("end")), fmt_date(nd.get("end"))))
        if od.get("owner_id") != nd.get("owner_id"):
            changes.append(("owner", name_for(od.get("owner_id")), name_for(nd.get("owner_id"))))
        if changes:
            deliv_field_changes.append((nd.get("title") or "(untitled)", changes))

    # Detect "no changes"
    if (not added_projects and not removed_projects and not project_changes
            and not deliverable_link_changes and not deliv_field_changes):
        print("NO_CHANGES")
        return

    # Build markdown
    lines = []
    today = datetime.now().strftime("%Y-%m-%d")
    lines.append(f"### {today}")
    lines.append("")

    if added_projects:
        lines.append(f"**New projects ({len(added_projects)}):**")
        for p in added_projects:
            disp = display_project(p["name"])
            owner = name_for(p.get("owner_id"))
            status = p.get("status") or "(no status)"
            dates = ""
            if p.get("start") or p.get("end"):
                dates = f" — {fmt_date(p.get('start'))} → {fmt_date(p.get('end'))}"
            lines.append(f"- **{disp}** · {status} · {owner}{dates}")
        lines.append("")

    if removed_projects:
        lines.append(f"**Projects removed ({len(removed_projects)}):**")
        for p in removed_projects:
            lines.append(f"- {display_project(p['name'])}")
        lines.append("")

    if project_changes:
        lines.append(f"**Project updates ({len(project_changes)}):**")
        for name, changes in project_changes:
            disp = display_project(name)
            for field, old, new in changes:
                lines.append(f"- **{disp}** — {field}: {old} → {new}")
        lines.append("")

    # Group deliverable link changes by project for readability
    if deliverable_link_changes:
        added_by_proj = {}
        removed_by_proj = {}
        for parent, kind, title in deliverable_link_changes:
            target = added_by_proj if kind == "added" else removed_by_proj
            target.setdefault(parent, []).append(title)
        if added_by_proj:
            total = sum(len(v) for v in added_by_proj.values())
            lines.append(f"**New deliverables ({total}):**")
            for parent, titles in added_by_proj.items():
                lines.append(f"- Under *{display_project(parent)}*:")
                for t in titles:
                    lines.append(f"    - {t}")
            lines.append("")
        if removed_by_proj:
            total = sum(len(v) for v in removed_by_proj.values())
            lines.append(f"**Deliverables unlinked ({total}):**")
            for parent, titles in removed_by_proj.items():
                lines.append(f"- From *{display_project(parent)}*:")
                for t in titles:
                    lines.append(f"    - {t}")
            lines.append("")

    if deliv_field_changes:
        lines.append(f"**Deliverable updates ({len(deliv_field_changes)}):**")
        for title, changes in deliv_field_changes:
            for field, old, new in changes:
                lines.append(f"- **{title}** — {field}: {old} → {new}")
        lines.append("")

    print("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    main()
