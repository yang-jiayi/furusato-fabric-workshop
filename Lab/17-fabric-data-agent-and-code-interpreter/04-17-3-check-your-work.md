# 17.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| Data Agent は1件で、4つのソースと Code Interpreter が設定されている | 足りないソースは Add data で追加します。うまくいかないからといって、別の Agent を増やしません。 |
| 主 Ontology の選択と、実際の native consumer の状態を記録した | No data added、SchemaUnavailable、空の文脈、API version 非対応や definition.json 欠落のエラーがあれば講師に伝え、未達として記録します。通常の SQL の成功を Ontology の利用成功と扱わず、別の Ontology やダミーの定義ファイルを追加しません。 |
| 回答の数値が、実行されたクエリの結果と一致する | DataNotAvailable、スキーマだけの回答、Code Interpreter が呼ばれていない場合は、未達として記録します。 |

<details>
<summary>English</summary>

## 17.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| There is one Data Agent with four sources and Code Interpreter configured | Add missing sources with Add data. Do not create additional agents because something does not work. |
| You recorded selection of the main ontology and the actual native consumer state | Report No data added, SchemaUnavailable, empty context, unsupported API versions or missing-definition.json errors to the instructor and record them as not achieved. Ordinary SQL success does not prove ontology use; do not add another ontology or a dummy definition file. |
| The numbers in the answer match the results of the executed query | Record DataNotAvailable, schema-only answers and answers where Code Interpreter was not called as not achieved. |

</details>
