# 16.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 選んだ範囲の GQL の結果と、SQL のキーの組が一致する | 一部だけを実体化した場合、全体の期待値（Node 109,592・Edge 297,303）は当てはまりません。選んだ範囲の件数（Gift 6,000、Supplier 2,500、SupplierProvidesGift 14,514）で比べます。 |
| 実体化の完了と失敗を、現在の結果で区別した | InvalidPropertyType などの場合は、時系列を削除・変更せず、エラーと対象を記録して停止します。直接 Graph の照会と、native Ontology consumer や Manage graph の画面表示は、別々に確認します。 |
| Ineligible の項目の理由が分かる | ツールチップの理由を確認します。キーが無い、バインドされていない、Semantic model から作った、複数のテーブルにバインドされている Entity type は、対象外になることがあります。 |

<details>
<summary>English</summary>

## 16.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| GQL results for the selected scope match the key pairs in SQL | If you materialized only part of the model, the full-model expectations (109,592 nodes and 297,303 edges) do not apply. Compare with the counts for the selected scope (Gift 6,000, Supplier 2,500 and SupplierProvidesGift 14,514). |
| You distinguished completed and failed materialization using current results | For InvalidPropertyType or similar errors, record the error and target and stop without deleting or retyping the time series. Verify direct graph queries separately from native ontology consumption and the Manage graph display. |
| You know why items are Ineligible | Read the reason in the tooltip. Entity types without a key, without bindings, generated from a semantic model or bound to more than one table can be ineligible. |

</details>
