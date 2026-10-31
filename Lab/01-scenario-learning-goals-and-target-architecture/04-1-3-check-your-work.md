# 1.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 3つの経路が別々に書かれ、ot_* テーブルと Gold が別の箱になっている | Gold は Notebook 05 が品質処理した分析用のデータです。元の ot_* テーブルと同じものとして書いていないか見直します。 |
| Graph を、必要な部分だけを選んで実体化するものとして書いている | Ontology 全体が自動で Graph になるように書いた場合は直します。 |
| Business Rules から Activator の通知へ直接つながっていない | Rules は AI が説明に使う文脈です。ファイルの到着で Pipeline を動かす Activator は別の仕組みです（9章）。 |
| 静的データと8月の観測データを足し合わせていない | 80,000件の静的データと8月の 15,000行は別のデータで、粒度も期間も違います。合計が現れないように図を直します。 |

<details>
<summary>English</summary>

## 1.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| The three paths are sketched separately, and the ot_* tables and Gold are in separate boxes | Gold is analysis data produced by Notebook 05 quality processing. Check that you have not shown it as the same thing as the original ot_* tables. |
| The graph is shown as something you materialize selectively | If your sketch turns the whole ontology into a graph automatically, correct it. |
| Business Rules are not connected directly to Activator alerts | Rules are context for AI explanations. The Activator that starts the Pipeline when a file arrives is a separate mechanism (Chapter 9). |
| Static data and August observation data are not added together | The 80,000 static donations and the 15,000 August rows are separate data with different grain and period. Fix the sketch so that no combined total appears. |

</details>
