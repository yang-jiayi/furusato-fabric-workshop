# 17.8 入力先を決めて指示を設定する

[Lab 目次](../README.md) · [この章の目次](README.md)

17.16のコマンドが4つの指示・説明・選択・例をまとめて設定するので、通常は手で貼り付ける必要はありません。以下の4つの指示本文は配布プロファイルから直接収録した原文です。手作業で確認・復元する場合は、日本語版・英語版で同じ原文を使います。入力先にある文章をすべて選択して置き換え、見出し・ファイル名・説明・ハッシュ値は貼り付けません。本文を翻訳したり、別の欄の末尾に足したりしません。HTML の Copy または同梱 txt が長文のコピーに適しています。保存後に改行や記号が変わっていないか確認します。

**4つの指示と Gen2 Ontology の対応**

| 設定先 | 同梱ファイル | 操作 |
| --- | --- | --- |
| Agent instructions | global-instructions.txt | 全体の欄。追記せず全文置換 |
| Lakehouse SQL | lakehouse-instructions.txt | この SQL ソースの指示欄 |
| KQL Database | kusto-instructions.txt | この KQL ソースの指示欄 |
| Semantic model | semantic-model-instructions.txt | このモデルソースの指示欄 |
| Ontology (Gen2) | 挿入する指示ファイルなし | 同じ主 Ontology の選択と Entity 説明を保持 |

新規 Agent は3つの通常ソースを追加した後、画面の Ontology 区画から既存の主 Ontology を追加します。移行済み Agent は、その区画の同じ主 Ontology と選択を保持します。通常ソースの一覧が3件でも、主 Ontology が別にあれば欠落とは限りません。ontology-instructions.txt は旧形式用です。Gen2 の global や別ソースの欄には貼り付けず、Notebook 04 の初期定義も移行済み Agent に再適用しません。

<details>
<summary>English</summary>

## 17.8 Map fields and set instructions

The commands in 17.16 configure all four instructions, descriptions, selections and examples together, so manual pasting is normally unnecessary. The following four instruction bodies are included directly from the distributed profile. For manual inspection or restoration, follow these rules. Both guide languages use the same original text. Replace the whole destination field; do not paste headings, filenames, explanations or hashes. Do not translate the bodies or append them to another field. HTML Copy or the included txt files are convenient for long text; check that line breaks and symbols survived saving.

**Four instruction fields and the Gen2 ontology mapping**

| Destination | Included file | Action |
| --- | --- | --- |
| Agent instructions | global-instructions.txt | Agent-wide field; replace, do not append |
| Lakehouse SQL | lakehouse-instructions.txt | Instructions for this SQL source |
| KQL Database | kusto-instructions.txt | Instructions for this KQL source |
| Semantic model | semantic-model-instructions.txt | Instructions for this model source |
| Ontology (Gen2) | No instruction file to insert | Preserve the same main ontology selection and entity descriptions |

For a new agent, add the three ordinary sources, then add the existing main ontology through the ontology area. For a migrated agent, preserve the same main ontology and selections there. Three ordinary sources do not imply a missing ontology if it appears separately. ontology-instructions.txt is for the legacy format: never paste it into Gen2 global instructions or another source, and never reapply the Notebook 04 initial definition to a migrated agent.

</details>
