# データ検証チェックリスト / Data validation checklist（v2.7.0 Core）

[日本語](#日本語) | [English](#english)

---

## 日本語

Core ハンズオンの各ゲートで、この表と実測値を照合します。
**1 つでも一致しない場合は先へ進まず、その章の手順をやり直してください。**

対象バージョン: **2.7.0** / データセット契約: **2.7.0-realistic.1**
静的スナップショットは 2025 年、運用観測は 2026 年 8 月（UTC）です。

### 1. Notebook 01 の出力テーブル行数（第 6 章ゲート）

```sql
SELECT COUNT(*) FROM ot_prefecture;            -- 47
SELECT COUNT(*) FROM ot_municipality;          -- 1,741
SELECT COUNT(*) FROM ot_donor;                 -- 12,000
SELECT COUNT(*) FROM ot_gift_category;         -- 30
SELECT COUNT(*) FROM ot_gift;                  -- 6,000
SELECT COUNT(*) FROM ot_supplier;              -- 2,500
SELECT COUNT(*) FROM ot_supplier_gift;         -- 14,514
SELECT COUNT(*) FROM ot_donation;              -- 80,000
SELECT COUNT(*) FROM ot_mun_category_metric;   -- 4,403
SELECT COUNT(*) FROM ot_pref_category_metric;  -- 662
SELECT COUNT(*) FROM ot_pref_donation_flow;    -- 2,209
```

配布 CSV は静的 8 + 増分 3 = **11 ファイル**です。
`SHA256SUMS.txt` と `dataset-manifest.json` で完全性を確認してから取り込みます。

### 2. 金額の突合

```sql
SELECT SUM(DonationAmountYen) FROM ot_donation;   -- 1,344,099,000
```

集計テーブル 3 種（Donor / Municipality / Prefecture）も、
件数合計 **80,000**、金額合計 **1,344,099,000 円** に一致します。

### 3. 0 件レコード（LEFT JOIN で保持されること）

| 対象 | 件数 |
|---|---:|
| 寄付 0 件の Donor | 18 |
| 寄付受入 0 件の Municipality | 10 |
| 登録返礼品 0 件の Supplier | 0 |

### 4. Ontology のノード・エッジ（第 10 章 静的ゲート）

| 区分 | 期待値 |
|---|---:|
| Entity Type 数 | 10 |
| Relationship Type 数 | 15 |
| 静的 Property 数 | 72 |
| Node 合計（10 Entity） | 109,592 |
| Edge 合計（15 Relationship） | 297,303 |

内訳（Node）: 47 / 1,741 / 12,000 / 30 / 6,000 / 2,500 / 80,000 / 4,403 / 662 / 2,209

`ot_supplier_gift`（14,514 行）は Relationship の mapping table であり、
Node には数えません。`SupplierProvidesGift` の Edge 数にだけ使用します。

| Relationship Type | Origin → Target | Mapping table | Edge |
|---|---|---|---:|
| MunicipalityInPrefecture | Municipality → Prefecture | ot_municipality | 1,741 |
| DonorLivesInPrefecture | Donor → Prefecture | ot_donor | 12,000 |
| SupplierInPrefecture | Supplier → Prefecture | ot_supplier | 2,500 |
| GiftInCategory | Gift → GiftCategory | ot_gift | 6,000 |
| MunicipalityCatalogsGift | Municipality → Gift | ot_gift | 6,000 |
| SupplierProvidesGift | Supplier → Gift | ot_supplier_gift | 14,514 |
| DonorMadeDonation | Donor → Donation | ot_donation | 80,000 |
| DonationToMunicipality | Donation → Municipality | ot_donation | 80,000 |
| DonationSelectedGift | Donation → Gift | ot_donation | 80,000 |
| MunHasCategoryMetric | Municipality → MunicipalityCategoryMetric | ot_mun_category_metric | 4,403 |
| MunMetricForCategory | MunicipalityCategoryMetric → GiftCategory | ot_mun_category_metric | 4,403 |
| PrefHasCategoryMetric | Prefecture → PrefectureCategoryMetric | ot_pref_category_metric | 662 |
| PrefMetricForCategory | PrefectureCategoryMetric → GiftCategory | ot_pref_category_metric | 662 |
| ResidencePrefHasFlow | Prefecture → PrefectureDonationFlow | ot_pref_donation_flow | 2,209 |
| FlowToRecipientPref | PrefectureDonationFlow → Prefecture | ot_pref_donation_flow | 2,209 |

10 Entity Type は **基幹エンティティ層（マスタ 6 + トランザクション 1）** と
**集計層（メトリック 2 + フロー 1）** の 7 + 3 に分かれます。

#### 4.1 カーディナリティ（第 15 章で 15 / 15 件が登録される）

カーディナリティは UI の入力欄ではなく、Notebook 02 が登録する宣言メタデータです。
実データ側では次の 3 点で確認します。

| 確認 | 期待値 |
|---|---|
| many-to-one の Relationship | Edge 数 = Origin 側のインスタンス数 |
| MunicipalityInPrefecture | Edge 1,741 = Municipality 1,741 |
| SupplierProvidesGift（many-to-many） | Edge 14,514。Gift 6,000 とも Supplier 2,500 とも一致しない |

#### 4.2 メトリック / フロー Entity（第 10 章ゲート）

10 問のテストはこの 3 エンティティを直接は問わないため、ここで数値を確認します。

| 対象 | インスタンス | 期待値 |
|---|---|---|
| MunicipalityCategoryMetric | `452025-01`（都城市 × 肉・肉加工品） | 1,147 件 / 28,901,000 円 |
| 同上の全カテゴリ合計 | `452025` | 1,813 件 / 41,151,000 円 |
| PrefectureCategoryMetric | 全件 | 662（受入 Prefecture × カテゴリの組のうち寄付が 1 件以上あったもの。上限は 47 × 30 = 1,410 通り） |
| PrefectureDonationFlow（順方向） | `13-01`（東京都 → 北海道） | 637 件 / 9,918,000 円 |
| PrefectureDonationFlow（逆方向） | `01-13`（北海道 → 東京都） | 108 件 / 1,876,000 円 |

> 順方向と逆方向は別インスタンスであり、値も異なります。入れ替えて読み替えないでください。
> メトリック値どうしを足したり、スコープの違う値を混ぜたりしません。
> メトリック Entity の件数は「あり得る組み合わせの数」ではなく「実際に観測された組の数」です。

### 5. 2026 年 8 月の増分取り込み（第 13 章ゲート）

増分は Pipeline + OneLake FileCreated トリガーだけで取り込みます。
参加者が Pipeline を手動実行することはありません。
3 ファイルのうち **1 本目は第 12.4 節のゲートで取り込み済み**です。第 13 章でアップロードするのは
`donation_events_002.csv` と `donation_events_003.csv` の 2 本だけで、
1 本目を再アップロードすると同じ行が二重に入ります。
各実行が Succeeded になってから次を置き、2 本とも終わったらトリガーを Off に戻します。

#### 5.0 KQL 管理オブジェクト（第 11 章ゲート）

セットアップスクリプトが作成する管理オブジェクトは **5 個だけ**です。
射影テーブル・関数・update policy は v2.7.0 にはありません。

| # | オブジェクト | 種別 | 管理コマンド | 設定 |
|---:|---|---|---|---|
| 1 | `DonationEvents` | テーブル | `.create-merge table` | 12 列 |
| 2 | `DonationEvents_IncrementCsvMap` | ingestion csv mapping | `.create-or-alter table ... ingestion csv mapping` | 12 序数 |
| 3 | `DonationObservationSummaryForAgent` | マテリアライズドビュー | `.create-or-alter materialized-view` | on table DonationEvents |
| 4 | `DonationEvents` | ポリシー（retention） | `.alter table ... policy retention` | SoftDeletePeriod 90 日 |
| 5 | `DonationEvents` | ポリシー（caching） | `.alter table ... policy caching` | hot cache 7 日 |

#### 5.0.1 トリガーと Activator（第 12 章ゲート）

| 確認項目 | 期待値 |
|---|---|
| トリガー作成前の `Files/increment` | 空であること |
| Event type | `FileCreated` のみ |
| 監視対象 | `Files/increment` のみ |
| 自動生成された Activator の名前 | `My activator_<PID>` にリネーム済み |
| 1 本目の実行の `Subject` | 空でないこと（`Files/increment/donation_events_001.csv` を含む） |
| 導出されたファイル名 | アップロードしたファイルと一致すること |

> `IncrementFileName`（既定値 `donation_events_001.csv`）はファシリテーター向けの
> 診断・フォールバック専用です。`Subject` が空のまま実行されるとこの既定値が使われ、
> 1 本目のファイルが繰り返し取り込まれます。

#### 5.1 ファイル単位

| SourceFile | 行数 | 金額合計 | 最初の観測（UTC） | 最後の観測（UTC） | WorkshopRunId |
|---|---:|---:|---|---|---|
| `donation_events_001.csv` | 5,000 | 85,098,000 | 2026-08-01T00:02:47Z | 2026-08-11T11:54:30Z | `increment-run-001` |
| `donation_events_002.csv` | 5,000 | 84,687,000 | 2026-08-11T07:00:11Z | 2026-08-21T14:15:02Z | `increment-run-002` |
| `donation_events_003.csv` | 5,000 | 84,101,000 | 2026-08-21T14:18:14Z | 2026-08-31T23:58:20Z | `increment-run-003` |

`ParticipantAlias` はすべて `workshop-participant` です。

#### 5.2 3 ファイル全体

| 指標 | 期待値 |
|---|---:|
| raw 行数 | 15,000 |
| unique EventID | 14,900 |
| 重複 EventID | 100（各 2 回） |
| raw 金額合計 | 253,886,000 |
| 重複排除後の金額合計 | 252,058,000 |
| 観測窓（UTC） | 2026-08-01T00:02:47Z 〜 2026-08-31T23:58:20Z |

重複は「`donation_events_001.csv` の末尾 100 行が `donation_events_002.csv` の先頭 100 行として再出現する」形です。

#### 5.3 UTC 日次分布（検証済み）

観測時刻 `DonatedAt` は UTC の **2026-08-01 から 2026-08-31 までの 31 日**に分布し、
**欠測日はありません**。1 UTC 日あたりの raw 行数は **450〜582 行**（重複排除後は 450〜540 行）です。

```kql
DonationEvents
| summarize Rows=count(), TotalYen=sum(DonationAmountYen) by UtcDay=bin(DonatedAt, 1d)
| order by UtcDay asc
```

| UTC 日 | raw 行数 | raw 金額 | 重複排除後 | 備考 |
|---|---:|---:|---:|---|
| 2026-08-01 | 475 | 7,805,000 | 475 | |
| 2026-08-02 | 459 | 7,850,000 | 459 | |
| 2026-08-03 | 472 | 7,463,000 | 472 | |
| 2026-08-04 | 476 | 8,011,000 | 476 | |
| 2026-08-05 | 528 | 8,660,000 | 528 | |
| 2026-08-06 | 499 | 8,515,000 | 499 | |
| 2026-08-07 | 454 | 7,681,000 | 454 | |
| 2026-08-08 | 455 | 8,137,000 | 455 | |
| 2026-08-09 | 471 | 8,527,000 | 471 | |
| 2026-08-10 | 456 | 8,171,000 | 456 | |
| 2026-08-11 | **582** | 10,018,000 | 482 | 追加重複 100 行（100 EventID・該当 200 行） |
| 2026-08-12 | 479 | 7,707,000 | 479 | |
| 2026-08-13 | 504 | 8,002,000 | 504 | |
| 2026-08-14 | 482 | 7,902,000 | 482 | |
| 2026-08-15 | 498 | 8,743,000 | 498 | |
| 2026-08-16 | 478 | 7,829,000 | 478 | |
| 2026-08-17 | 540 | 9,846,000 | 540 | |
| 2026-08-18 | 462 | 7,615,000 | 462 | |
| 2026-08-19 | 476 | 7,961,000 | 476 | |
| 2026-08-20 | 464 | 8,131,000 | 464 | |
| 2026-08-21 | 472 | 8,162,000 | 472 | |
| 2026-08-22 | 489 | 8,070,000 | 489 | |
| 2026-08-23 | 478 | 7,751,000 | 478 | |
| 2026-08-24 | 490 | 8,085,000 | 490 | |
| 2026-08-25 | 487 | 8,375,000 | 487 | |
| 2026-08-26 | 481 | 8,063,000 | 481 | |
| 2026-08-27 | 498 | 8,415,000 | 498 | |
| 2026-08-28 | 466 | 8,013,000 | 466 | |
| 2026-08-29 | 478 | 8,222,000 | 478 | |
| 2026-08-30 | **450** | 7,419,000 | 450 | 最小 |
| 2026-08-31 | 501 | 8,737,000 | 501 | |
| **合計** | **15,000** | **253,886,000** | **14,900** | |

> 2026-08-11 だけ raw 582 行と多いのは、配布データの重複 **100 EventID** が
> この日に集中しているためです。重複する EventID は 2 行ずつ存在するため、
> 該当行は **200 行**、重複排除で取り除かれる **追加分は 100 行** です。
> したがって raw 582 − 追加重複 100 = **482 行** となり、日次上限は 540 行です。
> 「200 行が余分」ではありません。異常値でもありません。

#### 5.4 公開時刻と JST 境界（9 月 1 日が出るのは正常）

| PublishedAtUtc | 対象ファイル |
|---|---|
| 2026-08-11T11:59:30Z | `donation_events_001.csv` |
| 2026-08-21T14:20:02Z | `donation_events_002.csv` |
| **2026-09-01T00:03:20Z** | `donation_events_003.csv` |

JST は UTC + 9 時間です。したがって次の 2 つは **仕様どおりの挙動** であり、
観測窓外エラーでも取り込み漏れでもありません。

| 観点 | 値 | 説明 |
|---|---|---|
| UTC 月末の繰り上がり | UTC 2026-08-31T15:00:05Z 〜 2026-08-31T23:58:20Z の **178 行** | JST では **2026-09-01** の午前に入る |
| JST 換算の暦日数 | **32 日**（2026-08-01 〜 2026-09-01） | UTC の 31 日より 1 日多い |
| file 003 の公開時刻 | **2026-09-01T00:03:20Z** | 観測時刻ではなくファイルの公開時刻 |

> `DonatedAt`（観測時刻）と `PublishedAtUtc`（公開時刻）は別の列です。
> 日次検証は必ず UTC の `DonatedAt` で行い、日本時間で報告するときだけ変換して
> タイムゾーンを明記します。

#### 5.5 マテリアライズドビューとの突合

`DonationObservationSummaryForAgent` は分バケットの集約です。行数は観測件数ではありません。

| 指標 | 期待値 |
|---|---:|
| `sum(ObservationCount)` | 15,000 |
| `sum(ObservedAmountYen)` | 253,886,000 |
| `min(FirstObservedAt)` | 2026-08-01T00:02:47Z |
| `max(LastObservedAt)` | 2026-08-31T23:58:20Z |
| `bin(EventMinute, 1d)` の日数 | 31（欠測なし） |

このビューは `EventID` を公開しません。したがって **重複排除後の 14,900 件を
このビューから証明することはできません**。raw テーブル `DonationEvents` でのみ確認できます。

確認が終わったら OneLake トリガーを Off に戻します。
同じファイルを再投入すると二重計上されます。

### 6. Municipality の time-series バインディング（第 14 章）

| 設定項目 | 値 |
|---|---|
| バインディング種別 | TimeSeries |
| ソース | Eventhouse `DonationEvents` |
| タイムスタンプ列 | `DonatedAt`（UTC） |
| キー列 | `MunicipalityID` → `MunicipalityId` |
| 測定値 | `DonationAmountYen` → `IncomingDonationAmountYen` |

#### 6.1 観測が届いたことの確認（0 件なら先へ進まない）

| 確認項目 | 期待値 |
|---|---|
| 対象 Municipality | `452025`（8 月の観測金額が最大） |
| 8 月（UTC）の観測数 | 331 |
| 8 月（UTC）の観測金額 | 5,737,000 円 |
| 静的値との関係 | 別の値。1,813 件 / 41,151,000 円 とは足し合わせない |

> 0 件になる場合は（1）タイムスタンプ列が `DonatedAt` 以外、
> （2）キー列の対応付けが `MunicipalityID` → `MunicipalityId` になっていない、
> のいずれかです。修正して Ontology の更新完了を待ってから再確認します。

### 7. Notebook 02 のメタデータ件数（第 15 章ゲート）

| 対象 | 件数 |
|---|---:|
| Entity Type | 10 |
| 静的 Property | 72 |
| time-series Property | 1 |
| Relationship Type | 15 |
| **合計** | **98** |

time-series Property が存在しない状態で実行すると、preflight が
`Count mismatch for timeseriesProperties: Ontology has 0, manifest expects 1` を出して停止します。
定義へのパッチは生成されず、**1 件も登録されません**（部分適用はありません）。
このときの Ontology は 10 + 72 + 0 + 15 = **97** という前提条件の状態であり、
契約が要求するのは 10 + 72 + 1 + 15 = **98** です。
第 14 章のバインディングと Ontology の更新完了を先に確認してください。
Relationship のカーディナリティ 15 件もこの適用で登録されます。

### 8. 代表値（Data Agent の回答確認に使用）

| 項目 | 期待値 |
|---|---|
| 寄付受入 1 位の自治体 | 452025 都城市（宮崎県） 1,813 件 / 41,151,000 円 / 全国金額ランク 1 位 |
| その自治体の 1 位カテゴリ | CategoryId 1 肉・肉加工品 1,147 件 / 28,901,000 円 |
| 宮崎県（PrefectureId 45）の自治体数 | 26 |
| 東京都の受入 | 2,661 件 / 45,930,000 円 |
| 東京都在住者の寄付 | 8,784 件 / 146,543,000 円 |
| 東京都在住・累計 1 位の寄付者 | DonorId 2005075 野口啓介 8 件 / 383,000 円 |
| 8 月の観測 1 位の自治体 | 452025 331 観測 / 5,737,000 円 |

> 東京都は「受入」と「住民の寄付」で値が異なります。
> Data Agent にどちらの意味かを必ず確認させる設計です。

> 静的スナップショットの 80,000 件と 8 月の 15,000 観測は別データセットです。
> 合計 95,000 という値には意味がありません。決して足し合わせません。

### 9. Data Agent の構成（第 16 章）

| 項目 | 期待値 |
|---|---|
| ソース数 | 3（Lakehouse / Eventhouse / Ontology） |
| Lakehouse の対象テーブル | 11 個の `ot_*` |
| Lakehouse の例クエリ | 3 件（SQL） |
| Eventhouse の対象 | Materialized views の `DonationObservationSummaryForAgent` **1 件のみ** |
| Eventhouse で選択しないもの | Tables の `DonationEvents`（raw 観測。選ぶと T07 が成立しない） |
| Ontology のソース指示・例クエリ | なし（説明とセマンティックメタデータのみ） |
| Ontology の対象 Entity | 10 |
| Code Interpreter | 無効（Core） |

### 10. 最終確認

- [ ] 第 6 章のテーブル行数と金額がすべて一致する
- [ ] 第 10 章のノード 109,592 / エッジ 297,303 が一致する
- [ ] 第 10 章のメトリック `452025-01` = 1,147 件 / 28,901,000 円 が一致する
- [ ] 第 10 章のフロー `13-01` と `01-13` が別の値であることを確認した
- [ ] 第 11 章の KQL 管理オブジェクトが 5 個だけである
- [ ] 第 12 章で Activator を `My activator_<PID>` にリネームした
- [ ] 第 12 章の 1 本目で `Subject` が空でなく、導出ファイル名が一致した
- [ ] 第 13 章の raw 15,000 / unique 14,900 / 重複 100 が一致する
- [ ] UTC 日次分布が 31 日・欠測なし・1 日 450〜582 行に収まる
- [ ] JST の 2026-09-01（178 行）と file 003 の 2026-09-01T00:03:20Z を正常として扱った
- [ ] OneLake トリガーを Off に戻した
- [ ] 第 14 章で `452025` の 8 月観測 331 件 / 5,737,000 円 を確認した
- [ ] 第 15 章のメタデータ 98 件が登録された
- [ ] 第 17 章の 10 問がすべて PASS になった
- [ ] 公開後のスモークテストが通った

---

## English

Reconcile the measured values against these tables at every gate of the Core
hands-on. **If even one value does not match, do not continue: redo the steps in
that chapter.**

Target version: **2.7.0** / dataset contract: **2.7.0-realistic.1**
The static snapshot is from 2025; the operational observations are from August
2026 (UTC).

### 1. Notebook 01 output table row counts (Chapter 6 gate)

```sql
SELECT COUNT(*) FROM ot_prefecture;            -- 47
SELECT COUNT(*) FROM ot_municipality;          -- 1,741
SELECT COUNT(*) FROM ot_donor;                 -- 12,000
SELECT COUNT(*) FROM ot_gift_category;         -- 30
SELECT COUNT(*) FROM ot_gift;                  -- 6,000
SELECT COUNT(*) FROM ot_supplier;              -- 2,500
SELECT COUNT(*) FROM ot_supplier_gift;         -- 14,514
SELECT COUNT(*) FROM ot_donation;              -- 80,000
SELECT COUNT(*) FROM ot_mun_category_metric;   -- 4,403
SELECT COUNT(*) FROM ot_pref_category_metric;  -- 662
SELECT COUNT(*) FROM ot_pref_donation_flow;    -- 2,209
```

The packaged CSVs are 8 static + 3 increment = **11 files**.
Confirm integrity with `SHA256SUMS.txt` and `dataset-manifest.json` before
ingesting them.

### 2. Amount reconciliation

```sql
SELECT SUM(DonationAmountYen) FROM ot_donation;   -- 1,344,099,000
```

The three aggregate tables (Donor / Municipality / Prefecture) also match a total
count of **80,000** and a total amount of **1,344,099,000 JPY**.

### 3. Zero-count records (must be preserved by the LEFT JOIN)

| Subject | Count |
|---|---:|
| Donors with zero donations | 18 |
| Municipalities that received zero donations | 10 |
| Suppliers with zero registered gifts | 0 |

### 4. Ontology nodes and edges (Chapter 10 static gate)

| Category | Expected value |
|---|---:|
| Entity Types | 10 |
| Relationship Types | 15 |
| Static properties | 72 |
| Node total (10 entities) | 109,592 |
| Edge total (15 relationships) | 297,303 |

Node breakdown: 47 / 1,741 / 12,000 / 30 / 6,000 / 2,500 / 80,000 / 4,403 / 662 / 2,209

`ot_supplier_gift` (14,514 rows) is the mapping table of a relationship and is
never counted as nodes. It is used only for the edge count of
`SupplierProvidesGift`.

| Relationship Type | Origin → Target | Mapping table | Edges |
|---|---|---|---:|
| MunicipalityInPrefecture | Municipality → Prefecture | ot_municipality | 1,741 |
| DonorLivesInPrefecture | Donor → Prefecture | ot_donor | 12,000 |
| SupplierInPrefecture | Supplier → Prefecture | ot_supplier | 2,500 |
| GiftInCategory | Gift → GiftCategory | ot_gift | 6,000 |
| MunicipalityCatalogsGift | Municipality → Gift | ot_gift | 6,000 |
| SupplierProvidesGift | Supplier → Gift | ot_supplier_gift | 14,514 |
| DonorMadeDonation | Donor → Donation | ot_donation | 80,000 |
| DonationToMunicipality | Donation → Municipality | ot_donation | 80,000 |
| DonationSelectedGift | Donation → Gift | ot_donation | 80,000 |
| MunHasCategoryMetric | Municipality → MunicipalityCategoryMetric | ot_mun_category_metric | 4,403 |
| MunMetricForCategory | MunicipalityCategoryMetric → GiftCategory | ot_mun_category_metric | 4,403 |
| PrefHasCategoryMetric | Prefecture → PrefectureCategoryMetric | ot_pref_category_metric | 662 |
| PrefMetricForCategory | PrefectureCategoryMetric → GiftCategory | ot_pref_category_metric | 662 |
| ResidencePrefHasFlow | Prefecture → PrefectureDonationFlow | ot_pref_donation_flow | 2,209 |
| FlowToRecipientPref | PrefectureDonationFlow → Prefecture | ot_pref_donation_flow | 2,209 |

The 10 Entity Types split 7 + 3 into a **core entity layer (6 master + 1
transaction)** and an **aggregate layer (2 metric + 1 flow)**.

#### 4.1 Cardinality (15 of 15 are registered in Chapter 15)

Cardinality is not a UI input field; it is declarative metadata that Notebook 02
registers. On the data side, confirm it in these three ways.

| Check | Expected value |
|---|---|
| A many-to-one relationship | Edge count = instance count on the origin side |
| MunicipalityInPrefecture | Edge 1,741 = Municipality 1,741 |
| SupplierProvidesGift (many-to-many) | 14,514 edges, matching neither Gift 6,000 nor Supplier 2,500 |

#### 4.2 Metric / flow entities (Chapter 10 gate)

The ten held-out tests do not ask about these three entities directly, so verify
their values here.

| Subject | Instance | Expected value |
|---|---|---|
| MunicipalityCategoryMetric | `452025-01` (Miyakonojo × meat and meat products) | 1,147 donations / 28,901,000 JPY |
| All-category total for the same municipality | `452025` | 1,813 donations / 41,151,000 JPY |
| PrefectureCategoryMetric | All instances | 662 (recipient prefecture × category pairs that received at least one donation; the ceiling is 47 × 30 = 1,410 combinations) |
| PrefectureDonationFlow (forward) | `13-01` (Tokyo → Hokkaido) | 637 donations / 9,918,000 JPY |
| PrefectureDonationFlow (reverse) | `01-13` (Hokkaido → Tokyo) | 108 donations / 1,876,000 JPY |

> The forward and reverse directions are separate instances with different
> values. Never read one as the other.
> Never add metric values together, and never mix values of different scope.
> The instance count of a metric entity is the number of pairs actually observed,
> not the number of pairs that could exist.

### 5. August 2026 increment ingestion (Chapter 13 gate)

The increment is ingested only by the Pipeline plus the OneLake FileCreated
trigger. Participants never run the Pipeline by hand.
**The first of the three files has already been ingested at the Chapter 12.4
gate.** Chapter 13 uploads only the remaining two,
`donation_events_002.csv` and `donation_events_003.csv`; re-uploading the first
file would ingest the same rows twice.
Place the next file only after the previous run reports Succeeded, and turn the
trigger back Off once both are done.

#### 5.0 KQL management objects (Chapter 11 gate)

The setup script creates **exactly 5** management objects.
There is no projection table, function or update policy in v2.7.0.

| # | Object | Kind | Management command | Setting |
|---:|---|---|---|---|
| 1 | `DonationEvents` | table | `.create-merge table` | 12 columns |
| 2 | `DonationEvents_IncrementCsvMap` | ingestion csv mapping | `.create-or-alter table ... ingestion csv mapping` | 12 ordinals |
| 3 | `DonationObservationSummaryForAgent` | materialized view | `.create-or-alter materialized-view` | on table DonationEvents |
| 4 | `DonationEvents` | policy (retention) | `.alter table ... policy retention` | SoftDeletePeriod 90 days |
| 5 | `DonationEvents` | policy (caching) | `.alter table ... policy caching` | hot cache 7 days |

#### 5.0.1 Trigger and Activator (Chapter 12 gate)

| Check | Expected value |
|---|---|
| `Files/increment` before the trigger is created | Must be empty |
| Event type | `FileCreated` only |
| Watched path | `Files/increment` only |
| Name of the auto-created Activator | Renamed to `My activator_<PID>` |
| `Subject` of the first run | Must not be empty (it contains `Files/increment/donation_events_001.csv`) |
| Derived file name | Must match the uploaded file |

> `IncrementFileName` (default `donation_events_001.csv`) is for facilitator
> diagnostics and fallback only. If a run starts with an empty `Subject`, this
> default is used and the first file is ingested repeatedly.

#### 5.1 Per file

| SourceFile | Rows | Total amount | First observation (UTC) | Last observation (UTC) | WorkshopRunId |
|---|---:|---:|---|---|---|
| `donation_events_001.csv` | 5,000 | 85,098,000 | 2026-08-01T00:02:47Z | 2026-08-11T11:54:30Z | `increment-run-001` |
| `donation_events_002.csv` | 5,000 | 84,687,000 | 2026-08-11T07:00:11Z | 2026-08-21T14:15:02Z | `increment-run-002` |
| `donation_events_003.csv` | 5,000 | 84,101,000 | 2026-08-21T14:18:14Z | 2026-08-31T23:58:20Z | `increment-run-003` |

`ParticipantAlias` is `workshop-participant` in every row.

#### 5.2 All three files

| Metric | Expected value |
|---|---:|
| Raw rows | 15,000 |
| Unique EventID | 14,900 |
| Duplicated EventID | 100 (each appearing twice) |
| Raw total amount | 253,886,000 |
| Total amount after de-duplication | 252,058,000 |
| Observation window (UTC) | 2026-08-01T00:02:47Z to 2026-08-31T23:58:20Z |

The duplication has this exact shape: the last 100 rows of
`donation_events_001.csv` reappear as the first 100 rows of
`donation_events_002.csv`.

#### 5.3 UTC daily distribution (verified)

The observation timestamp `DonatedAt` is distributed across **all 31 days from
2026-08-01 to 2026-08-31** in UTC, with **no missing day**. The raw row count per
UTC day is **450 to 582 rows** (450 to 540 after de-duplication).

```kql
DonationEvents
| summarize Rows=count(), TotalYen=sum(DonationAmountYen) by UtcDay=bin(DonatedAt, 1d)
| order by UtcDay asc
```

| UTC day | Raw rows | Raw amount | After de-duplication | Note |
|---|---:|---:|---:|---|
| 2026-08-01 | 475 | 7,805,000 | 475 | |
| 2026-08-02 | 459 | 7,850,000 | 459 | |
| 2026-08-03 | 472 | 7,463,000 | 472 | |
| 2026-08-04 | 476 | 8,011,000 | 476 | |
| 2026-08-05 | 528 | 8,660,000 | 528 | |
| 2026-08-06 | 499 | 8,515,000 | 499 | |
| 2026-08-07 | 454 | 7,681,000 | 454 | |
| 2026-08-08 | 455 | 8,137,000 | 455 | |
| 2026-08-09 | 471 | 8,527,000 | 471 | |
| 2026-08-10 | 456 | 8,171,000 | 456 | |
| 2026-08-11 | **582** | 10,018,000 | 482 | 100 extra duplicate rows (100 EventIDs, 200 rows in those groups) |
| 2026-08-12 | 479 | 7,707,000 | 479 | |
| 2026-08-13 | 504 | 8,002,000 | 504 | |
| 2026-08-14 | 482 | 7,902,000 | 482 | |
| 2026-08-15 | 498 | 8,743,000 | 498 | |
| 2026-08-16 | 478 | 7,829,000 | 478 | |
| 2026-08-17 | 540 | 9,846,000 | 540 | |
| 2026-08-18 | 462 | 7,615,000 | 462 | |
| 2026-08-19 | 476 | 7,961,000 | 476 | |
| 2026-08-20 | 464 | 8,131,000 | 464 | |
| 2026-08-21 | 472 | 8,162,000 | 472 | |
| 2026-08-22 | 489 | 8,070,000 | 489 | |
| 2026-08-23 | 478 | 7,751,000 | 478 | |
| 2026-08-24 | 490 | 8,085,000 | 490 | |
| 2026-08-25 | 487 | 8,375,000 | 487 | |
| 2026-08-26 | 481 | 8,063,000 | 481 | |
| 2026-08-27 | 498 | 8,415,000 | 498 | |
| 2026-08-28 | 466 | 8,013,000 | 466 | |
| 2026-08-29 | 478 | 8,222,000 | 478 | |
| 2026-08-30 | **450** | 7,419,000 | 450 | minimum |
| 2026-08-31 | 501 | 8,737,000 | 501 | |
| **Total** | **15,000** | **253,886,000** | **14,900** | |

> Only 2026-08-11 is high, at 582 raw rows, because the **100 duplicated
> EventIDs** in the packaged data are concentrated on that day. Each duplicated
> EventID exists as two rows, so **200 rows** belong to those duplicate groups
> while the **extra rows removed by de-duplication are 100**.
> Therefore raw 582 − 100 extra duplicates = **482 rows**, and the daily ceiling
> is 540 rows.
> It is not "200 extra rows", and it is not an anomaly.

#### 5.4 Publication time and the JST boundary (a 1 September date is correct)

| PublishedAtUtc | File |
|---|---|
| 2026-08-11T11:59:30Z | `donation_events_001.csv` |
| 2026-08-21T14:20:02Z | `donation_events_002.csv` |
| **2026-09-01T00:03:20Z** | `donation_events_003.csv` |

JST is UTC + 9 hours. The following two facts are therefore **behaviour exactly
as specified**, not an out-of-window error and not a missed ingestion.

| Aspect | Value | Explanation |
|---|---|---|
| UTC month-end rollover | The **178 rows** between UTC 2026-08-31T15:00:05Z and 2026-08-31T23:58:20Z | In JST they fall in the morning of **2026-09-01** |
| Calendar days in JST | **32 days** (2026-08-01 to 2026-09-01) | One more than the 31 days in UTC |
| Publication time of file 003 | **2026-09-01T00:03:20Z** | The publication time of the file, not an observation time |

> `DonatedAt` (observation time) and `PublishedAtUtc` (publication time) are
> different columns.
> Always run the daily validation on `DonatedAt` in UTC, and convert only when
> reporting in Japan time, stating the time zone explicitly.

#### 5.5 Reconciling against the materialized view

`DonationObservationSummaryForAgent` is an aggregate over minute buckets. Its row
count is not the observation count.

| Metric | Expected value |
|---|---:|
| `sum(ObservationCount)` | 15,000 |
| `sum(ObservedAmountYen)` | 253,886,000 |
| `min(FirstObservedAt)` | 2026-08-01T00:02:47Z |
| `max(LastObservedAt)` | 2026-08-31T23:58:20Z |
| Number of days in `bin(EventMinute, 1d)` | 31 (none missing) |

This view does not expose `EventID`. **The 14,900 de-duplicated rows therefore
cannot be proved from this view**; they can only be confirmed on the raw table
`DonationEvents`.

Turn the OneLake trigger back Off once the checks are done.
Re-submitting the same file double-counts the rows.

### 6. Municipality time-series binding (Chapter 14)

| Setting | Value |
|---|---|
| Binding kind | TimeSeries |
| Source | Eventhouse `DonationEvents` |
| Timestamp column | `DonatedAt` (UTC) |
| Key column | `MunicipalityID` → `MunicipalityId` |
| Measure | `DonationAmountYen` → `IncomingDonationAmountYen` |

#### 6.1 Confirming the observations arrived (do not continue on zero rows)

| Check | Expected value |
|---|---|
| Target municipality | `452025` (largest observed August amount) |
| Observations in August (UTC) | 331 |
| Observed amount in August (UTC) | 5,737,000 JPY |
| Relationship to the static values | A different value. Never add it to 1,813 donations / 41,151,000 JPY |

> A zero result means either (1) the timestamp column is something other than
> `DonatedAt`, or (2) the key mapping is not `MunicipalityID` → `MunicipalityId`.
> Fix it, wait for the Ontology update to finish, and check again.

### 7. Notebook 02 metadata object count (Chapter 15 gate)

| Subject | Count |
|---|---:|
| Entity Type | 10 |
| Static property | 72 |
| Time-series property | 1 |
| Relationship Type | 15 |
| **Total** | **98** |

If it is run while the time-series property does not exist, preflight stops with
`Count mismatch for timeseriesProperties: Ontology has 0, manifest expects 1`.
No patch to the definition is generated and **nothing at all is registered**
(there is no partial application).
The Ontology is then in the precondition state 10 + 72 + 0 + 15 = **97**, while
the contract requires 10 + 72 + 1 + 15 = **98**.
Confirm the Chapter 14 binding and the completion of the Ontology update first.
The 15 relationship cardinalities are registered by this same application.

### 8. Representative values (used to check Data Agent answers)

| Item | Expected value |
|---|---|
| Top recipient municipality | 452025 Miyakonojo (Miyazaki) 1,813 donations / 41,151,000 JPY / rank 1 nationally by amount |
| That municipality's top category | CategoryId 1 meat and meat products, 1,147 donations / 28,901,000 JPY |
| Municipalities in Miyazaki (PrefectureId 45) | 26 |
| Donations Tokyo received | 2,661 donations / 45,930,000 JPY |
| Donations made by Tokyo residents | 8,784 donations / 146,543,000 JPY |
| Top cumulative donor resident in Tokyo | DonorId 2005075 野口啓介, 8 donations / 383,000 JPY |
| Top municipality by August observations | 452025, 331 observations / 5,737,000 JPY |

> Tokyo has different values for "received" and "donated by residents".
> The design requires the Data Agent to confirm which meaning was intended.

> The 80,000 static snapshot rows and the 15,000 August observations are separate
> datasets.
> A total of 95,000 is meaningless. They are never added together.

### 9. Data Agent configuration (Chapter 16)

| Item | Expected value |
|---|---|
| Number of sources | 3 (Lakehouse / Eventhouse / Ontology) |
| Lakehouse tables selected | The 11 `ot_*` tables |
| Lakehouse example queries | 3 (SQL) |
| Eventhouse selection | **Only** `DonationObservationSummaryForAgent` under Materialized views |
| Not selected in the Eventhouse | `DonationEvents` under Tables (raw observations; selecting it breaks T07) |
| Ontology source instructions and example queries | None (description and semantic metadata only) |
| Ontology entities selected | 10 |
| Code Interpreter | Disabled (Core) |

### 10. Final check

- [ ] Every table row count and amount in Chapter 6 matches
- [ ] Nodes 109,592 / edges 297,303 in Chapter 10 match
- [ ] The Chapter 10 metric `452025-01` = 1,147 donations / 28,901,000 JPY matches
- [ ] Confirmed that the Chapter 10 flows `13-01` and `01-13` hold different values
- [ ] There are exactly 5 KQL management objects in Chapter 11
- [ ] The Activator was renamed to `My activator_<PID>` in Chapter 12
- [ ] `Subject` was not empty on the first run in Chapter 12, and the derived file name matched
- [ ] Chapter 13 raw 15,000 / unique 14,900 / duplicated 100 all match
- [ ] The UTC daily distribution covers 31 days with no missing day and stays within 450 to 582 rows per day
- [ ] JST 2026-09-01 (178 rows) and file 003 at 2026-09-01T00:03:20Z were treated as correct
- [ ] The OneLake trigger was turned back Off
- [ ] Chapter 14 confirmed 331 August observations / 5,737,000 JPY for `452025`
- [ ] The 98 metadata objects of Chapter 15 were registered
- [ ] All ten held-out tests in Chapter 17 came out PASS
- [ ] The post-publication smoke test passed
