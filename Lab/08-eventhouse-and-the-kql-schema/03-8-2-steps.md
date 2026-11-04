# 8.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

4. 手動構築でまだ無い管理オブジェクトを作成する場合は、24.6の承認済み計画・ID・所有範囲で今回自分用に新規配置したリソースだけを対象にし、全ての事前確認が通った後に行います。許可された空の参加者用フォルダー内の owned scope、または参加者自身の Workspace が対象です。共有 Workspace であることだけでは停止理由になりませんが、講師が提供した共有リソースや他の参加者が所有・使用する既存リソースには書き込みません。所有範囲、folder ID、resource ID、計画の対応が確認できなければ停止します。許可された新規ターゲットでは、配布 KQL ファイルの管理コマンド（ドットで始まる5つ）を上から順に1つずつ実行します。テーブル、CSV 取り込みマッピング、マテリアライズドビュー、保持ポリシー、キャッシュポリシーの順です。ビューはデータ取り込み前に作ります。
5. DonationEvents の12列と型を、次の create-merge 定義と比較します。このコードは照合用です。配置済みの対象では実行せず、既存のクエリエディターの下書きを上書き・消去しません。DDL の実行は、前の手順で対象・操作が承認された新規手動構築の場合だけです。

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

6. 取り込みマッピング DonationEvents_IncrementCsvMap は、12列を番号（Ordinal）で対応させます。CSV では SourceFile が PublishedAtUtc より前にあるため、番号はテーブルの列の順番と一致しません（SourceFile が10、PublishedAtUtc が11）。確認だけを行う場合、Show ingestion mapping script メニューは受動的な詳細表示ではありません。現在のクエリエディターにコマンドを挿入し、自動実行する場合があるため、クエリを実行しない確認の代替には使いません。既存の下書きを上書き・消去しません。利用できる場合はコマンドの挿入・実行を伴わない詳細表示、または講師が確認した保存済み定義で全12項目を照合します。そのような確認経路がなければ停止して講師に確認し、推測や管理コマンドの再実行で補いません。
7. 2つのオブジェクトの役割を区別します。DonationEvents は重複を含む観測をそのまま保存し、EventID を持つのはこのテーブルだけです。DonationObservationSummaryForAgent は「自治体 × 1分 × ファイル」単位の集計で、Data Agent が読むビューです。ビューに、重複を除く処理を独自に追加しません。
8. 取り込み前の DonationEvents の行数が0であることを確認します。想定外の行がある場合は先へ進まず、SourceFile ごとの件数を確認して講師に伝えます。
9. 現在の配置では、上の5つの基本コマンドとは別の前提として、初回取り込みと Activator 用のファイルアップロードより前に DonationEvents だけの OneLake mirroring を有効にします。24.6の deploy-realtime の結果を確認し、所有者・承認済みフォルダー・12列の schema・RLS と既存 mirroring policy を読み取ります。RLS が有効、既存 policy が互換でない、または確認できない場合は停止し、セキュリティを無効にしません。データベース全体や集計ビューは有効にしません。
10. 24.6の承認済み計画と読み戻しで、参加者用として新規配置された Eventhouse/KQL Database と対象テーブルが空であり、所有範囲・フォルダー・resource ID・schema・RLS・既存 policy の全項目が一致すると確認できた場合に限り、次の設定を適用します。許可された空の参加者用フォルダー内の owned scope、または参加者自身の Workspace が対象です。講師が提供した共有リソースや他の参加者が所有・使用する既存リソースには設定を書きません。ID や計画の対応を確認できない場合は停止します。deploy-realtime で適用済みなら再実行せず、下の読み取りだけで IsEnabled=true と TargetLatencyInMinutes=5 を確認します。読み取りは許可した項目だけを出力し、ConnectionStrings を含む policy 応答を保存・共有しません。

**Readable wrapped view — KQL**

<div>
.alter-merge table DonationEvents policy mirroring dataformat=parquet with (IsEnabled=true,TargetLatencyInMinutes=5);
</div>

**Verbatim source follows; copy from the canonical block.**

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

4. When manual construction requires a missing management object, act only on resources newly provisioned for you under the approved Chapter 24.6 plan, IDs and ownership scope, after all prerequisite checks pass. This may be an owned scope in an approved empty participant folder or your own workspace. A shared workspace alone is not a reason to stop, but never write to supplied shared resources or existing resources owned or used by another participant. Stop if ownership, folder ID, resource ID and plan alignment cannot be verified. On that authorized new target, run the five management commands in the distributed KQL file (those starting with a dot) one at a time from the top: table, CSV ingestion mapping, materialized view, retention policy and caching policy. Create the view before data ingestion.
5. Compare the 12 DonationEvents columns and types with the create-merge definition below. This code is for comparison: do not execute it against an already provisioned target or overwrite/clear an existing query-editor draft. Execute DDL only for the authorized new manual-construction target and operation described in the preceding step.

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

6. The ingestion mapping DonationEvents_IncrementCsvMap maps the 12 columns by ordinal. In the CSV files, SourceFile comes before PublishedAtUtc, so the ordinals do not follow the table's column order (SourceFile is 10 and PublishedAtUtc is 11). For inspection only, Show ingestion mapping script is not a passive details view: it can insert a command into the current query editor and execute it automatically. Do not use it as a no-query fallback or overwrite/clear an existing draft. If available, compare all 12 entries through a genuinely passive details view that neither inserts nor executes a command, or an instructor-verified persisted definition. If neither route is available, stop and ask the instructor; do not guess or rerun management commands.
7. Distinguish the roles of the two objects. DonationEvents stores observations as they arrive, including duplicates, and is the only one with EventID. DonationObservationSummaryForAgent is a summary per municipality, one-minute bucket and file that the Data Agent reads. Never add deduplication to the view on your own.
8. Confirm that DonationEvents has zero rows before ingestion. If unexpected rows exist, do not continue; check the counts per SourceFile and tell the instructor.
9. For the current deployment, enabling OneLake mirroring only for DonationEvents is a prerequisite separate from the five base commands, before first ingestion and before uploading any Activator input. Inspect the deploy-realtime result in 24.6 and verify ownership, the approved folder, the 12-column schema, RLS and the existing mirroring policy. Stop if RLS is enabled, an existing policy is incompatible, or verification is unavailable; never disable security. Do not enable the whole database or the summary view.
10. Apply the setting only when the approved Chapter 24.6 plan and readback verify that the Eventhouse/KQL database and empty target table were newly provisioned for you, and that ownership scope, folder, resource ID, schema, RLS and existing policy all match. The target may be an owned scope in an approved empty participant folder or your own workspace. Never change settings on supplied shared resources or existing resources owned or used by another participant. Stop if IDs or plan alignment cannot be verified. If deploy-realtime already applied the setting, do not repeat the write; use only the readback below to confirm IsEnabled=true and TargetLatencyInMinutes=5. Output only the allowlisted fields; never save or share a policy response containing ConnectionStrings.

**Readable wrapped view — KQL**

<div>
.alter-merge table DonationEvents policy mirroring dataformat=parquet with (IsEnabled=true,TargetLatencyInMinutes=5);
</div>

**Verbatim source follows; copy from the canonical block.**

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
