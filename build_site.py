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


def notion_url_for_id(did: str) -> str:
    """Build a public Notion page URL from a 32-hex page ID."""
    if not did:
        return ""
    return f"https://www.notion.so/{did}"


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

        # Project-level Notion URL: prefer the explicit `url` field if the
        # parsing step captured it; otherwise leave blank (button is hidden).
        project_url = p.get("url") or p.get("notion_url") or ""

        deliv_records = []
        for url in p.get("deliverables", []):
            did = url_to_id(url)
            d = deliverables.get(did)
            deliv_url = notion_url_for_id(did) if did else ""
            if not d:
                # Page exists in projects' deliverable list but isn't in cache.
                deliv_records.append({
                    "title": "(deliverable not cached)",
                    "characteristics": "",
                    "notion_url": deliv_url,
                    "start": "",
                    "end": "",
                    "status": "",
                })
                continue
            deliv_records.append({
                "title": d.get("title") or "",
                "characteristics": d.get("characteristics") or "",
                "notion_url": deliv_url,
                "start": to_mdY(d.get("start", "")),
                "end": to_mdY(d.get("end", "")),
                "status": d.get("status") or "",
            })

        out.append({
            "name": p.get("name", ""),
            "status": p.get("status", ""),
            "start": to_mdY(p.get("start", "")),
            "end": to_mdY(p.get("end", "")),
            "owner": owner_name,
            "departments": sorted(p.get("departments", [])),
            "project_description": p.get("project_description", ""),
            "notion_url": project_url,
            "deliverables": deliv_records,
        })
    return out


# -----------------------------------------------------------------------------
# Template handling
# -----------------------------------------------------------------------------
PROJECTS_LINE_RE = re.compile(r"^const\s+PROJECTS\s*=\s*\[.*?\];\s*$", re.MULTILINE)

# Bumped to v6 when we added Weekly Enrollment / Tech Report CTA buttons in the hero.
DRAWER_PATCH_MARKER = "/* drawer:desc-chars-notion-due-legend-sticky-hero-cta v6 */"

# The Notion logo SVG, inlined so the site has no extra external dependencies.
NOTION_SVG = (
    '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326'
    'L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904'
    'c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887'
    'l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264'
    'c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84'
    'l-3.222.186c-.093-.186 0-.653.327-.746l.84-.234V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073'
    'l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933z"/>'
    '</svg>'
)

DRAWER_PATCH = """/* drawer:desc-chars-notion-due-legend-sticky-hero-cta v6 */
/* Weekly report CTA buttons in the hero, just below the subtitle */
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}
.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: #ffffff;
  border: 1.5px solid var(--m-blue);
  color: var(--m-blue);
  border-radius: 999px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.01em;
  transition: background .15s ease, color .15s ease;
}
.hero-cta:hover {
  background: var(--m-blue);
  color: #ffffff;
}
.hero-cta svg {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
}

/* Sticky-pin the relocated legend to the bottom of the filter bar.
   --controls-height is set at runtime by a small inline script;
   the 78px fallback covers the typical desktop case. */
.legend {
  position: sticky;
  top: var(--controls-height, 78px);
  z-index: 49;
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 12px 40px;
  background: rgba(240, 240, 240, .94);
  backdrop-filter: blur(8px);
  border: none;
  border-bottom: 1px solid var(--rule);
  border-radius: 0;
  margin: 0 0 24px;
}

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

/* Notion link buttons — quiet by default, hover for emphasis */
.drawer-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.drawer-title-row h2 { flex: 1; min-width: 0; }
.notion-link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 4px;
  background: rgba(255,255,255,0.18);
  color: #ffffff;
  text-decoration: none;
  flex-shrink: 0;
  transition: background .15s ease;
}
.notion-link-btn:hover { background: rgba(255,255,255,0.32); color: #ffffff; }
.notion-link-btn svg { width: 13px; height: 13px; display: block; }
.deliv-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.deliv-title-row > span:first-child { flex: 1; min-width: 0; }
.deliv-notion-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 3px;
  background: var(--light-grey);
  color: var(--dark-grey);
  text-decoration: none;
  flex-shrink: 0;
  transition: background .15s ease, color .15s ease;
}
.deliv-notion-btn:hover { background: var(--rule-strong); color: var(--ink); }
.deliv-notion-btn svg { width: 11px; height: 11px; display: block; }

/* Deliverable due-date line — small monospace below the title row */
.deliv-due {
  display: block;
  margin-top: 3px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--ink-mute);
}
"""

# -----------------------------------------------------------------------------
# Patch 1 — the deliverable render block inside openDrawer().
# Replaces the original (no characteristics, no notion button) with a version
# that includes both.
# -----------------------------------------------------------------------------
NEW_DELIV_RENDER = (
    "  const delivHTML = p.deliverables.length\n"
    "    ? `<ul class=\"deliv-list\">${p.deliverables.map(d => `\n"
    "        <li class=\"deliv-item\">\n"
    "          <span class=\"bullet\"></span>\n"
    "          <span class=\"text\">\n"
    "            <span class=\"deliv-title-row\">\n"
    "              <span>${escHTML(d.title)}</span>\n"
    "              ${d.notion_url ? `<a class=\"deliv-notion-btn\" href=\"${d.notion_url}\" target=\"_blank\" rel=\"noopener\" title=\"Open in Notion\" aria-label=\"Open in Notion\">" + NOTION_SVG + "</a>` : ''}\n"
    "            </span>\n"
    "            ${d.end ? `<span class=\"deliv-due\">Due ${escHTML(d.end)}</span>` : (d.start ? `<span class=\"deliv-due\">Started ${escHTML(d.start)}</span>` : '')}\n"
    "            ${d.characteristics ? `<span class=\"deliv-characteristics\">${escHTML(d.characteristics)}</span>` : ''}\n"
    "          </span>\n"
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

# -----------------------------------------------------------------------------
# Patch 2 — inject Project Description above the meta grid (drawer-body innerHTML).
# -----------------------------------------------------------------------------
OLD_DRAWER_HEAD_RE = re.compile(
    r"(document\.getElementById\('drawer-body'\)\.innerHTML\s*=\s*`\s*\n\s*)<div class=\"drawer-meta-grid\">"
)

def _new_drawer_head(match):
    return (
        match.group(1)
        + '${p.project_description ? `<div class="drawer-project-desc">${escHTML(p.project_description)}</div>` : \'\'}\n'
        + '    <div class="drawer-meta-grid">'
    )

# -----------------------------------------------------------------------------
# Patch 3 — wrap the static drawer-title h2 in a flex row so the Notion button
# can sit beside it. Also adds the link element itself.
# -----------------------------------------------------------------------------
OLD_TITLE_HTML_RE = re.compile(r'<h2 id="drawer-title">—</h2>')
NEW_TITLE_HTML = (
    '<div class="drawer-title-row">'
    '<h2 id="drawer-title">—</h2>'
    f'<a id="drawer-notion-link" class="notion-link-btn" target="_blank" rel="noopener" title="Open in Notion" aria-label="Open in Notion" style="display:none;">{NOTION_SVG}</a>'
    '</div>'
)

# -----------------------------------------------------------------------------
# Patch 4 — when openDrawer fires, sync the project's Notion URL onto the
# header link element. Insert right after the existing line that sets the
# drawer title text.
# -----------------------------------------------------------------------------
OLD_TITLE_JS_RE = re.compile(
    r"(document\.getElementById\('drawer-title'\)\.textContent\s*=\s*p\.display;)"
)
NEW_TITLE_JS_TAIL = (
    "\n  const __notionLink = document.getElementById('drawer-notion-link');"
    "\n  if (__notionLink) {"
    "\n    if (p.notion_url) { __notionLink.href = p.notion_url; __notionLink.style.display = ''; }"
    "\n    else { __notionLink.style.display = 'none'; }"
    "\n  }"
)

# -----------------------------------------------------------------------------
# Patch 6 & 7 — relocate the timeline legend.
# Originally the legend sits inside <section id="view-timeline"> at the bottom,
# so it's only visible in Timeline view AND requires scrolling on long pages.
# Move it to sit between the filter-banner and view-timeline, where it's
# always visible (any view) and reachable without scrolling.
# -----------------------------------------------------------------------------
LEGEND_HTML = (
    '<div class="legend">\n'
    '    <div class="legend-item"><span class="legend-swatch leg-done"></span>Done</div>\n'
    '    <div class="legend-item"><span class="legend-swatch leg-ongoing"></span>Ongoing</div>\n'
    '    <div class="legend-item"><span class="legend-swatch leg-progress"></span>In Motion</div>\n'
    '    <div class="legend-item"><span class="legend-swatch leg-paused"></span>Paused</div>\n'
    '    <div class="legend-item"><span class="legend-swatch leg-planned"></span>Planned · Scoped</div>\n'
    '    <div class="legend-item"><span class="legend-swatch leg-reopened"></span>Complete · Reopened</div>\n'
    '    <div class="legend-item"><span class="legend-swatch leg-today"></span>Today</div>\n'
    '  </div>'
)

# Match the existing legend block plus the closing </section> right after it,
# so we cleanly remove the legend from inside view-timeline.
OLD_LEGEND_INSIDE_TIMELINE_RE = re.compile(
    r'\n\s*<div class="legend">\s*'
    r'(?:<div class="legend-item">[^<]*<span class="legend-swatch[^"]*"></span>[^<]+</div>\s*){7}'
    r'</div>\s*(</section>)'
)

# Match the closing of filter-banner + the opening of view-timeline so we can
# slide the legend block in between.
OLD_BANNER_TIMELINE_GAP_RE = re.compile(
    r'(<button id="banner-clear" type="button">Clear filter</button>\s*</div>)'
    r'(\s*<section class="view-section" id="view-timeline">)'
)

# Patch 9 — inject the Weekly Report CTA row in the hero, between the
# subtitle paragraph and the stats grid.
HERO_CTAS_HTML = (
    '\n\n  <div class="hero-actions">\n'
    '    <a class="hero-cta" href="https://enrollment-performance-hub.netlify.app/">\n'
    '      <span>Weekly Enrollment Report</span>\n'
    '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M7 17L17 7M9 7h8v8"/></svg>\n'
    '    </a>\n'
    '    <a class="hero-cta" href="https://moravian-spsi-tech-status.vercel.app/">\n'
    '      <span>Weekly Tech Report</span>\n'
    '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M7 17L17 7M9 7h8v8"/></svg>\n'
    '    </a>\n'
    '    <a class="hero-cta" href="https://moravian-marketing-performance-report.netlify.app/">\n'
    '      <span>Weekly Marketing Report</span>\n'
    '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M7 17L17 7M9 7h8v8"/></svg>\n'
    '    </a>\n'
    '  </div>'
)
OLD_HERO_SUB_TO_STATS_RE = re.compile(
    r'(<p class="hero-sub">[^<]*</p>)(\s*<div class="stats">)',
    re.DOTALL,
)

# Patch 8 — inject a tiny script that measures the sticky filter bar's height
# at runtime and exposes it as --controls-height. The legend uses this so it
# pins flush to the bottom of the filter bar even when controls wrap on mobile.
STICKY_OFFSET_SCRIPT = (
    '\n<script>(function(){var c=document.querySelector(".controls-wrap");'
    'if(!c)return;var s=function(){'
    'document.documentElement.style.setProperty("--controls-height",c.offsetHeight+"px");};'
    's();window.addEventListener("resize",s);})();</script>\n'
)
# We don't use a regex for the </body> insertion — `rsplit` on the last
# occurrence is safer than a regex that could match `</body>` inside an
# unrelated CSS/JS comment or string.


def patch_template(html: str) -> str:
    """Idempotently apply all drawer patches to the unpatched template HTML."""
    if DRAWER_PATCH_MARKER in html:
        return html  # already patched

    # 1. Inject CSS just before the closing </style> tag.
    html = re.sub(r"(</style>)", DRAWER_PATCH + r"\1", html, count=1)

    # 2. Replace the deliverable render block.
    if not OLD_DELIV_RENDER_RE.search(html):
        raise SystemExit("Template missing the expected deliverable render block. Aborting.")
    html = OLD_DELIV_RENDER_RE.sub(NEW_DELIV_RENDER, html, count=1)

    # 3. Inject Project Description above the meta grid.
    if not OLD_DRAWER_HEAD_RE.search(html):
        raise SystemExit("Template missing the drawer head opener. Aborting.")
    html = OLD_DRAWER_HEAD_RE.sub(_new_drawer_head, html, count=1)

    # 4. Wrap the drawer-title h2 with a flex row + add the Notion link element.
    if not OLD_TITLE_HTML_RE.search(html):
        raise SystemExit('Template missing the static `<h2 id="drawer-title">` element. Aborting.')
    html = OLD_TITLE_HTML_RE.sub(NEW_TITLE_HTML, html, count=1)

    # 5. Hook openDrawer's title-set line so it also updates the Notion link.
    if not OLD_TITLE_JS_RE.search(html):
        raise SystemExit("Template missing the openDrawer title assignment line. Aborting.")
    html = OLD_TITLE_JS_RE.sub(lambda m: m.group(1) + NEW_TITLE_JS_TAIL, html, count=1)

    # 6. Remove the legend from inside the timeline section.
    if not OLD_LEGEND_INSIDE_TIMELINE_RE.search(html):
        raise SystemExit("Template missing the legend block inside view-timeline. Aborting.")
    html = OLD_LEGEND_INSIDE_TIMELINE_RE.sub(lambda m: "\n" + m.group(1), html, count=1)

    # 7. Insert the legend between filter-banner and view-timeline.
    if not OLD_BANNER_TIMELINE_GAP_RE.search(html):
        raise SystemExit("Template missing the filter-banner / view-timeline gap. Aborting.")
    html = OLD_BANNER_TIMELINE_GAP_RE.sub(
        lambda m: m.group(1) + "\n\n  " + LEGEND_HTML + m.group(2),
        html,
        count=1,
    )

    # 8. Inject the sticky-offset measurement script before the real closing
    # body tag (use rsplit so we never match a stray `</body>` inside a comment).
    body_tag = "</body>"
    parts = html.rsplit(body_tag, 1)
    if len(parts) != 2:
        raise SystemExit("Template missing </body>. Aborting.")
    html = parts[0] + STICKY_OFFSET_SCRIPT + body_tag + parts[1]

    # 9. Inject the Weekly Report CTA buttons in the hero.
    if not OLD_HERO_SUB_TO_STATS_RE.search(html):
        raise SystemExit("Template missing hero-sub → stats anchor. Aborting.")
    html = OLD_HERO_SUB_TO_STATS_RE.sub(
        lambda m: m.group(1) + HERO_CTAS_HTML + m.group(2),
        html,
        count=1,
    )

    return html


def replace_projects_block(html: str, projects) -> str:
    """Swap in the new const PROJECTS = [...]; line.

    IMPORTANT: pass `new_line` via a callable, not a string, so re.sub doesn't
    interpret `\\n` / `\\t` etc. in the JSON payload as control characters.
    A string replacement would convert json.dumps's `\\n` (two chars) into a
    literal LF, producing invalid JS and breaking the site.
    """
    new_line = "const PROJECTS = " + json.dumps(projects, ensure_ascii=False) + ";"
    if not PROJECTS_LINE_RE.search(html):
        raise SystemExit("Could not find `const PROJECTS = [...]` in template. Aborting.")
    return PROJECTS_LINE_RE.sub(lambda m: new_line, html, count=1)


def stamp_refresh_date(html: str) -> str:
    """Update the hardcoded TODAY date constant so 'Last refreshed' shows today."""
    today = datetime.now()
    new_today = f"const TODAY = new Date({today.year}, {today.month - 1}, {today.day});"
    return re.sub(r"const\s+TODAY\s*=\s*new\s+Date\([^)]+\);", new_today, html, count=1)


def main():
    if not os.path.exists(TEMPLATE_FILE):
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
    proj_with_url = sum(1 for p in projects if p["notion_url"])
    deliv_with_url = sum(1 for p in projects for d in p["deliverables"] if d["notion_url"])
    print(f"Wrote {OUT_FILE}")
    print(f"  Projects: {len(projects)} ({proj_with_url} with Notion URL)")
    print(f"  Deliverables: {deliv_count} ({deliv_with_url} with Notion URL)")
    print(f"  Deliverables with Characteristics text: {char_count}")
    print(f"  Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
