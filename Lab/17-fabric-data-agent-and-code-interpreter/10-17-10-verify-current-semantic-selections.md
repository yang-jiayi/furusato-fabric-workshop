# 17.10 現行の Semantic 選択を確認する

[Lab 目次](../README.md) · [この章の目次](README.md)

selection-contract.json は path/type/is_selected のフラットな契約です。表示された全項目を確認し、記載された選択値を変えません。現在の構成は実際に選択済みの SQL テーブル、KQL 集計、モデルテーブル、Ontology entity に限られます。ソース探索により項目を追加したり、契約外の候補を展開したりしません。

テーブル名や件数だけでなく各 path と type を実定義に照合します。IDを直接比較できない場合は現在の定義で binding を解決し、意味の差分が残れば停止します。選択状態の表示だけで、実際の問い合わせや回答品質を確認済みとは扱いません。

<details>
<summary>English</summary>

## 17.10 Verify current semantic selections

selection-contract.json is a flat path/type/is_selected contract. Inspect every listed item and preserve its specified selection state. The current configuration is limited to the actually selected SQL tables, KQL summary, model tables and Ontology entities. Do not add items through source discovery or expand beyond the contract.

Reconcile every path and type against the live definition, not only table names or counts. If IDs cannot be compared directly, resolve bindings from the current definition and stop if semantic differences remain. A visible selection does not verify actual queries or answer quality.

</details>
