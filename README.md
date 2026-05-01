# SPSI Project Portal — Refresh Routine

Live site: https://v0-html-page-hosting-rust.vercel.app/portal.html

## Files in this folder

| File | What it is |
|---|---|
| `index.html` | The deployable site. Drag this into Vercel to publish. |
| `_template.html` | The HTML template build_site.py patches. **Don't edit by hand** — it's used as the canonical structural template across refreshes. |
| `build_site.py` | Local builder. Reads the three JSON files and writes a fresh `index.html`. No Notion access required. |
| `projects_from_notion.json` | Snapshot of the SPSI Projects Timeline database from Notion. |
| `deliverables.json` | Cache of every deliverable page (title, status, dates, owner, characteristics body). |
| `user_id_to_name_map.json` | Notion user ID → display name. Edit by hand if a new person joins. |

## How to refresh

Ask Claude in Cowork:

> Refresh the SPSI portal site.

Claude will:

1. Pull the live SPSI Projects Timeline view from Notion → rewrite `projects_from_notion.json`.
2. Diff against the current cache, fetch any new/changed deliverables from Notion → update `deliverables.json`.
3. Run `build_site.py` → rewrite `index.html`.
4. Hand you the file path so you can deploy.

You then drag `index.html` into Vercel.

## What if I just want to rebuild from existing JSON?

```bash
cd "Moravian Site"
python3 build_site.py
```

That will regenerate `index.html` using whatever's currently in the three JSON files. Useful if you tweak the user map by hand or edit a stale deliverable record.

## Adding a new person

If a new owner shows up in Notion and the site shows their owner cell as blank, edit `user_id_to_name_map.json`:

```json
{
  "user://abcd-...": "First Last"
}
```

Save, then re-run `python3 build_site.py`.

## Design constraints baked in

- No Notion links anywhere in the rendered output. The site stands alone.
- Match the existing Moravian palette / typography exactly. `build_site.py` patches a saved template — it doesn't restyle.
- Deliverable Characteristics render as italic muted text under each deliverable title. Empty Characteristics → just the title, no body.
- Project Description renders italic above the metadata grid in the drawer. No description → section is omitted.
