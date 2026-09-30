# ワークショップ用データセット / Workshop dataset

[日本語](#日本語) | [English](#english)

---

## 日本語

**バージョン `2.7.0-realistic.1`** ／ チェックサム契約 `generated-realistic-v1`

Fabric IQ Ontology ワークショップで使用する、ふるさと納税を題材にした学習用データです。

### このデータについて

すべて**生成データ**です。実在の個人・世帯・事業者・寄付実績は含みません。

ただし、参加者が現実感を持って操作できるよう、次の点は実世界に合わせています。ここでの「整合」はデータセット内部での一貫性を指します。返礼品名・事業者名・品種名は合成した例示であり、実際の生産実績・産地認定・提供可否を証明するものではありません。

| 項目 | 内容 |
|---|---|
| 自治体 | 総務省の**実在する 6 桁 全国地方公共団体コード** 1,741 件（市 792／町 743／村 183／特別区 23） |
| 返礼品カテゴリ | 主要ポータルに準じた 30 分類（肉・肉加工品、魚介類・海産物、米・パン など） |
| 返礼品名 | 産地表記とカテゴリが内部的に整合する合成例（例：宮崎県産 黒毛和牛サーロイン、北海道産 ほたて貝柱）。実際の産地認定・品種の産地適合・現在の取扱いを示すものではありません |
| 事業者名 | 業種と所在地が内部的に整合する合成法人名（例：有限会社氷見漁業、株式会社五泉酒造）。実在の法人を示すものではありません |
| 寄付者名 | 実在頻度に沿った姓＋名の組み合わせ、28 種の職業 |
| 寄付金額 | 16 段階の丸め額（1 万円が最多で 29.055%） |
| 寄付時期 | 12 月に 38.1% が集中（駆け込み需要の再現） |
| 人気自治体 | Workshop 内の合成シナリオとして都城市を 1 位に重み付け。現実の最新年度ランキングを表すものではありません |

個人情報・資格情報・テナント ID・ワークスペース ID の類は一切含みません。

### ファイル一覧

| ファイル | 行数 | 列 |
|---|---:|---|
| `seed/prefectures.csv` | 47 | `PrefectureID,PrefectureName,PrefectureNameEn` |
| `seed/municipalities.csv` | 1,741 | `MunicipalityID,MunicipalityName,PrefectureID,PrefectureName` |
| `seed/categories.csv` | 30 | `CategoryID,CategoryName,CategoryNameEn` |
| `seed/gifts.csv` | 6,000 | `GiftID,GiftName,CategoryID,MunicipalityID,Notes,GiftNameEn` |
| `seed/businesses.csv` | 2,500 | `BusinessID,BusinessName,PrefectureID,BusinessType,PrefectureName,BusinessTypeEn` |
| `seed/business_gifts.csv` | 14,514 | `BusinessID,GiftID` |
| `seed/donors.csv` | 12,000 | `DonorID,DonorName,PrefectureID,Age,Occupation,PrefectureName,PrefectureNameEn,OccupationEn` |
| `seed/donation_orders.csv` | 80,000 | `DonationID,DonorID,MunicipalityID,GiftID,DonationAmountYen,DonatedAt,PaymentMethod` |

#### 増分イベント（Pipeline 演習用）

| ファイル | 行数 | 列 |
|---|---:|---|
| `increment/donation_events_001.csv` | 5,000 | `EventID,DonationID,DonorID,MunicipalityID,GiftID,DonationAmountYen,DonatedAt,PaymentMethod,WorkshopRunId,ParticipantAlias,SourceFile,PublishedAtUtc` |
| `increment/donation_events_002.csv` | 5,000 | 同上 |
| `increment/donation_events_003.csv` | 5,000 | 同上 |

- 静的データは 2025 年、増分イベントは **2026 年 8 月**です。期間は重なりません。
  観測ウィンドウは `2026-08-01T00:02:47Z` から `2026-08-31T23:58:20Z`（UTC）で、
  `dataset-manifest.json` の `expectedIncrement.observationWindowUtc` が正本です。
  `PublishedAtUtc` は 3 ファイルそれぞれ
  `2026-08-11T11:59:30Z` / `2026-08-21T14:20:02Z` / `2026-09-01T00:03:20Z` です。
- `DonatedAt` を UTC 日付で集計すると **8/1 から 8/31 まで 31 日すべてに行があり**、
  欠けた日はありません。1 日あたりの生データ行数は **最小 450 行・最大 582 行**で、
  すべての日がこの範囲に収まります（31 日合計 15,000 行）。
  正本は `dataset-manifest.json` の `expectedIncrement.dailyDistributionUtc` で、
  `tools/data/Test-IncrementConsistency.ps1` が 31 日の網羅と上下限を検証します。
- 3 ファイル合計 15,000 行のうち **EventID の重複が 100 件**あります。
  001 の末尾 100 行が 002 の先頭に再掲される構成で、
  producer がバッチを再送した状況を再現しています。
  業務値はまったく同じで、`WorkshopRunId` / `SourceFile` / `PublishedAtUtc` だけが異なります。
- 重複を除いた 14,900 件の金額合計は **252,058,000 円**です。
- すべてのイベントが実在の自治体・返礼品・寄付者に紐付きます。
  返礼品はその自治体が実際にカタログしているものだけが選ばれます。
- 取り込み経路は Data Pipeline のみです。Lakehouse の `Files/increment` から
  `DonationEvents` テーブルへ `DonationEvents_IncrementCsvMap` で Copy します。

- 文字コードは全 11 CSV とも **UTF-8（BOM なし）**、改行は **LF**、末尾は改行で終わります。
  `.gitattributes` の `*.csv -text` により clone しても変換されないため、
  `SHA256SUMS.txt` の値はこの状態のまま一致します。
- `MunicipalityID` は先頭ゼロを含む **6 桁文字列**です。Excel で開くと先頭ゼロが失われるため、
  編集せずそのまま Lakehouse へアップロードしてください。
- `DonatedAt` は UTC の ISO 8601（`YYYY-MM-DDTHH:MM:SSZ`）です。表示時のみ Asia/Tokyo へ変換します。

### Notebook 01 の完了後に一致すべき値

| 指標 | 期待値 |
|---|---:|
| 寄付件数 | 80,000 |
| 寄付総額 | **1,344,099,000 円** |
| 寄付 0 件の Donor | 18 |
| 寄付受入 0 件の Municipality | 10 |
| 登録返礼品 0 件の Supplier | 0 |

#### Ontology 出力テーブル

| テーブル | 行数 |
|---|---:|
| `ot_prefecture` | 47 |
| `ot_municipality` | 1,741 |
| `ot_donor` | 12,000 |
| `ot_gift_category` | 30 |
| `ot_gift` | 6,000 |
| `ot_supplier` | 2,500 |
| `ot_supplier_gift` | 14,514 |
| `ot_donation` | 80,000 |
| `ot_mun_category_metric` | 4,403 |
| `ot_pref_category_metric` | 662 |
| `ot_pref_donation_flow` | 2,209 |

10 Entity の Node 合計 **109,592** ／ 15 Relationship の Edge 合計 **297,303**

`ot_supplier_gift` は `SupplierProvidesGift` の mapping table（14,514 行）であり、
Entity type ではありません。したがって Node には数えず、Edge にだけ反映します。

#### 代表値

| 項目 | 値 |
|---|---|
| 寄付受入 1 位 | 452025 都城市（宮崎県） 1,813 件 / 41,151,000 円 |
| その自治体の 1 位カテゴリ | CategoryId 1 肉・肉加工品 1,147 件 / 28,901,000 円 |
| 東京都在住・累計 1 位の寄付者 | DonorId 2005075 野口啓介 8 件 / 383,000 円 |
| 東京都の受入 | 2,661 件 / 45,930,000 円 |
| 東京都在住者の寄付 | 8,784 件 / 146,543,000 円 |

> 東京都は「受入」と「住民の寄付」で値が異なります。
> Data Agent がどちらの意味かを確認せずに答えていないかを検証する題材です。

#### 増分イベント（2026 年 8 月）の代表値

| 項目 | 値 |
|---|---|
| 観測数・観測金額とも 1 位の自治体 | MunicipalityId `452025` 331 件 / 5,737,000 円 |
| 2 位 | MunicipalityId `272132` 155 件 / 2,453,000 円 |

生データ 15,000 行を `MunicipalityID` で集計した値で、
`DonationObservationSummaryForAgent`（重複除外前）と同じ粒度です。
件数と金額のどちらで並べても 1 位は同じ自治体で、2 位に対し両指標とも明確に上回ります。
正本は `dataset-manifest.json` の `expectedIncrement.curatedViewLeader` で、
`tools/data/Test-IncrementConsistency.ps1` が 3 つの CSV から再計算して検証します。

### 整合性の確認

`SHA256SUMS.txt` でダウンロードの完全性を確認できます。

```powershell
Get-FileHash workshop\v2.7.0\data\seed\donation_orders.csv -Algorithm SHA256
```

期待値と 1 文字でも異なる場合は再取得してください。
Git がテキストファイルの改行を変換すると値がずれるため、
リポジトリでは `.gitattributes` により変換を禁止しています。

より詳しい期待値は `dataset-manifest.json` にあります。

---

## English

**Version `2.7.0-realistic.1`** / checksum contract `generated-realistic-v1`

Learning data for the Fabric IQ Ontology workshop, built around the Japanese
*furusato* hometown-tax donation scenario.

### About this data

Every row is **generated data**. It contains no real individual, household,
supplier or donation record.

To let participants work with it realistically, the following aspects are
aligned with the real world. "Consistent" here means consistent *inside* the
dataset. Gift names, supplier names and produce varieties are synthesized
examples; they do not prove any actual production record, geographic
certification or current availability.

| Item | Content |
|---|---|
| Municipalities | 1,741 **real six-digit national local government codes** published by the Ministry of Internal Affairs and Communications (792 cities / 743 towns / 183 villages / 23 special wards) |
| Gift categories | 30 categories modelled on the major portals (meat and meat products, seafood, rice and bread, and so on) |
| Gift names | Synthesized examples whose origin wording and category are internally consistent (for example 宮崎県産 黒毛和牛サーロイン, 北海道産 ほたて貝柱). They do not indicate any actual geographic certification, variety-to-region fit, or current listing |
| Supplier names | Synthesized corporate names whose industry and location are internally consistent (for example 有限会社氷見漁業, 株式会社五泉酒造). They do not denote any real legal entity |
| Donor names | Family-name plus given-name combinations weighted by real-world frequency, across 28 occupations |
| Donation amounts | 16 rounded steps (10,000 JPY is the most frequent, at 29.055%) |
| Donation timing | 38.1% concentrated in December, reproducing the year-end rush |
| Popular municipality | Miyakonojo is weighted to first place as a synthetic in-workshop scenario. It does not represent any real latest-year ranking |

The dataset contains no personal information, no credentials, and no tenant or
workspace IDs of any kind.

### File inventory

| File | Rows | Columns |
|---|---:|---|
| `seed/prefectures.csv` | 47 | `PrefectureID,PrefectureName,PrefectureNameEn` |
| `seed/municipalities.csv` | 1,741 | `MunicipalityID,MunicipalityName,PrefectureID,PrefectureName` |
| `seed/categories.csv` | 30 | `CategoryID,CategoryName,CategoryNameEn` |
| `seed/gifts.csv` | 6,000 | `GiftID,GiftName,CategoryID,MunicipalityID,Notes,GiftNameEn` |
| `seed/businesses.csv` | 2,500 | `BusinessID,BusinessName,PrefectureID,BusinessType,PrefectureName,BusinessTypeEn` |
| `seed/business_gifts.csv` | 14,514 | `BusinessID,GiftID` |
| `seed/donors.csv` | 12,000 | `DonorID,DonorName,PrefectureID,Age,Occupation,PrefectureName,PrefectureNameEn,OccupationEn` |
| `seed/donation_orders.csv` | 80,000 | `DonationID,DonorID,MunicipalityID,GiftID,DonationAmountYen,DonatedAt,PaymentMethod` |

#### Increment events (for the Pipeline exercise)

| File | Rows | Columns |
|---|---:|---|
| `increment/donation_events_001.csv` | 5,000 | `EventID,DonationID,DonorID,MunicipalityID,GiftID,DonationAmountYen,DonatedAt,PaymentMethod,WorkshopRunId,ParticipantAlias,SourceFile,PublishedAtUtc` |
| `increment/donation_events_002.csv` | 5,000 | same as above |
| `increment/donation_events_003.csv` | 5,000 | same as above |

- The static data is from 2025 and the increment events are from **August 2026**.
  The periods do not overlap. The observation window runs from
  `2026-08-01T00:02:47Z` to `2026-08-31T23:58:20Z` (UTC), and
  `expectedIncrement.observationWindowUtc` in `dataset-manifest.json` is the
  source of truth. `PublishedAtUtc` for the three files is
  `2026-08-11T11:59:30Z` / `2026-08-21T14:20:02Z` / `2026-09-01T00:03:20Z`
  respectively.
- Aggregating `DonatedAt` by UTC date gives **rows on all 31 days from 8/1 through
  8/31**, with no missing day. The raw row count per day is **450 rows minimum and
  582 rows maximum**, and every day falls inside that range (15,000 rows across the
  31 days). The source of truth is
  `expectedIncrement.dailyDistributionUtc` in `dataset-manifest.json`, and
  `tools/data/Test-IncrementConsistency.ps1` validates both the 31-day coverage and
  the bounds.
- Of the 15,000 rows across the three files, **100 `EventID` values are duplicated**.
  The last 100 rows of file 001 reappear at the head of file 002, reproducing a
  producer that re-sent a batch. The business values are exactly the same; only
  `WorkshopRunId` / `SourceFile` / `PublishedAtUtc` differ.
- The 14,900 rows left after de-duplication total **252,058,000 JPY**.
- Every event ties to an existing municipality, gift and donor. Only a gift that
  the recipient municipality actually catalogs is ever selected.
- The only ingestion path is a Data Pipeline. It copies from `Files/increment` in
  the Lakehouse into the `DonationEvents` table using
  `DonationEvents_IncrementCsvMap`.

- All eleven CSVs are **UTF-8 without BOM** with **LF** line endings and a
  trailing newline. `*.csv -text` in `.gitattributes` prevents any conversion on
  clone, so the values in `SHA256SUMS.txt` match in exactly this state.
- `MunicipalityID` is a **six-character string** including leading zeros. Opening
  it in Excel drops the leading zeros, so upload the file to the Lakehouse as is,
  without editing.
- `DonatedAt` is ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ`). Convert to Asia/Tokyo
  for display only.

### Values that must match after Notebook 01

| Metric | Expected value |
|---|---:|
| Donation count | 80,000 |
| Donation total | **1,344,099,000 JPY** |
| Donors with zero donations | 18 |
| Municipalities that received zero donations | 10 |
| Suppliers with zero registered gifts | 0 |

#### Ontology output tables

| Table | Rows |
|---|---:|
| `ot_prefecture` | 47 |
| `ot_municipality` | 1,741 |
| `ot_donor` | 12,000 |
| `ot_gift_category` | 30 |
| `ot_gift` | 6,000 |
| `ot_supplier` | 2,500 |
| `ot_supplier_gift` | 14,514 |
| `ot_donation` | 80,000 |
| `ot_mun_category_metric` | 4,403 |
| `ot_pref_category_metric` | 662 |
| `ot_pref_donation_flow` | 2,209 |

Node total across the 10 entities **109,592** / edge total across the 15
relationships **297,303**

`ot_supplier_gift` is the mapping table for `SupplierProvidesGift` (14,514 rows),
not an entity type. It is therefore never counted as nodes and contributes to
edges only.

#### Representative values

| Item | Value |
|---|---|
| Top recipient | 452025 Miyakonojo (Miyazaki) 1,813 donations / 41,151,000 JPY |
| That municipality's top category | CategoryId 1 meat and meat products, 1,147 donations / 28,901,000 JPY |
| Top cumulative donor resident in Tokyo | DonorId 2005075 野口啓介, 8 donations / 383,000 JPY |
| Donations Tokyo received | 2,661 donations / 45,930,000 JPY |
| Donations made by Tokyo residents | 8,784 donations / 146,543,000 JPY |

> Tokyo has different values for "received" and "donated by residents".
> This is the material for checking whether the Data Agent answers without first
> confirming which of the two meanings was intended.

#### Representative values for the increment events (August 2026)

| Item | Value |
|---|---|
| Municipality ranked first by both observation count and observed amount | MunicipalityId `452025`, 331 observations / 5,737,000 JPY |
| Second place | MunicipalityId `272132`, 155 observations / 2,453,000 JPY |

These are the 15,000 raw rows aggregated by `MunicipalityID`, at the same grain as
`DonationObservationSummaryForAgent` (before de-duplication). The same
municipality ranks first whether you order by count or by amount, and it leads
second place clearly on both metrics. The source of truth is
`expectedIncrement.curatedViewLeader` in `dataset-manifest.json`, and
`tools/data/Test-IncrementConsistency.ps1` recomputes it from the three CSVs.

### Verifying integrity

`SHA256SUMS.txt` confirms the integrity of a download.

```powershell
Get-FileHash workshop\v2.7.0\data\seed\donation_orders.csv -Algorithm SHA256
```

If the value differs by even one character, download the file again.
A value drifts when Git converts the line endings of a text file, so the
repository forbids that conversion through `.gitattributes`.

More detailed expected values are in `dataset-manifest.json`.
