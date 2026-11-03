# 9.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

8月の観測データは、次の流れで Eventhouse の DonationEvents にコピーされます。Lakehouse の Files/increment にファイルが作られると OneLake イベントで検知され、Activator のルールが Pipeline を起動します。この章では、1本目の donation_events_001.csv で、この流れを最後まで確認します。

確認する順番は、イベント → Activator の起動（activation）→ Pipeline の実行 → Copy の行数 → KQL の件数です。どこかが欠けたら、最初に欠けた段階だけを直します。この Activator は、13章の Ontology の Business Rules とは別の仕組みです。

準備するもの・確認すること

- 以下のアップロード手順は、参加者自身が所有し操作の承認を得た新規ターゲットで、安全確認が完了し、対象の DonationEvents テーブルと Files/increment が空の場合だけ行います。対象の DonationEvents テーブル、Files/increment または OneLake Delta に既存データがある場合は書き込まず、10章の現状確認へ進みます。共有ワークスペース内の別リソースにデータがあることだけでは停止しません。自分の Pipeline（PL_Furusato_&lt;PID&gt;）と Activator（My activator_&lt;PID&gt;）を使い、ルール TR_OneLake_FileCreated_IngestDonationEvents_001 が停止していることを確認します。
- Files/increment が空で、DonationEvents が0行であることを確認します（8章）。

<details>
<summary>English</summary>

## 9.1 What you will do

The August observation data is copied into DonationEvents in the Eventhouse as follows: when a file is created in Files/increment of the Lakehouse, a OneLake event detects it and an Activator rule starts the Pipeline. In this chapter you follow this chain end to end with the first file, donation_events_001.csv.

Check in this order: event → Activator activation → Pipeline run → Copy row count → KQL count. If something is missing, fix only the first missing stage. This Activator is separate from the ontology Business Rules in Chapter 13.

Before you start

- Perform the uploads below only in a new target you own and are authorized to modify, after safety checks pass and its DonationEvents table and Files/increment are confirmed empty. If the target DonationEvents table, Files/increment or OneLake Delta already contains data, do not write; inspect the current state in Chapter 10. Data in unrelated resources elsewhere in the shared workspace alone is not a stop condition. Use your own Pipeline (PL_Furusato_&lt;PID&gt;) and Activator (My activator_&lt;PID&gt;), and confirm the TR_OneLake_FileCreated_IngestDonationEvents_001 rule is stopped.
- Confirm that Files/increment is empty and that DonationEvents has zero rows (Chapter 8).

</details>
