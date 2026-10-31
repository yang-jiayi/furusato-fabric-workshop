# 6.2 操作手順（3）

[Lab 目次](../README.md) · [この章の目次](README.md)

8. バインドの画面には、関係用のキー列（Municipality の PrefectureId など、全体で14列）も表示されることがあります。これらは Property の数に含めません。

> バインドには Lakehouse の管理テーブル（ot_*）を使います。外部の Delta テーブルや、列マッピング付きのテーブルは使いません。

> 標準構成では、概念だけを試す Unknown の Property を追加しません。Unknown の Property は、バインドするまで照会やプレビューに表示されません。

<details>
<summary>English</summary>

## 6.2 Steps

8. The binding screen may also show relationship key columns (such as PrefectureId on Municipality; 14 columns in total). Do not count them as properties.

> Bind to managed Lakehouse tables (ot_*). Do not use external Delta tables or tables with column mapping.

> Do not add concept-only properties of type Unknown to the standard setup. Unknown properties do not appear in queries or previews until bound.

</details>
