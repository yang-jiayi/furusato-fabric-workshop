# データセット検証ツール / Validate the packaged workshop dataset

[日本語](#日本語) | [English](#english)

---

## 日本語

`Test-IncrementConsistency.ps1` は、コミット済みの 11 本の CSV
（`seed/` 8 本と `increment/` 3 本）を対象とする**読み取り専用**の validator です。
書き込み、アップロード、変更は一切行わず、PowerShell 7 以外のモジュールも必要としません。

### 使い方

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1
```

`-Detailed` を付けると成功した検査もすべて出力します。`-DataRoot <path>` を付けると
data フォルダーのコピーを検証できます。

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v2.7.0/data -Detailed
```

データセット契約が満たされていればスクリプトは終了コード `0` で終了し、
満たされていなければ失敗一覧とともに `1` で終了します。そのためリリース検査の
gate として使用できます。期待される結果は `Checks passed: 219` です。

### 前提

- PowerShell 7（`pwsh`）。追加モジュールは不要です。
- `workshop/v2.7.0/data` 配下の CSV、`dataset-manifest.json`、`SHA256SUMS.txt`。

### 検証範囲

| 領域 | 検査内容 |
|---|---|
| エンコーディング | 11 本すべてが BOM なし UTF-8、LF 改行、末尾改行あり |
| 封印値 | SHA-256、バイト長、行数、ヘッダーを `dataset-manifest.json` と照合し、`SHA256SUMS.txt` とも一致すること |
| ファイル構成 | seed がちょうど 8 本、increment が 3 本、`core/` fixture が存在しないこと |
| 外部キー | Municipality→Prefecture、Donor→Prefecture、Supplier→Prefecture、Gift→Category、Gift→Municipality、supplier-gift ブリッジ、寄付の両粒度 |
| カタログ整合性 | 静的寄付および増分イベントのすべてが、受入自治体が実際にカタログしている返礼品を選んでいること |
| カタログ表記 | `静岡県産 さくらんぼ 佐藤錦` という返礼品名が存在せず、佐藤錦が静岡県に紐付かないこと。本リリースで改名した 3 行は名称・カテゴリ・自治体・注記・ASCII のみの `GiftNameEn` を厳密に維持すること。同梱の混在言語 `GiftNameEn` 行は減ってよいが増えてはならないこと |
| 分布 | 寄付合計、寄付 0 件の Donor と Municipality、支払方法の集合、丸め額の刻み、都道府県とカテゴリの網羅 |
| 観測窓 | すべての `DonatedAt` が承認済みの 2026 年 8 月 UTC 窓に入ること。ファイル別の `PublishedAtUtc`、`SourceFile`、`WorkshopRunId`、`DonatedAt` の並び順 |
| 識別子 | `EVT-FRS-######` 形式の EventID、6 文字の `MunicipalityID`、数値列が数字のみであること |
| 重複の形 | raw 15,000 / unique 14,900 / 重複 `EventID` 100 件。「001 の末尾 100 行が 002 の先頭 100 行として再出現する」形。業務値は同一で run メタデータだけが異なること |

期待値は `workshop/v2.7.0/data/dataset-manifest.json` から読み込みます。
したがって manifest が唯一の正本であり続けます。

### 再現性と既知の制限

`GiftNameEn` はファイル全体では gate しません。同梱 6,000 行のうち 4,005 行は
本リリース以前から英語列に日本語の単位表記（`12個`、`1式`、`1玉`）を含みます。
これはジェネレーターの慣習であり、実行時に修正する対象ではありません。
そのためスクリプトは、本リリースが著作した行だけを厳密に gate し、残りは
「欠陥が減ることはあっても増えないこと」を境界として検査します。

---

## English

`Test-IncrementConsistency.ps1` is a read-only validator for the eleven committed
CSV files (eight `seed/` files and three `increment/` files). It never writes,
uploads, or mutates anything and needs no module beyond PowerShell 7.

### Usage

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1
```

Add `-Detailed` to print every passing check, or `-DataRoot <path>` to validate a
copy of the data folder:

```powershell
pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v2.7.0/data -Detailed
```

The script exits with code `0` when the dataset contract holds and `1` with a list
of failures otherwise, so it can gate a release check. The expected result is
`Checks passed: 219`.

### Prerequisites

- PowerShell 7 (`pwsh`). No additional module is required.
- The CSVs, `dataset-manifest.json` and `SHA256SUMS.txt` under
  `workshop/v2.7.0/data`.

### What it validates

| Area | Checks |
|---|---|
| Encoding | UTF-8 without BOM, LF line endings, trailing newline for all eleven files |
| Seals | SHA-256, byte length, row count, and header against `dataset-manifest.json`, plus `SHA256SUMS.txt` agreement |
| Inventory | Exactly eight seed files, three increment files, and no `core/` fixture |
| Foreign keys | Municipality→Prefecture, Donor→Prefecture, Supplier→Prefecture, Gift→Category, Gift→Municipality, supplier-gift bridge, and both donation grains |
| Catalog integrity | Every static donation and every increment event selects a gift the recipient municipality actually catalogs |
| Catalog wording | No gift named `静岡県産 さくらんぼ 佐藤錦` and no 佐藤錦 attributed to Shizuoka; the three rows this release renamed keep their exact name, category, municipality, notes, and plain-ASCII `GiftNameEn`; the packaged mixed-language `GiftNameEn` rows may shrink but never grow |
| Distributions | Donation totals, donors and municipalities without donations, payment-method sets, rounded yen steps, prefecture and category coverage |
| Observation window | Every `DonatedAt` inside the approved August 2026 UTC window, per-file `PublishedAtUtc`, `SourceFile`, `WorkshopRunId`, and `DonatedAt` ordering |
| Identifiers | `EVT-FRS-######` event IDs, six-character `MunicipalityID`, digit-only numeric columns |
| Duplicate layout | 15,000 raw / 14,900 unique / 100 duplicated `EventID` values, the exact "last 100 rows of file 001 reappear as the first 100 rows of file 002" shape, and business values that repeat while only run metadata differs |

The expected values come from `workshop/v2.7.0/data/dataset-manifest.json`, so the
manifest stays the single source of truth.

### Reproducibility and known limitations

`GiftNameEn` is not gated file-wide: 4,005 of the 6,000 packaged rows predate this
release with a Japanese unit token in the English column (`12個`, `1式`, `1玉`), a
generator convention that is out of scope for a runtime fix. The script therefore
gates the rows this release authors exactly and bounds the rest so the defect can
shrink but never grow.
