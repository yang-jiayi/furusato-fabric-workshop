# 17.16 復旧・制約・評価

[Lab 目次](../README.md) · [この章の目次](README.md)

1. apply/publish の後に結果が不明なら、書込みを再送せず、その intent を保持して verify を読み取り専用で実行します。新しい変更が必要と判明しても、使用済みintentを再利用しません。所有者と現在の定義を確認した別手順に従います。
2. 現在の実験では、ファイルごとの時刻の12時間転記が誤ることがあります。fixture 001 の最終時刻は 11:54:30 UTC（現地表記 11:54:30 AM）で、23:54:30 ではありません。fixture 003 の開始時刻は 14:18:14 UTC（2:18:14 PM）で、02:18:14 ではありません。集計 join が誤って全体合計を各ファイルの合計として扱い、誤った「データなし」を返すこともあります。回答を独立に評価するときは、各 fixture の開始・終了時刻、UTC表示、期間と分母の定義、集計の粒度と各ファイルの合計が混同されていないことを確認します。
3. 高額寄付フラグの定義は寄付額が57,000円を超える場合（&gt; 57,000円）であり、57,000円以上ではありません。回答がこの定義や、実際の measure にある KEEPFILTERS の説明を省くことがあります。支払方法ランキングでは filter が落ちる場合があります。回答が閾値の厳密な不等号、measure 所有の filter の適用、ランキング対象の filter を説明・適用しているかを独立に確認します。GQL・structured output・DAX の十分な実行根拠もありません。正確さを示すために指示へ答えを追加せず、実際の source/query/result と説明を照合し、未確認または誤りはそのまま記録します。
4. 全ての回答を19章・付録Cで公開問題と条件により評価します。設定が一致しても、正確性や採用が示されたとは限りません。別の実環境におけるGraph model、GQL、時系列、mirroringは、それぞれ独立に前提と実行結果を確認します。

<details>
<summary>English</summary>

## 17.16 Recovery, limitations and evaluation

1. If the outcome after apply/publish is uncertain, preserve the intent and run read-only verify; never resend the write. If a new change is needed, do not reuse the spent intent. Follow a separate procedure after confirming ownership and the live definition.
2. Current experimental responses can transpose timestamps by 12 hours. Fixture 001 ends at 11:54:30 UTC (native 11:54:30 AM), not 23:54:30. Fixture 003 starts at 14:18:14 UTC (2:18:14 PM), not 02:18:14. A generated aggregate join can also mistake a grand total for per-file totals and return a false “no data.” In an independent answer review, check each fixture's start/end time, UTC labeling, period and denominator definitions, aggregation grain, and that per-file totals are not confused.
3. The high-value flag means donation amount &gt; JPY 57,000, not &gt;= JPY 57,000. An answer may omit this definition or an explanation of the actual measure-owned KEEPFILTERS. A payment-method ranking can also drop its filter. Independently check the strict threshold predicate, whether the measure-owned filter is applied and explained, and whether the ranking's filter is retained. Sufficient GQL, structured-output and DAX execution evidence is also missing. Do not add answers to the instructions to make them seem correct; reconcile actual sources/queries/results and explanations, and record unknowns or errors as observed.
4. Evaluate answers using the public questions and criteria in Chapter 19 and Appendix C. Matching configuration does not establish correctness or adoption. In any other environment, check Graph-model, GQL, time-series and mirroring prerequisites and execution results independently.

</details>
