# 19.5 評価用ファイルと進め方を選ぶ

[Lab 目次](../README.md) · [この章の目次](README.md)

手順内のパスに含まれる v3.0.0-preview や v2.7.0、requirements-preview30.txt、build_preview30.py は、現在の配布物の固定フォルダー名・ファイル名であり、別の版を選ぶ指定ではありません。表示どおりの名前を使います。

配布ZIPを展開した場合、評価キットは source/workshop/v3.0.0-preview/data-agent/participant-evaluation にあります。Git checkout ではリポジトリ直下の workshop/v3.0.0-preview/data-agent/participant-evaluation を開きます。操作・採点・前後比較は、Git checkout では Lab/19-evaluate-and-improve-ai-answer-quality/ と docs/v3.1.0/current/guide/furusato-workshop-v3-1-0-complete.html の第19章・付録C、ZIP展開後はZIPルートの Lab/19-evaluate-and-improve-ai-answer-quality/ と guide/furusato-workshop-v3-1-0-complete.html を参照します。付録Cの Lab は Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/ です。実際の回答や実環境のIDは、Gitの外の自分専用フォルダーへ保存します。各templateを複製し、作業用ファイル名から -template を外します。JSONはテキストエディター、CSVはExcelなどで開けます。CSVのIDと時刻は文字列として取り込みます。

**質問枠 / 条件数（1段階）**

| 選択 | 1段階の実施範囲 | 用途 |
| --- | --- | --- |
| 基本演習 | T01–T10 × 1 = 10 / 84 | 操作と採点を学ぶ。全体の改善を断定しない。 |
| 公開問題の完全評価 | T01–T10 × 3 + B01–B19 × 1 = 49 / 290 | 今回の採用済み構成の再現確認と、次の修正の前後比較。 |

今回の設定を初めて適用した後は、まず再現確認として測定します。次の変更を試す場合は、その現在の公開版をbaselineとして保存し、変更後をfinalとして測ります。過去の未調整設定へ戻す必要はありません。同じ構成を2回測った差を指示変更の効果と呼びません。

完全評価のslots.csvは前後合計98行、conditions.csvは580行、paired.csvは290行です。行はbaseline/finalが交互に並ぶため、最初にphase=baselineでフィルターし、候補を公開してからphase=finalへ切り替えます。フィルターした行を削除しません。最初の再現確認だけならbaselineを実施し、finalは未実施の予定として残します。改善を報告するときは両段階を完了します。

<details>
<summary>English</summary>

## 19.5 Choose the evaluation files and scope

Path components such as v3.0.0-preview and v2.7.0, and filenames such as requirements-preview30.txt and build_preview30.py, are fixed folder and file names in the current distribution, not choices of separate editions. Use the names exactly as shown.

After extracting the distribution ZIP, the evaluation kit is in source/workshop/v3.0.0-preview/data-agent/participant-evaluation. In a Git checkout, open workshop/v3.0.0-preview/data-agent/participant-evaluation from the repository root. For the procedure, scoring and comparison, use Lab/19-evaluate-and-improve-ai-answer-quality/ and Chapter 19 and Appendix C in docs/v3.1.0/current/guide/furusato-workshop-v3-1-0-complete.html from a Git checkout; after ZIP extraction, use Lab/19-evaluate-and-improve-ai-answer-quality/ and guide/furusato-workshop-v3-1-0-complete.html from the ZIP root. The Appendix C Lab is Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/. Keep actual answers and live IDs in your own folder outside Git. Duplicate each template and remove -template from the working filename. Open JSON in a text editor and CSV in a spreadsheet; import IDs and timestamps as text.

**Question slots / conditions per phase**

| Choice | Scope per phase | Use |
| --- | --- | --- |
| Practice | T01–T10 × 1 = 10 / 84 | Learn the process; do not infer full-suite improvement. |
| Full public evaluation | T01–T10 × 3 + B01–B19 × 1 = 49 / 290 | Verify the adopted configuration and compare subsequent revisions. |

After first applying the adopted configuration, measure it as reproduction testing. For a subsequent change, save the current publication as baseline and measure the changed publication as final. Restoring a historical untuned configuration is unnecessary. Differences between unchanged configurations do not establish an instruction-change effect.

The full templates contain 98 slot rows, 580 condition rows and 290 paired rows. Baseline/final rows are interleaved: first filter phase=baseline, then switch to phase=final after publishing the candidate. Do not delete filtered rows. For initial reproduction testing, run baseline and retain final as planned but unrun; an improvement comparison requires both phases.

</details>
