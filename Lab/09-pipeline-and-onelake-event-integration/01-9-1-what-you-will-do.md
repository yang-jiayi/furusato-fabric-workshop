# 9.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

8月の観測データは、次の流れで Eventhouse の DonationEvents にコピーされます。Lakehouse の Files/increment にファイルが作られると OneLake イベントで検知され、Activator のルールが Pipeline を起動します。この章では、1本目の donation_events_001.csv で、この流れを最後まで確認します。

確認する順番は、イベント → Activator の起動（activation）→ Pipeline の実行 → Copy の行数 → KQL の件数です。どこかが欠けたら、最初に欠けた段階だけを直します。この Activator は、13章の Ontology の Business Rules とは別の仕組みです。

準備するもの・確認すること

- 24.6で自分が配置した Pipeline（PL_Furusato_&lt;PID&gt;）と Activator（My activator_&lt;PID&gt;）を使います。未配置なら24.4〜24.6へ戻ります。Activator のルール TR_OneLake_FileCreated_IngestDonationEvents_001 は停止した状態で、末尾の _001 は参加者IDにかかわらず同じです。
- Files/increment が空で、DonationEvents が0行であることを確認します（8章）。

<details>
<summary>English</summary>

## 9.1 What you will do

The August observation data is copied into DonationEvents in the Eventhouse as follows: when a file is created in Files/increment of the Lakehouse, a OneLake event detects it and an Activator rule starts the Pipeline. In this chapter you follow this chain end to end with the first file, donation_events_001.csv.

Check in this order: event → Activator activation → Pipeline run → Copy row count → KQL count. If something is missing, fix only the first missing stage. This Activator is separate from the ontology Business Rules in Chapter 13.

Before you start

- Use the Pipeline (PL_Furusato_&lt;PID&gt;) and Activator (My activator_&lt;PID&gt;) you deployed in 24.6. If they are absent, return to 24.4–24.6. The Activator rule TR_OneLake_FileCreated_IngestDonationEvents_001 is stopped, and its _001 suffix is the same for every participant.
- Confirm that Files/increment is empty and that DonationEvents has zero rows (Chapter 8).

</details>
