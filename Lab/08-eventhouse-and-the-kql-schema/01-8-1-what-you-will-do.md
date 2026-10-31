# 8.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

8月の観測データは、静的な寄付とは別に、Eventhouse の KQL Database に保存します。この章では、取り込み先のテーブル、CSV の取り込みマッピング、Data Agent 用の集計ビューを準備・確認します。

KQL の管理コマンドが成功しても、データが届いたことにはなりません。データの到着は9章と10章で確認します。

準備するもの・確認すること

- 標準経路では24.6で作成した Eventhouse（EH_Furusato_&lt;PID&gt;）と同名の KQL Database を確認します。管理オブジェクトは配置済みなので定義を読み、再作成しません。手動構築を行う場合だけ、作業フォルダーの New item → Eventhouse でこの名前を指定します。同名の KQL Database も作成されます。
- 配布フォルダーの kql/Furusato_Eventhouse_Setup_v2.7.0.kql を開いておきます。

<details>
<summary>English</summary>

## 8.1 What you will do

The August observation data is stored in an Eventhouse KQL database, separately from the static donations. In this chapter you prepare and check the destination table, the CSV ingestion mapping and the summary view for the Data Agent.

A successful KQL management command does not mean that data has arrived. You check data arrival in Chapters 9 and 10.

Before you start

- In the standard route, inspect the Eventhouse (EH_Furusato_&lt;PID&gt;) and same-named KQL database created in 24.6. The management objects are already deployed; inspect their definitions without recreating them. Only for manual construction, use New item → Eventhouse in your work folder with this name; its same-named KQL database is created too.
- Open kql/Furusato_Eventhouse_Setup_v2.7.0.kql from the distribution.

</details>
