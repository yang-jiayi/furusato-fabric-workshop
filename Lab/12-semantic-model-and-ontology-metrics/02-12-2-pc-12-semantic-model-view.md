# 12.2 操作手順（1）

[Lab 目次](../README.md) · [この章の目次](README.md)

1. Semantic model の「寄附」テーブルで、寄附総額 = SUM('寄附'[寄附金額])、寄附件数 = COUNTROWS('寄附')、平均寄附額 = DIVIDE([寄附総額], [寄附件数]) の定義と表示形式を確認します。

![初回 framing 後の Viewing モード。Data pane に5テーブルがあり、画面の一部に列と関係図が表示される。](../assets/pc-12-semantic-model-view.png)

初回 framing 後の Semantic model を Viewing モードで表示し、5テーブルが読み込まれ、一部の列と関係が見える状態です。図全体は表示範囲外です。構成の参考であり、DAX の結果は別の実クエリで確認します。

<details>
<summary>English</summary>

## 12.2 Steps

1. In the 寄附 table of the semantic model, check the definitions and formats: 寄附総額 = SUM('寄附'[寄附金額]), 寄附件数 = COUNTROWS('寄附') and 平均寄附額 = DIVIDE([寄附総額], [寄附件数]).

![Viewing mode after initial framing, with five tables in the Data pane and part of the columns and relationship diagram visible.](../assets/pc-12-semantic-model-view.png)

Semantic model in Viewing mode after initial framing, with five tables loaded and some columns and relationships visible. The full diagram is outside the viewport. This is a configuration illustration; verify DAX results with an actual query.

</details>
