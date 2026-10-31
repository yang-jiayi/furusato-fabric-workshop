# 2.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 各 Entity の粒度を1文で書ける | 書けない概念は、まだ設計が決まっていません。業務の問いに戻って決め直します。 |
| キーと表示名を分け、名前で結合していない | 先頭のゼロが消えていないか、同じ名前の自治体が混ざっていないかを確認します。 |
| JOIN の形だけを根拠に継承（is-a）を作っていない | Donor と Supplier のように役割が違うものを1つにまとめていたら、分け直します。 |
| すべての外部キーを Relationship にしていない | 業務上の意味がない経路は、誤った推論の原因になります。意味のある経路だけを残します。 |

<details>
<summary>English</summary>

## 2.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| You can state the grain of each entity in one sentence | A concept whose grain you cannot state is not designed yet. Go back to the business question and decide again. |
| Keys and display names are separate, and nothing joins on names | Check that leading zeros are kept and that same-named municipalities are not mixed up. |
| No is-a inheritance is created just because tables can be joined | If you merged different roles, such as Donor and Supplier, split them again. |
| Not every foreign key has become a relationship | Paths without business meaning lead to wrong inferences. Keep only meaningful paths. |

</details>
