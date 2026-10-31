# 8.2 操作手順

[Lab 目次](../README.md) · [この章の目次](README.md)

1. KQL Database に対して KQL Queryset を開きます。
2. DonationEvents テーブルがすでにあるかを確認します。講師の配置などで作成済みの場合は、定義を確認するだけにして、コマンドを再実行しません。
3. まだ無い場合は、配布 KQL ファイルの管理コマンド（ドットで始まる5つ）を、上から順に1つずつ実行します。テーブル、CSV 取り込みマッピング、マテリアライズドビュー、保持ポリシー、キャッシュポリシーの順です。ビューは、データを取り込む前に作ります。
4. DonationEvents の12列と型が、次の定義のとおりかを確認します。

**KQL**

```kql
.create-merge table DonationEvents (
    EventID:string,
    DonationID:long,
    DonorID:long,
    MunicipalityID:string,
    GiftID:long,
    DonationAmountYen:long,
    DonatedAt:datetime,
    PaymentMethod:string,
    WorkshopRunId:string,
    ParticipantAlias:string,
    PublishedAtUtc:datetime,
    SourceFile:string
)
```

5. 取り込みマッピング DonationEvents_IncrementCsvMap は、12列を番号（Ordinal）で対応させます。CSV では SourceFile が PublishedAtUtc より前にあるため、番号はテーブルの列の順番と一致しません（SourceFile が10、PublishedAtUtc が11）。
6. 2つのオブジェクトの役割を区別します。DonationEvents は重複を含む観測をそのまま保存し、EventID を持つのはこのテーブルだけです。DonationObservationSummaryForAgent は「自治体 × 1分 × ファイル」単位の集計で、Data Agent が読むビューです。ビューに、重複を除く処理を独自に追加しません。
7. 取り込み前の DonationEvents の行数が0であることを確認します。想定外の行がある場合は先へ進まず、SourceFile ごとの件数を確認して講師に伝えます。

> KQL ファイルの後半には、取り込み後に使う確認用のクエリも入っています。管理コマンドではないので、この章では実行しません。

<details>
<summary>English</summary>

## 8.2 Steps

1. Open a KQL queryset for the KQL database.
2. Check whether the DonationEvents table already exists. If it was already created (for example by the instructor's deployment), only review its definition and do not rerun the commands.
3. If it does not exist, run the five management commands in the KQL file (those starting with a dot) one at a time from the top: table, CSV ingestion mapping, materialized view, retention policy and caching policy. Create the view before any data is ingested.
4. Check that the 12 columns and types of DonationEvents match the following definition.

**KQL**

```kql
.create-merge table DonationEvents (
    EventID:string,
    DonationID:long,
    DonorID:long,
    MunicipalityID:string,
    GiftID:long,
    DonationAmountYen:long,
    DonatedAt:datetime,
    PaymentMethod:string,
    WorkshopRunId:string,
    ParticipantAlias:string,
    PublishedAtUtc:datetime,
    SourceFile:string
)
```

5. The ingestion mapping DonationEvents_IncrementCsvMap maps the 12 columns by ordinal. In the CSV files, SourceFile comes before PublishedAtUtc, so the ordinals do not follow the table's column order (SourceFile is 10 and PublishedAtUtc is 11).
6. Distinguish the roles of the two objects. DonationEvents stores observations as they arrive, including duplicates, and is the only one with EventID. DonationObservationSummaryForAgent is a summary per municipality, one-minute bucket and file that the Data Agent reads. Never add deduplication to the view on your own.
7. Confirm that DonationEvents has zero rows before ingestion. If unexpected rows exist, do not continue; check the counts per SourceFile and tell the instructor.

> The second half of the KQL file contains verification queries for use after ingestion. They are not management commands; do not run them in this chapter.

</details>
