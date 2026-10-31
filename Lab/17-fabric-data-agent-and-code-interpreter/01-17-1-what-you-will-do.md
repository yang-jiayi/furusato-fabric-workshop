# 17.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Fabric Data Agent を1件だけ使い、Lakehouse（SQL）・KQL Database（KQL）・Ontology・Semantic model（DAX）の4つをソースにして、自然言語の質問に答えさせます。同じ Agent の Code Interpreter で、取得した結果から表やグラフ、CSV を作ります。

指示（Agent instructions）は回答の方針を伝えるもので、アクセス制御ではありません。回答を見るときは、本文だけでなく、使われたソース、実行されたクエリ、返された結果を確認します。

準備するもの・確認すること

- 最初に17.5の教材と実施順を確認します。作業フォルダーの Data Agent（DA_Furusato_&lt;PID&gt;）を1件だけ使い、既存の設定がある場合は保存してから変更します。17.6〜17.7でソースを用意し、17.16のコマンドで採用済みの設定を適用・公開・読み戻しします。17.8〜17.15には入力先、原文、確認方法を収録しています。
- 10章（時系列）と12章（Semantic model）が完了していることを確認します。

<details>
<summary>English</summary>

## 17.1 What you will do

Use exactly one Fabric Data Agent with four sources — the Lakehouse (SQL), the KQL database (KQL), the ontology and the semantic model (DAX) — to answer natural-language questions. Use Code Interpreter on the same agent to create tables, charts and CSV files from the results.

Agent instructions guide how the agent answers; they are not access control. When you review an answer, check not only its text but also the source used, the executed query and the returned results.

Before you start

- Start with the materials and order in 17.5. Use one Data Agent in your work folder (DA_Furusato_&lt;PID&gt;) and save any existing configuration before editing. Prepare sources in 17.6–17.7, then apply, publish and read back the adopted configuration with the commands in 17.16. Sections 17.8–17.15 contain field mappings, complete original text and verification steps.
- Confirm that Chapters 10 (time series) and 12 (semantic model) are complete.

</details>
