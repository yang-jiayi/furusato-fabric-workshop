# Furusato Fabric Workshop — Architecture

[日本語](overview.ja.md) · [English](overview.en.md) · [Interactive explorer](index.html)

**The architecture of the existing `v2.7.0 / unified-20260923` workshop.**
The diagrams describe the released implementation and its optional analytics extension.
All donation, donor and supplier records are synthetic teaching data.

| 日本語 | English |
|---|---|
| [![日本語の全体アーキテクチャ](../assets/architecture/furusato-architecture.ja.png)](../assets/architecture/furusato-architecture.ja.svg) | [![Overall architecture in English](../assets/architecture/furusato-architecture.en.png)](../assets/architecture/furusato-architecture.en.svg) |
| [解説](overview.ja.md) · [SVG](../assets/architecture/furusato-architecture.ja.svg) · [PNG](../assets/architecture/furusato-architecture.ja.png) | [Explanation](overview.en.md) · [SVG](../assets/architecture/furusato-architecture.en.svg) · [PNG](../assets/architecture/furusato-architecture.en.png) |

## Explore locally / ローカルで見る

Open **[`index.html`](index.html)** in a browser after downloading/cloning the repository.
GitHub's file view shows the HTML source; the local page is the interactive experience.
The page works from `file://`, with local assets, without a build step, external framework,
font download, remote analytics, sign-in or Fabric connection.

- Japanese: `index.html?lang=ja&focus=overview`
- English: `index.html?lang=en&focus=overview`
- Flow focus: `static`, `events`, `agent`, `analytics`, `control`, `outcomes`
- Click a flow button or diagram card. Use **Tab**, **Enter** or **Space**.
- Shortcuts: **0** overview, **1–4** numbered flows, **5** setup, **6** learning outcomes,
  **J / E** language, **Escape** overview. Shortcuts pause inside controls.
- At **2560 × 1440**, use browser zoom **100%** for the full diagram and readable detail panel.
  The diagram scrolls horizontally on small screens; controls and explanation reflow.
- Use **Expand diagram** for a full-width reading view. The PNG files are exactly
  **2560 × 1440**, rasterized from their corresponding SVGs.

## An ending for the architecture walkthrough / 動画の最後に使う

This is a browser-based explorer, not a slide deck. A suggested closing route:

1. **Overview** — begin with the business question.
2. **01 Static & meaning** — follow donation facts into business relationships.
3. **02 Observations** — distinguish the operational observation population.
4. **03 One Agent** — connect the three query languages to their evidence.
5. **04 Quality & BI** — follow the separate, quality-gated analytics branch.
6. **00 Setup** — identify the preview / consent boundary briefly.
7. **Learning outcomes** — finish on the positive value statement.

The [bilingual closing narration and browser cues](walkthrough.md) follow this route.
They are intended for the **ending** of each revised promo video.
Recording, video assembly and publication remain separate steps.

The language toggle updates diagram text, controls, details, accessible names and download links.
The explorer makes no service calls and displays no live status. The diagram describes
the intended lifecycle: **formal start → verify actual delivery → formal stop**.

## Evidence and icon rights / 根拠とアイコン利用条件

- [Source anchors and interpretation](sources.md)
- [Icon provenance and usage terms](icons.md)
- [Machine-readable icon manifest](../assets/architecture/icon-manifest.json)
- [Existing single-Agent guide](../single-agent-workshop.md)

The icon source is the **user-specified
[`yang-jiayi/AzureDiagarm` collection](https://github.com/yang-jiayi/AzureDiagarm/tree/main/Azure_Public_Service_Icons/Icons)**.
Microsoft icons retain their original artwork and applicable Microsoft terms.
The workshop's MIT license does not relicense Microsoft marks.

Documentation baseline: `32d296ebd673df4f180ac56670542cc0eaf350db` · reviewed 2026-09-21.
Lifecycle update: 2026-09-23 · official `start_rule` / `stop_rule`, complete-file PutBlob
and separate native event/activation/job/Copy/KQL gates. The data architecture is unchanged.
The documentation uses logical names and `{PID}` placeholders; environment identifiers stay external.
