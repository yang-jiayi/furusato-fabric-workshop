# 8.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

4. まだ無い場合に管理オブジェクトを作成する手順は、参加者自身が所有する新規ワークスペースでのみ、全ての事前確認が通った後に行います。現在供給されている共有ワークスペースでは、見つからない項目を作成せず停止します。許可された新規ターゲットでは、配布 KQL ファイルの管理コマンド（ドットで始まる5つ）を上から順に1つずつ実行します。テーブル、CSV 取り込みマッピング、マテリアライズドビュー、保持ポリシー、キャッシュポリシーの順です。ビューはデータ取り込み前に作ります。
5. DonationEvents の12列と型が、次の定義のとおりかを確認します。

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

6. 取り込みマッピング DonationEvents_IncrementCsvMap は、12列を番号（Ordinal）で対応させます。CSV では SourceFile が PublishedAtUtc より前にあるため、番号はテーブルの列の順番と一致しません（SourceFile が10、PublishedAtUtc が11）。
7. 2つのオブジェクトの役割を区別します。DonationEvents は重複を含む観測をそのまま保存し、EventID を持つのはこのテーブルだけです。DonationObservationSummaryForAgent は「自治体 × 1分 × ファイル」単位の集計で、Data Agent が読むビューです。ビューに、重複を除く処理を独自に追加しません。
8. 取り込み前の DonationEvents の行数が0であることを確認します。想定外の行がある場合は先へ進まず、SourceFile ごとの件数を確認して講師に伝えます。
9. 現在の配置では、上の5つの基本コマンドとは別の前提として、初回取り込みと Activator 用のファイルアップロードより前に DonationEvents だけの OneLake mirroring を有効にします。24.6の deploy-realtime の結果を確認し、所有者・承認済みフォルダー・12列の schema・RLS と既存 mirroring policy を読み取ります。RLS が有効、既存 policy が互換でない、または確認できない場合は停止し、セキュリティを無効にしません。データベース全体や集計ビューは有効にしません。
10. 参加者自身が所有する新規ワークスペースで、対象テーブルが空であり、所有範囲・承認済みフォルダー・schema・RLS・既存 policy の全項目を確認できた場合に限り、次の設定を適用します。現在供給されている共有ワークスペースでは設定を書き換えません。deploy-realtime で適用済みなら再実行せず、下の読み取りだけで IsEnabled=true と TargetLatencyInMinutes=5 を確認します。読み取りは許可した項目だけを出力し、ConnectionStrings を含む policy 応答を保存・共有しません。

**KQL**

```kql
.alter-merge table DonationEvents policy mirroring dataformat=parquet with (IsEnabled=true,TargetLatencyInMinutes=5);
```

11. 安全な読み取り確認（設定の確認であり、データ到着の証明ではありません）。

**KQL**

```kql
.show table DonationEvents policy mirroring
| project EntityName,
    IsEnabled=tobool(parse_json(Policy).IsEnabled),
    TargetLatencyInMinutes=toint(parse_json(Policy).TargetLatencyInMinutes),
    Backfill=tobool(parse_json(Policy).Backfill)
```

> KQL ファイルの後半には、取り込み後に使う確認用のクエリも入っています。管理コマンドではないので、この章では実行しません。

<details>
<summary>English</summary>

## 8.2 Steps

4. Create missing management objects only in a new workspace owned by the participant, after all prerequisite checks pass. In the currently supplied shared workspace, stop rather than creating anything that is missing. On an authorized new target, run the five management commands in the distributed KQL file (those starting with a dot) one at a time from the top: table, CSV ingestion mapping, materialized view, retention policy and caching policy. Create the view before data ingestion.
5. Check that the 12 columns and types of DonationEvents match the following definition.

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

6. The ingestion mapping DonationEvents_IncrementCsvMap maps the 12 columns by ordinal. In the CSV files, SourceFile comes before PublishedAtUtc, so the ordinals do not follow the table's column order (SourceFile is 10 and PublishedAtUtc is 11).
7. Distinguish the roles of the two objects. DonationEvents stores observations as they arrive, including duplicates, and is the only one with EventID. DonationObservationSummaryForAgent is a summary per municipality, one-minute bucket and file that the Data Agent reads. Never add deduplication to the view on your own.
8. Confirm that DonationEvents has zero rows before ingestion. If unexpected rows exist, do not continue; check the counts per SourceFile and tell the instructor.
9. For the current deployment, enabling OneLake mirroring only for DonationEvents is a prerequisite separate from the five base commands, before first ingestion and before uploading any Activator input. Inspect the deploy-realtime result in 24.6 and verify ownership, the approved folder, the 12-column schema, RLS and the existing mirroring policy. Stop if RLS is enabled, an existing policy is incompatible, or verification is unavailable; never disable security. Do not enable the whole database or the summary view.
10. Only in a new workspace owned by the participant, with an empty target table and verified ownership scope, approved folder, schema, RLS and existing policy, apply the following setting. Do not write settings in the currently supplied shared workspace. If deploy-realtime already applied it, do not repeat the write; use only the readback below to confirm IsEnabled=true and TargetLatencyInMinutes=5. Output only the allowlisted fields; never save or share a policy response containing ConnectionStrings.

**KQL**

```kql
.alter-merge table DonationEvents policy mirroring dataformat=parquet with (IsEnabled=true,TargetLatencyInMinutes=5);
```

11. Safe policy readback (configuration verification, not evidence of data arrival).

**KQL**

```kql
.show table DonationEvents policy mirroring
| project EntityName,
    IsEnabled=tobool(parse_json(Policy).IsEnabled),
    TargetLatencyInMinutes=toint(parse_json(Policy).TargetLatencyInMinutes),
    Backfill=tobool(parse_json(Policy).Backfill)
```

> The second half of the KQL file contains verification queries for use after ingestion. They are not management commands; do not run them in this chapter.

</details>
