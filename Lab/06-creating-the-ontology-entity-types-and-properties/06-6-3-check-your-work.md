# 6.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 10の Entity type のキー・型・バインドが保存され、Instances に行が表示される | 行が出ない、またはエラーになる場合は、バインド先のテーブルと列、SQL analytics endpoint の同期を確認します。 |
| 静的 Property が合計72で、表の Property 数と一致する | 多い場合は関係用のキー列や不要な自動追加の Property を数えていないか、少ない場合はバインドし忘れた列がないかを確認します。 |
| 同じ名前の Property を別の型で作っていない | 名前が重なる場合は型をそろえます。複数の Entity type で共有する Property は14章で扱います。 |

<details>
<summary>English</summary>

## 6.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| Keys, types and bindings of all 10 entity types are saved and Instances shows rows | If no rows appear or an error occurs, check the bound table and columns and the SQL analytics endpoint synchronization. |
| There are 72 static properties in total, matching the table | If there are more, check that you are not counting relationship key columns or unwanted auto-added properties; if there are fewer, look for columns you forgot to bind. |
| No property name is reused with a different type | Align the types if names collide. Properties shared across entity types are covered in Chapter 14. |

</details>
