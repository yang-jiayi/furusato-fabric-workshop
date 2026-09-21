# Ontology 検証・RDF / OWL 出力 / Ontology validation and RDF / OWL export

[日本語](#日本語) | [English](#english)

---

## 日本語

### RDF / OWL 構成出力

`export_ontology_rdf.py` は、正本の
[`ontology-full-definition-template.json`](../../workshop/v2.7.0/ontology/ontology-full-definition-template.json) を読み、
[`ontology/rdf`](../../workshop/v2.7.0/ontology/rdf) に `.ttl`・`.rdf`・`.owl` と `SHA256SUMS.txt` を生成します。
Fabric API、認証、データ照会、稼働中のモデル変更は行いません。Python と追加依存 `rdflib` を使います。

```powershell
python -m pip install -r .\tools\ontology\requirements.txt
python .\tools\ontology\export_ontology_rdf.py
python .\tools\ontology\export_ontology_rdf.py --check
python -m unittest discover -s .\tools\ontology\tests -v
```

通常実行はローカルの生成ファイルを再生成・置換します。`--check` は読み取り専用で、欠落・陳腐化・不一致を失敗にします。
`--output-dir <path>` で別の保存先、`--template <path>` で完全なポータブルテンプレートのコピーを指定できます。
実 ID を埋めた live 定義、AIPath、不明な型・part、参照切れは受け付けません。

| Fabric 構成 | RDF / OWL 表現 |
|---|---|
| 10 Entity type | 10 `owl:Class` |
| 72 static + 1 time-series Property | 73 `owl:DatatypeProperty`。時系列かどうかは `fabric:propertyKind` 注釈で区別 |
| 15 Relationship | 15 `owl:ObjectProperty`。元の source / target を `rdfs:domain` / `rdfs:range` に対応 |
| `BigInt` / `String` / `DateTime` | `xsd:long` / `xsd:string` / `xsd:dateTime`。日付に見える String は勝手に型変換しない |
| キー・表示名・業務説明・同義語 | キー順序と表示プロパティを注釈、説明を `rdfs:comment`、同義語を `skos:altLabel` として保持 |
| 11 DataBinding / 15 Contextualization | source 種別、テーブル、列とプロパティの対応、すべてのキー列を注釈リソースとして保持 |
| Municipality の時系列 | `IncomingDonationAmountYen`、`DonationEvents`、`DonatedAt`、`DonationAmountYen` / `MunicipalityID` の対応を保持 |
| 元定義 | `.platform` 以外の 53 parts を `fabric:definitionPart` / `fabric:definitionJson` で欠落なく保持 |

`furusato:` はこのリポジトリの用語、`fabric:` は**この変換ツール独自の注釈語彙**であり、
Microsoft が提供する RDF 語彙ではありません。名前はクラス `furusato:Donation`、
属性 `furusato:Donation__DonationAmountYen`、関係 `furusato:DonationToMunicipality` のように解決できます。
属性を Entity ごとの IRI に分け、同名属性の domain が誤って交差しないようにしています。
独自の注釈述語と `skos:altLabel` は `owl:AnnotationProperty` として明示的に宣言し、
標準語彙以外の述語に型宣言の欠落がないことも検査します。

`.ttl` は Turtle、`.rdf` / `.owl` は同一バイトの RDF/XML です。`.owl` は OWL/XML ではありません。
3 形式を再読み込みして同じグラフであることを照合します。キーを `owl:hasKey`、
データセット内のカーディナリティを OWL の普遍的な件数制約へは変換しません。
このファイルは Fabric の直接 import / round-trip 操作用ファイルでも、
時系列インスタンスや実行可能なバインドを含むファイルでもありません。
実 Workspace / Item ID、接続先、個票、評価ログは含めず、接続情報は元のプレースホルダーを維持します。
`.platform` の配置メタデータは除外します。RDF の文法と構成一致を検査しますが、OWL reasoner による
論理整合性証明や Fabric へのインポート成功を保証するものではありません。

### Relationship カーディナリティの検証

`Test-OntologyCardinality.ps1` は、15 本の Ontology Relationship を対象とする
**読み取り専用**の validator です。書き込み、アップロード、変更は一切行わず、
PowerShell 7 以外のモジュールも必要としません。

### 使い方

```powershell
pwsh ./tools/ontology/Test-OntologyCardinality.ps1
```

`-Detailed` を付けると成功した検査もすべて出力します。`-WorkshopRoot <path>` を
付けると workshop フォルダーのコピーを検証できます。

導出モードは 2 つあり、スクリプトはどちらで判定したかを必ず出力します。

- 既定（actual-data モード）：同梱の seed CSV を読み直して Node 数・Edge 数・参加率を
  実データから再計算し、dataset manifest がその再計算と一致することを確認したうえで
  カーディナリティを導出します。宣言が実データと合っているかを証明できるのはこのモードだけです。
- `-FromData:$false`（declared-count モード）：dataset manifest の宣言値だけを使います。
  高速ですが、manifest 自体が CSV と食い違っている場合は検出できません。
- `-SelfTest`：意図的な欠陥を埋め込んだコピーを検査し、9 種類すべてが検出されることを確認します。
  ディスク上のファイルは変更しません。

```powershell
pwsh ./tools/ontology/Test-OntologyCardinality.ps1 -WorkshopRoot ./workshop/v2.7.0 -Detailed
```

カーディナリティ契約が満たされていればスクリプトは終了コード `0` で終了し、
満たされていなければ失敗一覧とともに `1` で終了します。そのためリリース検査の
gate として使用できます。既定の actual-data モードでの期待値は `Checks passed: 350`、
`-FromData:$false` の declared-count モードでは `Checks passed: 318`、
`-SelfTest` では `Checks passed: 359` です。

### 前提

- PowerShell 7（`pwsh`）。追加モジュールは不要です。
- `workshop/v2.7.0` 配下の ontology 定義、Notebook、contract、dataset manifest。

### 検証範囲

| 領域 | 検査内容 |
|---|---|
| 網羅 | 15 本の Relationship すべてが `direction`、`cardinality`、`grain` を宣言していること |
| メタデータ一致 | `ontology-semantic-metadata.json` と Notebook 02 の埋め込みコピーが一致すること |
| テンプレート一致 | `ontology-full-definition-template.json` と Notebook 03 の埋め込みコピーが一致すること |
| 契約一致 | `participant-workspace-contract.json` が同じカーディナリティと同じ端点を宣言していること |
| 構成 | 4 つのソースが同じ 15 個の名前を列挙し、dataset manifest が 15 本すべての Edge 数を持つこと |
| キーの一意性 | 宣言されたカーディナリティが、同梱の Node 数と Edge 数から導出される形状と一致すること |

### 導出カーディナリティの考え方

Relationship の binding は binding table の 1 行につき厳密に 1 本の Edge を生成します。
したがって、Node 数が Edge 数と等しい側が、そのテーブル上でキーが一意な側です。

| 観測 | 導出されるカーディナリティ |
|---|---|
| `edges == sourceNodes` かつ `edges == targetNodes` | `one-to-one` |
| `edges == targetNodes` | `one-to-many from <source entity>` |
| `edges == sourceNodes` | `many-to-one` |
| どちらとも一致しない | `many-to-many`（`zero-to-many …` として宣言） |

件数は `data/dataset-manifest.json` の `expected.nodeCounts` と
`expected.edgeCounts` から取得します。この値は Notebook 01 が Lakehouse の出力
テーブルを構築するときに再現します。これらの件数と矛盾する宣言は実行を失敗させ、
導出された形状、宣言された文字列、3 つの件数すべてを示します。

### 再現性と限界

Notebook 02 は実行時に同じ契約を強制します。`validate_manifest` は、
`direction`、`cardinality`、`grain` のいずれかを欠く Relationship を持つ
メタデータ manifest を拒否し、最初の 1 件で停止せずに、違反しているすべての
Relationship を 1 つのメッセージで報告します。

---

## English

### RDF / OWL schema export

`export_ontology_rdf.py` reads the canonical
[`ontology-full-definition-template.json`](../../workshop/v2.7.0/ontology/ontology-full-definition-template.json)
and generates three schema files plus their SHA-256 manifest in
[`ontology/rdf`](../../workshop/v2.7.0/ontology/rdf). It makes no Fabric/authentication/data calls and never changes a live model.

```powershell
python -m pip install -r .\tools\ontology\requirements.txt
python .\tools\ontology\export_ontology_rdf.py
python .\tools\ontology\export_ontology_rdf.py --check
python -m unittest discover -s .\tools\ontology\tests -v
```

Normal execution regenerates/replaces the named local outputs. `--check` is read-only and fails on missing or stale bytes.
Use `--output-dir <path>` for another destination and `--template <path>` for a copy of the complete portable template.
Live-bound definitions, AIPath, unknown types/parts and dangling references are rejected.

The graph preserves 10 `owl:Class`, 73 `owl:DatatypeProperty` (72 static and one time-series),
and 15 `owl:ObjectProperty` with the original source/target as domain/range.
`BigInt`, `String` and `DateTime` map to `xsd:long`, `xsd:string` and `xsd:dateTime`; string-formatted dates stay strings.
Keys, key order, display properties, business metadata, 11 bindings and 15 contextualizations remain annotations.
Descriptions use `rdfs:comment`, synonyms use `skos:altLabel`, and every key/column-to-property mapping is retained.
The time-series annotation retains Municipality's `IncomingDonationAmountYen`, its raw `DonationEvents` source,
`DonatedAt` timestamp, and the exact `DonationAmountYen` / `MunicipalityID` column spellings.
All 53 non-`.platform` parts are also preserved losslessly as `fabric:definitionPart` / `fabric:definitionJson`.

`furusato:` identifies this repository's terms. `fabric:` is **this exporter’s custom annotation vocabulary**, not an official
Microsoft RDF vocabulary. Examples are `furusato:Donation`, `furusato:Donation__DonationAmountYen`,
and `furusato:DonationToMunicipality`. Property IRIs are entity-qualified to avoid unintended intersecting domains.
Custom annotation predicates and `skos:altLabel` are explicitly declared as `owl:AnnotationProperty`;
the checks also reject nonstandard predicates without a property declaration.

Turtle (`.ttl`) and RDF/XML (`.rdf`, `.owl`) round-trip to the same graph; `.rdf` and `.owl` are byte-identical.
The `.owl` file is not OWL/XML. Keys are not promoted to `owl:hasKey`, nor are dataset-specific cardinalities converted into
universal OWL integrity constraints. These are not directly importable Fabric definitions or executable connectors.
No donor/donation instances, live workspace/item IDs, endpoints or private evaluation logs are exported.
Source identity variables remain placeholders and deployment-specific `.platform` metadata is excluded.
Parsing and graph equality checks are not an OWL reasoner consistency proof or a guarantee of Fabric import compatibility.

### Relationship cardinality validation

`Test-OntologyCardinality.ps1` is a read-only validator for the fifteen ontology
relationships. It never writes, uploads, or mutates anything and needs no module
beyond PowerShell 7.

### Usage

```powershell
pwsh ./tools/ontology/Test-OntologyCardinality.ps1
```

Add `-Detailed` to print every passing check, or `-WorkshopRoot <path>` to
validate a copy of the workshop folder:

```powershell
pwsh ./tools/ontology/Test-OntologyCardinality.ps1 -WorkshopRoot ./workshop/v2.7.0 -Detailed
```

There are two derivation modes, and the script always states which one produced
the verdict.

- Default (actual-data mode): re-reads the packaged seed CSVs, recomputes node
  counts, edge counts and participation from the rows, checks the dataset
  manifest against that recomputation, and only then derives cardinality. This is
  the only mode that can prove the declaration is true of the shipped data.
- `-FromData:$false` (declared-count mode): uses the dataset-manifest counts
  alone. Faster, but it cannot detect a manifest that disagrees with the CSVs.
- `-SelfTest`: runs the built-in negative tests, mutating in-memory copies and
  asserting that all nine planted defects are detected. Nothing is written.

The script exits with code `0` when the cardinality contract holds and `1` with a
list of failures otherwise, so it can gate a release check. The expected result is
`Checks passed: 350` in the default actual-data mode, `Checks passed: 318` in
declared-count mode (`-FromData:$false`), and `Checks passed: 359` with
`-SelfTest`.

### Prerequisites

- PowerShell 7 (`pwsh`). No additional module is required.
- The ontology definitions, notebooks, contract and dataset manifest under
  `workshop/v2.7.0`.

### What it validates

| Area | Checks |
|---|---|
| Coverage | All fifteen relationships declare `direction`, `cardinality`, and `grain` |
| Metadata parity | `ontology-semantic-metadata.json` and the Notebook 02 embedded copy agree |
| Template parity | `ontology-full-definition-template.json` and the Notebook 03 embedded copy agree |
| Contract parity | `participant-workspace-contract.json` declares the same cardinality and the same endpoints |
| Inventory | The four sources list the same fifteen names, and the dataset manifest counts edges for all fifteen |
| Key uniqueness | The declared cardinality agrees with the shape derived from the packaged node and edge counts |

### How the derived cardinality works

Every relationship binding emits exactly one edge per row of its binding table,
so the side whose node count equals the edge count is the side whose key is
unique across that table:

| Observation | Derived cardinality |
|---|---|
| `edges == sourceNodes` and `edges == targetNodes` | `one-to-one` |
| `edges == targetNodes` | `one-to-many from <source entity>` |
| `edges == sourceNodes` | `many-to-one` |
| neither matches | `many-to-many` (declared as `zero-to-many …`) |

The counts come from `data/dataset-manifest.json` (`expected.nodeCounts` and
`expected.edgeCounts`), which Notebook 01 reproduces when it builds the Lakehouse
output tables. A declaration that contradicts those counts fails the run and
names the derived shape, the declared string, and all three counts.

### Reproducibility and limitations

Notebook 02 enforces the same contract at run time: `validate_manifest` rejects a
metadata manifest whose relationships omit `direction`, `cardinality`, or
`grain`, and reports every offending relationship in one message instead of
stopping at the first.
