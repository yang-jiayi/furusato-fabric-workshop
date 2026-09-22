# Icon provenance and usage / アイコンの出典と利用条件

[Architecture home](README.md) · [Machine-readable manifest](../assets/architecture/icon-manifest.json)

## Source selected by the user / 指定された出典

All 13 Microsoft SVGs used by this documentation were downloaded from:

**[`yang-jiayi/AzureDiagarm`](https://github.com/yang-jiayi/AzureDiagarm/tree/c1b454cad21e8d9914bd28fd4cd8a16b9cb73c37/Azure_Public_Service_Icons/Icons/fabric)**<br>
Commit: **`c1b454cad21e8d9914bd28fd4cd8a16b9cb73c37`**<br>
Directory: `Azure_Public_Service_Icons/Icons/fabric/`<br>
Checked: **2026-09-21**

This is the actual `fabric` subdirectory of the user-supplied
[`Azure_Public_Service_Icons/Icons` collection](https://github.com/yang-jiayi/AzureDiagarm/tree/main/Azure_Public_Service_Icons/Icons).
No Azure Service Fabric or Power BI Embedded icon is substituted for Microsoft Fabric or Power BI.
No supplemental icon was downloaded from another collection.

The pinned upstream `fabric-manifest.json` declares the original package
**`@fabric-msft/svg-icons` 8.2.0**. Each of the 13 downloaded files was checked against
that upstream manifest's SHA-256. The local manifest records exact source path, commit,
download URL, hash, byte length, original viewBox and original package asset name.
The upstream package lineage is attributed to that manifest; the directly acquired source is
the user's repository.

13 個の SVG はすべて指定リポジトリから取得し、元のバイト列をそのまま保存しています。
色・グラデーション・縦横比・図形を保持し、近くに製品名を表示します。
図に埋め込む場合も同じ SVG バイト列を使用し、任意の拡大縮小だけを行います。

## Icons included / 使用するアイコン

| Component | Original filename |
|---|---|
| Microsoft Fabric | `microsoft-fabric.svg` |
| OneLake | `onelake.svg` |
| Lakehouse | `fabric-lakehouse.svg` |
| Notebook 01 / 04 / 05 | `fabric-notebook.svg` |
| Ontology | `fabric-item-ontology.svg` |
| Data Pipeline | `fabric-data-pipeline.svg` |
| Eventhouse | `fabric-eventhouse.svg` |
| KQL Database | `fabric-kql-database.svg` |
| Data Agent | `fabric-data-agent.svg` |
| Semantic model | `fabric-semantic-model.svg` |
| Power BI report | `fabric-power-bi-report.svg` |
| Variable Library, optional | `fabric-item-variable-library.svg` |
| User data functions, optional | `fabric-item-user-data-function.svg` |

## Explicit neutral shapes / 意図的に中立図形で示すもの

The full, non-truncated `Icons` tree at the pinned commit contains no dedicated
**Activator / Reflex** or **Code Interpreter** SVG by those component names.
They are shown as **text-labeled neutral panels**, rather than an unrelated Microsoft logo.
CSV files, FileCreated signals, SQL helpers, quality checks and medallion schemas are
also labeled concepts—not additional service logos.

指定コレクションに専用アイコンがない Activator と Code Interpreter は、
名称を明記した中立的な枠で表示します。別製品のアイコンに置き換えません。

## Applicable terms / 適用する利用条件

**Copyright © Microsoft Corporation. All rights reserved.**

We inspected the upstream [README icon guidance](https://github.com/yang-jiayi/AzureDiagarm/blob/c1b454cad21e8d9914bd28fd4cd8a16b9cb73c37/README.md#official-icon-library-maintenance),
[LICENSE](../assets/architecture/upstream/LICENSE.txt) and
[NOTICE](../assets/architecture/upstream/NOTICE.txt).
The README explicitly keeps Microsoft icon assets subject to Microsoft's terms rather
than treating the repository's MIT license as a blanket icon or trademark license.
The NOTICE identifies the Fabric package as MIT and separately points to the Fabric icon guidance.

The following official pages were retrieved directly and checked on 2026-09-21:

- **[Microsoft Fabric icon terms](https://learn.microsoft.com/en-us/fabric/fundamentals/icons)** —
  Microsoft permits copying, distribution and display in architectural diagrams, training
  materials and documentation, reserving other rights.
- **[Azure icon terms](https://learn.microsoft.com/en-us/azure/architecture/icons/)** —
  the supplied collection's umbrella guidance follows the same permitted-use categories.
- The upstream README also points to
  **[Microsoft Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general)**.

This use is architecture documentation and workshop training material. Icons are labeled with
their actual Microsoft product/item names and retain the original artwork:
**no cropping, flipping, rotation, distortion or recoloring**.
They are not used as a logo for the workshop or a non-Microsoft service.
This independent workshop does not imply Microsoft sponsorship or endorsement.

この文書は、公式ガイダンスが認めるアーキテクチャ図・教材・ドキュメントでの使用です。
製品アイコンの権利と Microsoft の商標に関する条件は引き続き適用されます。
このリポジトリの MIT ライセンスで商標やアイコンを再許諾する扱いにはしません。

For traceability, unchanged copies of the upstream
[LICENSE](../assets/architecture/upstream/LICENSE.txt),
[NOTICE](../assets/architecture/upstream/NOTICE.txt),
[Microsoft Terms of Use PDF](../assets/architecture/upstream/Microsoft_Terms_of_Use.pdf) and
[Fabric manifest](../assets/architecture/upstream/fabric-manifest.json) are retained.
Their source paths and SHA-256 values are in the local icon manifest.
The PDF comes from the collection; the Fabric-specific permitted use was additionally
verified against the official Fabric page.

## Rendering / 描画

The browser explorer uses local SVG image resources with proportional scaling.
Standalone architecture SVG exports embed the exact original icon bytes as image resources
so they do not depend on remote URLs or browser cross-file loading.
The QHD PNGs are rasterized from those exported SVGs; Markdown uses PNG for reliable image display.
The diagram layout, labels, connections and neutral shapes are workshop-authored content;
the embedded Microsoft artwork retains the rights above.

<a id="readme-icons"></a>

## README product artwork / README の製品アイコン

The README also uses these same original files for the Microsoft Fabric product
identifier, the six-product overview, and the bilingual learning cards. Notebook,
Data Pipeline and Semantic model icons appear next to their own product/item names.
No new substitute artwork is used for Code Interpreter.

The hero illustration and the two video covers embed the **unchanged original SVG
bytes** as image resources. The README displays high-resolution PNG renders for
reliable GitHub image loading; the editable SVG versions remain alongside them.
The authored backgrounds, orbit lines and play buttons are decorative. They are
not Fabric UI screenshots or evidence of query execution.

On **2026-09-22**, the ten reused README icons were checked byte-for-byte against
the same directory at source commit
[`55c907f08682e46549f588d17016a7a0244fe233`](https://github.com/yang-jiayi/AzureDiagarm/tree/55c907f08682e46549f588d17016a7a0244fe233/Azure_Public_Service_Icons/Icons/fabric).
They match the originals already recorded in the architecture icon manifest.
The original icon files and existing architecture diagrams were not changed.

README のヘッダー・製品一覧・日英の学習カードにも、指定された Fabric コレクションの
原本を使用しています。各アイコンは Microsoft の製品・機能を識別するものであり、
本 Workshop 独自のロゴや Microsoft の公認・協賛を示すものではありません。
色・図形・グラデーションを変えず、縦横比を保った拡大縮小だけを行っています。

See the [README artwork manifest](../assets/readme/branding-manifest.json)
for the embedded originals and rendered image hashes.
