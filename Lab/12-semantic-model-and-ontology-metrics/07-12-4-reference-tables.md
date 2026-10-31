# 12.4 参照表

[Lab 目次](../README.md) · [この章の目次](README.md)

**データの種類ごとのメジャー**

| テーブル | メジャー | DAX | 書式 |
| --- | --- | --- | --- |
| 寄附 | 静的寄附総額 | CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "StaticSeed")) | ¥#,##0 |
| 寄附 | 静的寄附件数 | CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed")) | #,##0 |
| 寄附 | 受入増分寄附総額 | CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement")) | ¥#,##0 |
| 寄附 | 受入増分寄附件数 | CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement")) | #,##0 |

<details>
<summary>English</summary>

## 12.4 Reference tables

**Measures for each kind of data**

| Table | Measure | DAX | Format |
| --- | --- | --- | --- |
| 寄附 | 静的寄附総額 | CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "StaticSeed")) | ¥#,##0 |
| 寄附 | 静的寄附件数 | CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed")) | #,##0 |
| 寄附 | 受入増分寄附総額 | CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement")) | ¥#,##0 |
| 寄附 | 受入増分寄附件数 | CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement")) | #,##0 |

</details>
