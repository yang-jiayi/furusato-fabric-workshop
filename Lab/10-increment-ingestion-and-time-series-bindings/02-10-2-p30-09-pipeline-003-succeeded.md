# 10.2 操作手順（1）

[Lab 目次](../README.md) · [この章の目次](README.md)

1. 002・003をアップロードするのは、自分が所有し操作の承認を得たターゲットで、9章の001のイベント・Pipeline/Copy・KQL確認が完了し、対象に002・003の既存ファイルやデータがないことを確認した場合だけです。所有権・承認・対象状態のいずれかを確認できない場合や既存データがある場合は、書き込まず読み取りで現状を確認して講師に相談します。9章と同じ順で1本ずつ検証します。002 の期待値は5,000行・84,687,000円です。
2. 002 の確認が終わってから donation_events_003.csv をアップロードし、同じように確認します（5,000行・84,101,000円）。
3. 003 の Pipeline Recent runs と Copy の実際の状態を読み取り、実行 ID と対象ファイルを確認します。添付図は Pipeline/Copy の成功状態だけを示す例です。003 とのソース対応、読み書き行数・バイト数、自動起動、KQL の合計は証明しません。これらは実際のパラメーター・イベント/activation・Copy 出力・KQL 結果で個別に照合し、確認できないものは未確認と記録します。

![PL_Furusato_101 の実行画面。Copy data1 が Succeeded と表示される。](../assets/p30-09-pipeline-003-succeeded.png)

実際の PL_Furusato_101 の実行画面。1件の Pipeline 実行と Copy data1 が Succeeded です。この画面だけでは、対象ファイルとの対応、行数・バイト数、自動起動、KQL の合計は証明されません。

<details>
<summary>English</summary>

## 10.2 Steps

1. Upload 002 and 003 only to a target you own and are authorized to modify, after verifying the Chapter 9 event, Pipeline/Copy and KQL checks for 001, and confirming the target has no existing 002/003 files or data. If ownership, approval or target state is unclear, or relevant data already exists, do not write; inspect the current state and ask the instructor. Verify each file one at a time in the Chapter 9 sequence. Expected values for 002 are 5,000 rows / JPY 84,687,000.
2. After 002 is confirmed, upload donation_events_003.csv and check it in the same way (5,000 rows and JPY 84,101,000).
3. Read the actual Pipeline Recent runs and Copy status for 003, and check the run ID and target file. The figure illustrates a successful Pipeline/Copy status only. It does not prove source association with 003, rows/bytes, automatic triggering or KQL totals. Reconcile those separately using actual parameters, event/activation, Copy output and KQL results; record anything not verified as unverified.

![PL_Furusato_101 run view showing Copy data1 as Succeeded.](../assets/p30-09-pipeline-003-succeeded.png)

Actual PL_Furusato_101 run view showing one successful Pipeline run and Copy data1. This screen alone does not prove which source file it processed, row or byte counts, automatic triggering or KQL totals.

</details>
