# 15.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Ontology agent（Ontology Copilot）は Ontology に組み込まれた AI で、Ontology の説明、データの照会、改善案の作成を会話で行えます。Plan モード（既定）では何も変更せず、案と読み取り専用のプレビューを示します。変更は、Act モードに切り替えたときだけ適用されます。

主 Ontology を使い、添付なし（A）とあり（B）の説明と未適用の提案を比べます。Plan の読み取りだけで終了し、標準構成を変更する Act や2件目の Ontology の作成は行いません。

準備するもの・確認すること

- 主 Ontology（ONT_Furusato_&lt;PID&gt;）の実際の定義を読み取り、10 Entity・15 Relationship の件数と、既存 Entity・Property・Relationship の ID、型、関係の始点・終点と向き、キー、バインド、共有参照、継承を比較用に保存します。DonationQualityScope が既にある場合や基準と一致しない場合は停止し、この演習のために削除・別 Ontology の作成は行いません。
- 配布フォルダーの attachments にある4つのファイル（`business-requirements.txt`、`data-dictionary.txt`、`domain-model.png`、`revision-requirements.txt`）を用意します。
- 改善や適用には、ワークスペースの共同作成者（Contributor）以上の権限が必要です。閲覧者（Viewer）は説明と照会だけができます。

<details>
<summary>English</summary>

## 15.1 What you will do

The Ontology agent (Ontology Copilot) is AI built into the ontology. In a conversation it can explain the ontology, query its data and draft improvements. In Plan mode (the default) it changes nothing and shows proposals with a read-only preview. Changes are applied only after you switch to Act mode.

Use the main ontology to compare explanations and unapplied proposals without attachments (A) and with attachments (B). Finish with read-only Plan; do not use Act to change the standard setup or create a second ontology.

Before you start

- Read the actual main ontology definition (ONT_Furusato_&lt;PID&gt;) and retain its ten entities, fifteen relationships and the existing entity/property/relationship IDs, types, relationship endpoints/directions, keys, bindings, shared references and inheritance for comparison. Stop if DonationQualityScope already exists or the baseline does not match; do not delete items or create another ontology for this exercise.
- Prepare the four files in the attachments folder of the distribution (`business-requirements.txt`, `data-dictionary.txt`, `domain-model.png` and `revision-requirements.txt`).
- Improving the ontology and applying changes require Contributor or higher in the workspace. Viewers can only explain and query.

</details>
