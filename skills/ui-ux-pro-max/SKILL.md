---
name: ui-ux-pro-max
description: >-
  Third-party skill (nextlevelbuilder/ui-ux-pro-max-skill, check repo for license).
  Design intelligence for professional UI/UX: generates a complete design system
  (pattern + style + colors + typography + effects + anti-patterns) from a product
  description, with 79 searchable UI styles, 192 industry reasoning rules, 192 color
  palettes, 74 font pairings, 22 stack guidelines and pre-delivery checks.
  Use whenever the user wants to build, design, create, implement, review, fix or
  improve any UI: landing pages, dashboards, portfolios, mobile apps, design systems,
  "build a landing page", "create a dashboard", "design my app", "mejora el diseño",
  "revisa esta interfaz", "dale estilo". Do not modify — pull updates from upstream.
---

# UI UX Pro Max (Third-Party Reference)

> **Source:** [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
> **Do not modify this skill directly.** To update, pull from the upstream repository
> or reinstall with the CLI below.

AI skill that provides design intelligence for building professional UI/UX across
platforms and frameworks. Given a product description it generates a tailored
design system (landing pattern, visual style, palette, typography, effects,
anti-patterns to avoid, pre-delivery checklist) and implements it with
stack-specific guidelines.

## Install / update (human runs this, never the agent)

```bash
npm install -g ui-ux-pro-max-cli
cd /path/to/project
uipro init --ai opencode    # opencode | claude | cursor | windsurf | ...
```

`uipro update` refreshes the skill files. Requires Python 3.x for the search
script (standard library only, no network calls).

## How to use

Just ask naturally; the skill auto-activates on UI/UX requests:

```text
Build a landing page for my SaaS product
Create a dashboard for healthcare analytics
Design a portfolio website with dark mode
```

Flow: user request → design system generated (pattern + style + colors +
typography + effects) → smart recommendations via BM25 search → code generation
with proper tokens → pre-delivery checks against anti-patterns.

## Direct search (advanced)

```bash
python3 <skill-dir>/scripts/search.py "beauty spa wellness" --design-system -p "Serenity Spa"
python3 <skill-dir>/scripts/search.py "glassmorphism" --domain style
python3 <skill-dir>/scripts/search.py "form validation" --stack react
```

Domains: `style`, `typography`, `chart`, `ux`, `icons`. Stacks include
`html-tailwind` (default), `react`, `next`, `vue`, `nuxt`, `svelte`, `astro`,
`angular`, `laravel`, `flutter`, `react-native`, `swiftui`, `jetpack-compose`.

## Relation to local skills

- `impeccable` owns craft/polish of an existing interface; `ui-ux-pro-max`
  owns generating the design system from zero.
- `web-esenciales` owns the 20 must-have business/SEO items of a website
  (404, CTA, robots.txt, schema, analytics); run it after the design system
  is applied to verify nothing essential is missing.
- `web-cloner` owns replicating an existing site; `ui-ux-pro-max` owns
  designing a new one.
