# 19.6 開始前に記録を固定する

[Lab 目次](../README.md) · [この章の目次](README.md)

1. registration.json に日時、実施者、baseline/finalの設定名、仮説、変更する指示欄だけを記入します。完全評価の初期値は49枠・290条件・600秒です。基本演習なら開始前にpractice-10、10、84へ変更し、用紙からoriginal / repeat=1以外の予定行を外します。
2. 第17章で確認した公開版の指示、ソースID、選択テーブル・列、例、Ontology、スキーマ、メジャーを保存し、registrationに保存先と公開定義のSHA-256を記入します。モデル名や容量が表示される場合も記録し、見えない値を推測しません。
3. データ配布版のSHA-256と、付録Aの件数・金額を実環境で確認した記録を保存します。同じCSVでも二重取り込みなら同じデータではありません。評価中はデータ更新、指示編集、モデル変更を止めます。変化した場合は比較不能と記録して新しい評価を登録します。
4. questions.csv、rubric.csv、canonical-public-suite.jsonは変更しません。日本語の固定質問を翻訳せず送ります。付録Cは同じ原文と期待値を掲載しています。採点基準と期待値をAgentの指示、例、ソース説明に追加しません。
5. 新しい修正の採用条件も先に固定します。初期案は、FAIL→PASSが1件以上、PASS→FAILが0件、実ソースの実行根拠と事実の正しさが悪化しないことです。過去の採用判断をこの条件で再採点せず、これからの変更に使います。

baselineの公開定義は最初の質問より前に保存します。finalの公開定義とそのSHA-256は、候補を適用・公開・読み戻した後、finalの最初の質問より前に追記します。未来のハッシュを推測しません。完全な公開定義を取得できない場合はその不足を記録し、画面から保存できた指示と選択の一致だけを確認済みとします。

ファイルのSHA-256を調べるには、第17章で使ったPythonのターミナルをZIP内のsourceフォルダー（Gitならリポジトリ直下）で開き、次を実行します。最初のコマンドの出力をdataManifestSha256へ記録します。2つ目は最後の引用符内を実際に保存した公開定義JSONのパスへ置き換え、該当する段階のPublishedDefinitionSha256へ記録します。公開定義が取得できなければ空欄と理由を残します。

**Readable wrapped view — Python: データ配布版**

<div>
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "workshop/v3.0.0-preview/data/dataset-manifest.json"
</div>

**Verbatim source follows; copy from the canonical block.**

**Python: データ配布版**

```python
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "workshop/v3.0.0-preview/data/dataset-manifest.json"
```

**Readable wrapped view — Python: 保存した公開定義**

<div>
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "&lt;published-definition-json-path&gt;"
</div>

**Verbatim source follows; copy from the canonical block.**

**Python: 保存した公開定義**

```python
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "<published-definition-json-path>"
```

**空の記録用紙の記入方法**

| 用紙の欄 | 記入する値 |
| --- | --- |
| phase / slot_id / suite / repeat / case_id | 配布済みの値を保持。1行が1質問枠です。 |
| started_at_utc / ended_at_utc | UTCのISO 8601時刻。例の形式: YYYY-MM-DDTHH:MM:SSZ。 |
| submission_status | sent / not_sent / unknown |
| response_status | completed / failed / timeout / blocked / unknown / not_run |
| private_answer_file / private_execution_file | Git外に保存した回答全文と実行詳細のファイル名。未取得は空欄にして理由をnotesへ。 |
| actual_sources / actual_query_languages | 実際に使われたソースとSQL/KQL/GQL/DAX。期待経路を転記しません。 |
| status / reason / private_evidence_file_and_location | 条件のPASS/FAIL/UNCLEAR/NA、理由、ファイル名と該当する行や画面。 |
| native_status / native_reason | 独立した実行確認のPASS/FAIL/UNCLEAR/NOT_REQUIREDと理由。これは過去の厳密な審査ツールと同一の判定ではありません。 |
| failure_category / extra_factual_errors | source / time / grain / meaning / execution。固定条件外の誤記も本文と根拠を記入。 |
| equal_question / equal_criterion / equal_data / included | 前後比較用のyes/no。included=noには除外理由と元の判定を残します。 |
| transition | 例: PASS→FAIL。全290行を対応付け、採用した行だけ残す操作はしません。 |

<details>
<summary>English</summary>

## 19.6 Freeze the registration before starting

1. Fill in registration.json with date, reviewer, phase configuration labels, hypothesis and permitted instruction fields. Defaults are 49 slots, 290 conditions and 600 seconds. For practice, change to practice-10, 10 and 84 and remove other planned rows before beginning.
2. Save the published instructions, source IDs, table/column selections, examples, ontology, schema and measures verified in Chapter 17. Record private file locations and the published-definition SHA-256. Record visible model/capacity information without guessing unavailable values.
3. Save the data-distribution SHA-256 and live checks of Appendix A counts and amounts. Duplicate ingestion changes the data even when CSVs match. Freeze data, instructions and model during evaluation; record any drift and register a new comparison.
4. Keep questions.csv, rubric.csv and canonical-public-suite.json unchanged. Send the fixed Japanese question without translation; Appendix C contains the same wording and answer keys. Never put criteria or expected answers into Agent instructions, examples or source descriptions.
5. Preregister the adoption rule for new revisions. Suggested defaults are at least one FAIL→PASS, zero PASS→FAIL, and no deterioration in actual-source query execution records or factual correctness. This is a rule for future changes, not a regrading of historical adoption.

Save the baseline publication before its first question. Add the final publication and its SHA-256 after applying, publishing and reading back the candidate, before the first final question. Never invent a future hash. If the complete published definition is unavailable, record that gap and claim only the instruction/selection checks actually made from the UI.

To calculate SHA-256, use the Chapter 17 Python terminal from the ZIP's source folder or the Git repository root. Record the first command's output as dataManifestSha256. In the second command, replace the final quoted path with your saved published-definition JSON and record its hash for that phase. If the publication cannot be obtained, leave its hash blank with the reason.

**Readable wrapped view — Python: data distribution**

<div>
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "workshop/v3.0.0-preview/data/dataset-manifest.json"
</div>

**Verbatim source follows; copy from the canonical block.**

**Python: data distribution**

```python
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "workshop/v3.0.0-preview/data/dataset-manifest.json"
```

**Readable wrapped view — Python: saved publication**

<div>
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "&lt;published-definition-json-path&gt;"
</div>

**Verbatim source follows; copy from the canonical block.**

**Python: saved publication**

```python
python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "<published-definition-json-path>"
```

**How to fill the blank records**

| Record fields | What to enter |
| --- | --- |
| phase / slot_id / suite / repeat / case_id | Keep the supplied values. Each slot row represents one planned submission. |
| started_at_utc / ended_at_utc | UTC ISO 8601 timestamps, in YYYY-MM-DDTHH:MM:SSZ form. |
| submission_status | sent / not_sent / unknown |
| response_status | completed / failed / timeout / blocked / unknown / not_run |
| private_answer_file / private_execution_file | Private files containing the entire answer and execution details. If unavailable, leave blank and explain in notes. |
| actual_sources / actual_query_languages | Sources and SQL/KQL/GQL/DAX actually observed; do not copy expected routes. |
| status / reason / private_evidence_file_and_location | Condition verdict, reason, and file plus line/screenshot location. |
| native_status / native_reason | Separate execution-review PASS/FAIL/UNCLEAR/NOT_REQUIRED with reason. This is not the historical strict-grader verdict. |
| failure_category / extra_factual_errors | source / time / grain / meaning / execution. Preserve errors beyond fixed criteria with supporting text/evidence. |
| equal_question / equal_criterion / equal_data / included | yes/no for pairing. An excluded row retains the reason and original verdicts. |
| transition | For example, PASS→FAIL. Pair all 290 rows; do not retain only favorable outcomes. |

</details>
