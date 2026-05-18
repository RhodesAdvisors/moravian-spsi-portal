# Match your site to the SPSI Project Portal

Handoff for whoever maintains the **Weekly Tech Report** and **Weekly Enrollment Report** sites. The SPSI Project Portal at https://v0-html-page-hosting-rust.vercel.app/portal.html is the visual reference — same color palette, same fonts, same top bar, same control style.

This guide is the easiest path to alignment. Three options:

1. **Paste this whole document into a Claude (Cowork) session along with your current `index.html`** and say: *"Make my site match the brand kit in this document. Keep all my existing data and functionality. Replace styling and chrome only."*
2. **Manually copy the snippets below into your `<style>` and `<body>`** — order matters; CSS variables first.
3. **Have a developer apply it** — everything below is plain CSS/HTML, no build step required.

---

## What you're matching

- Moravian blue top bar with the star logo + serif school name on the left, a pulsing green "LIVE" indicator + date on the right
- Serif page title, monospace eyebrow above it, muted sub-paragraph below
- Stat cards in a row (numbers in serif, labels in monospace)
- Sticky filter/controls row with blurred background as you scroll
- Restrained Moravian-blue accents, Source Sans 3 / Source Serif 4 / JetBrains Mono typography only
- Sentence case everywhere (never ALL CAPS labels — except the small monospace eyebrows and labels)

---

## Step 1 — Add the fonts

Drop this in your `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,300;8..60,400;8..60,500;8..60,600&family=Source+Sans+3:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

## Step 2 — Drop the brand tokens at the top of your `<style>`

These are the canonical Moravian colors. Use these variables everywhere instead of literal hex codes.

```css
:root {
  /* Moravian primary palette */
  --m-blue: #00267A;
  --m-grey: #CCCCCC;
  --accent-blue: #078CF5;
  --light-grey: #F0F0F0;
  --dark-grey: #666666;
  --dark-blue: #001B56;
  --black: #000000;

  /* Tertiary (use sparingly — only for status encoding) */
  --t-deep-green: #006668;
  --t-red: #BC204B;
  --t-gold: #E58200;
  --t-green: #90C634;
  --t-orange: #FF723B;
  --t-yellow: #FFC23B;

  /* App tokens — these are what most rules should reference */
  --bg: #ffffff;
  --bg-soft: #F0F0F0;
  --ink: #001B56;
  --ink-soft: #00267A;
  --ink-mute: #666666;
  --rule: #e3e6ee;
  --rule-strong: #c5cad8;

  /* Status colors (only if you use status badges) */
  --s-done: #006668;
  --s-ongoing: #00267A;
  --s-progress: #078CF5;
  --s-paused: #E58200;
  --s-planned: #666666;
  --s-reopened: #BC204B;
}
```

## Step 3 — Base typography + reset

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--bg);
  color: var(--ink);
  font-family: 'Source Sans 3', -apple-system, sans-serif;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
::selection { background: var(--accent-blue); color: #fff; }
a { color: var(--m-blue); text-decoration: none; }
a:hover { color: var(--accent-blue); }
```

## Step 4 — Top bar

This is the most distinctive shared chrome. Same on all three sites.

```html
<header class="topbar">
  <div class="topbar-inner">
    <div class="brandmark">
      <img class="brandmark-mark" src="https://archives.moravian.edu/customizations/global/images/MU%20Star.png" alt="Moravian University">
      <span>Moravian University · School of Professional Studies & Innovation</span>
    </div>
    <div class="topbar-right">
      <span class="live">LIVE</span>
      <span id="topbar-date">—</span>
    </div>
  </div>
</header>
```

```css
.topbar {
  background: var(--m-blue);
  color: #fff;
  border-bottom: 4px solid var(--accent-blue);
}
.topbar-inner {
  max-width: 1440px; margin: 0 auto;
  padding: 14px 40px;
  display: flex; justify-content: space-between; align-items: center;
  gap: 24px;
}
.brandmark {
  display: flex; align-items: center; gap: 14px;
  font-family: 'Source Serif 4', serif;
  font-size: 18px; font-weight: 400;
  letter-spacing: -.005em;
}
.brandmark-mark {
  width: 36px; height: 36px;
  flex-shrink: 0; display: block; object-fit: contain;
}
.topbar-right {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
  color: rgba(255,255,255,.85);
  display: flex; gap: 24px; align-items: center;
}
.topbar-right .live::before {
  content: ''; display: inline-block;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--t-green);
  margin-right: 7px; vertical-align: middle;
  box-shadow: 0 0 0 0 rgba(144,198,52,.7);
  animation: pulse 2s ease-out infinite;
}
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(144,198,52,.7); }
  70%  { box-shadow: 0 0 0 8px rgba(144,198,52,0); }
  100% { box-shadow: 0 0 0 0 rgba(144,198,52,0); }
}
```

Set the date via JS so it stays current:

```js
const today = new Date();
document.getElementById('topbar-date').textContent =
  'As of ' + today.toLocaleDateString('en-US',
    {weekday:'long', month:'long', day:'numeric', year:'numeric'});
```

## Step 5 — Hero block

```html
<section class="hero">
  <div class="hero-eyebrow">YOUR REPORT NAME · Engagement with Rhodes Advisors</div>
  <h1 class="hero-title">Your one-line headline. <strong>Highlight word in bold.</strong></h1>
  <p class="hero-sub">A short paragraph that explains what this page is and who maintains it. Match the SPSI portal's tone — direct, no fluff.</p>
</section>
```

```css
.hero {
  padding: 56px 40px 40px;
  max-width: 1440px; margin: 0 auto;
  border-bottom: 1px solid var(--rule);
}
.hero-eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: .18em; text-transform: uppercase;
  color: var(--accent-blue);
  margin-bottom: 20px;
  display: inline-flex; align-items: center; gap: 12px;
}
.hero-eyebrow::before {
  content: ''; width: 32px; height: 2px; background: var(--accent-blue);
}
.hero-title {
  font-family: 'Source Serif 4', serif;
  font-weight: 300;
  font-size: clamp(40px, 5.5vw, 68px);
  line-height: 1.02; letter-spacing: -.022em;
  color: var(--m-blue);
  max-width: 22ch;
}
.hero-title strong { color: var(--m-blue); font-weight: 500; }
.hero-sub {
  margin-top: 24px;
  font-size: 17px; color: var(--ink-mute);
  max-width: 64ch; line-height: 1.55;
}
```

## Step 6 — Cross-link buttons (optional but recommended)

Put these in your hero, below the sub-paragraph. The SPSI portal links to both report sites — mirror it back from yours so users can hop between all three.

```html
<div class="hero-actions">
  <a class="hero-cta" href="https://v0-html-page-hosting-rust.vercel.app/portal.html" target="_blank" rel="noopener">
    <span>SPSI Project Portal</span>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M7 17L17 7M9 7h8v8"/></svg>
  </a>
  <!-- And one for the third site in the trio: -->
</div>
```

```css
.hero-actions {
  display: flex; flex-wrap: wrap; gap: 12px;
  margin-top: 28px;
}
.hero-cta {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 18px;
  background: #fff;
  border: 1.5px solid var(--m-blue);
  color: var(--m-blue);
  border-radius: 999px;
  text-decoration: none;
  font-size: 14px; font-weight: 500;
  letter-spacing: 0.01em;
  transition: background .15s ease, color .15s ease;
}
.hero-cta:hover { background: var(--m-blue); color: #fff; }
.hero-cta svg { width: 13px; height: 13px; flex-shrink: 0; }
```

## Step 7 — Sticky controls bar (if you have filters or tabs)

```css
.controls-wrap {
  border-top: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  margin-top: 56px;
  padding: 20px 0;
  position: sticky; top: 0; z-index: 50;
  backdrop-filter: blur(8px);
  background: rgba(240, 240, 240, .94);
}
.controls {
  max-width: 1440px; margin: 0 auto;
  padding: 0 40px;
  display: flex; align-items: center; gap: 20px;
  flex-wrap: wrap;
}
```

## Step 8 — Stat cards (if you show summary metrics)

```css
.stats {
  display: grid; grid-template-columns: repeat(4, 1fr);
  margin-top: 48px;
  border: 1px solid var(--rule);
  border-radius: 4px; overflow: hidden;
}
.stat {
  padding: 24px 28px;
  border-right: 1px solid var(--rule);
  position: relative;
}
.stat:last-child { border-right: none; }
.stat .num {
  font-family: 'Source Serif 4', serif;
  font-size: 44px; font-weight: 400;
  line-height: 1; color: var(--m-blue);
  letter-spacing: -.02em;
}
.stat .label {
  margin-top: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ink-mute);
}
.stat .accent-bar {
  position: absolute; top: 0; left: 0;
  width: 32px; height: 3px;
  background: var(--m-blue);
}
```

---

## Color usage rules of thumb

- **--m-blue** is for primary headings, brand-bar, links — the workhorse.
- **--accent-blue** is for emphasis: eyebrow accents, hover states, focus rings. Use sparingly.
- **Plain black** is for body copy. Plain white is for backgrounds.
- **--ink-mute (#666)** is for secondary text — subtitles, captions, helper text.
- **Tertiary colors** (red, gold, green) appear ONLY when encoding status. Never decorative.
- **Sentence case** for everything. The only exceptions are short monospace labels which get UPPERCASE + extra letter-spacing.

## What NOT to do

- No emojis as UI accents — the SPSI portal uses inline SVGs for the few icons it has
- No gradients, drop shadows, glow effects, or rounded "card" shadows. The look is flat and disciplined.
- No system fonts mixed in — only Source Sans 3 / Source Serif 4 / JetBrains Mono
- No alternate accent colors. If you have categorical data, use the existing status palette tokens.

## If the tools your site uses don't match

The SPSI portal is a single static `index.html` deployed to Vercel via GitHub. If your sites are built with React/Tailwind/v0/etc., the same color tokens and typography rules apply — just translate into your stack's idioms (Tailwind theme config, CSS-in-JS, etc.).

For the simplest path: bring the static HTML into a single file with the styles above, deploy that, and replace the existing site. The data display logic for the two report sites is probably small enough that a plain HTML rewrite is the cleanest move.

---

Reach out to Lee if anything's unclear — the SPSI portal repo is at https://github.com/RhodesAdvisors/moravian-spsi-portal and he can share any of the source verbatim.
