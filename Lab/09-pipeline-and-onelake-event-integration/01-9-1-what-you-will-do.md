# 9.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

8月の観測データは、次の流れで Eventhouse の DonationEvents にコピーされます。Lakehouse の Files/increment にファイルが作られると OneLake イベントで検知され、Activator のルールが Pipeline を起動します。この章では、1本目の donation_events_001.csv で、この流れを最後まで確認します。

確認する順番は、イベント → Activator の起動（activation）→ Pipeline の実行 → Copy の行数 → KQL の件数です。どこかが欠けたら、最初に欠けた段階だけを直します。この Activator は、13章の Ontology の Business Rules とは別の仕組みです。

準備するもの・確認すること

- 以下のアップロード手順は、参加者自身が所有する新規ターゲットで、安全確認が完了し、対象テーブルと Files/increment が空の場合だけ行います。現在供給されている共有ワークスペースで既存の行や OneLake Delta が見つかった場合は、書き込まず10章の現状チェックへ進みます。Pipeline（PL_Furusato_&lt;PID&gt;）と Activator（My activator_&lt;PID&gt;）は自分の配置を使います。Activator のルール TR_OneLake_FileCreated_IngestDonationEvents_001 は停止した状態です。
- Files/increment が空で、DonationEvents が0行であることを確認します（8章）。

<details>
<summary>English</summary>

## 9.1 What you will do

The August observation data is copied into DonationEvents in the Eventhouse as follows: when a file is created in Files/increment of the Lakehouse, a OneLake event detects it and an Activator rule starts the Pipeline. In this chapter you follow this chain end to end with the first file, donation_events_001.csv.

Check in this order: event → Activator activation → Pipeline run → Copy row count → KQL count. If something is missing, fix only the first missing stage. This Activator is separate from the ontology Business Rules in Chapter 13.

Before you start

- Perform the uploads below only on a new target owned by the participant after safety checks pass and the table and Files/increment are empty. If existing rows or OneLake Delta are present in the currently supplied shared workspace, do not write; go to the current-state check in Chapter 10. Use your own Pipeline (PL_Furusato_&lt;PID&gt;) and Activator (My activator_&lt;PID&gt;). The Activator rule TR_OneLake_FileCreated_IngestDonationEvents_001 must be stopped.
- Confirm that Files/increment is empty and that DonationEvents has zero rows (Chapter 8).

</details>
