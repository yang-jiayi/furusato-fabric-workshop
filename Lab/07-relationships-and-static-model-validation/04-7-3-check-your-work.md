# 7.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 15の Relationship の向きと列が表と一致する | 配置済み関係に差分があれば変更せず停止し、担当者へ確認します。不足分を作成中の場合だけ、保存前に表と照合します。 |
| 居住地・受入地・登録地の3つの経路を区別して説明できる | 3章の経路の説明に戻り、それぞれの経路がどの Relationship を通るかを書き出します。 |
| Graph やクエリで、関係の数が期待値と合う（16章で確認） | 多すぎる場合は多対多による重複や対応表の重複行を、少なすぎる場合は相手側に存在しないキー、型の違い、バインド漏れを調べます。 |

<details>
<summary>English</summary>

## 7.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| The direction and columns of all 15 relationships match the table | If an existing deployed relationship differs, stop without editing and consult the instructor. Only while creating a missing relationship, reconcile it with the table before saving. |
| You can explain the residence, recipient and registration paths separately | Go back to the path explanation in Chapter 3 and write down which relationships each path uses. |
| Relationship counts match the expected values in a graph or query (checked in Chapter 16) | If there are too many, look for duplication through many-to-many links or duplicate mapping rows; if there are too few, look for keys missing on the other side, type mismatches or missing bindings. |

</details>
