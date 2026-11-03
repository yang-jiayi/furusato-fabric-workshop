# Furusato Workshop 3.1.0 — deployment and evaluation

[Participant guide](../furusato-workshop-v3-1-0-complete.html) ·
[GitHub Lab](../../Lab/README.md) ·
[Participant ZIP](../Furusato_Workshop_v3.1.0_current.zip) ·
[Downloads and checksums](../README.md) ·
[Security](../../SECURITY.md)

## 日本語

### 参加者向け教材

現在の参加者向け教材は、日英 HTML、番号付き GitHub Lab、参加者 ZIP です。
ZIP には Notebook、データ、設定、ツール、テキスト形式の参照添付ファイルを含みます。
HTML と ZIP の SHA-256 を [チェックサム一覧](../SHA256SUMS.txt) で照合してください。
第15章の業務要件資料は `business-requirements.txt` です。

### デプロイ

1. 公開リポジトリを clone し、使用するコミットを固定します。Windows では PBIR の階層が深いため、clone 先に短いパスを選んでください。
2. dev/test/prod ごとに対象 Workspace・空 Folder・未使用 PID `001`–`999`・接続先・非公開の設定／証跡ルートを明示します。ID・資格情報は Git 外で管理し、配布 Notebook に固定しません。
3. 稼働中の capacity、権限、Ontology／Data Agent の提供条件を確認します。統合 SQL ヘルパーは Fabric Notebook driver 上の `pyodbc` と ODBC Driver 18 が必要です。
4. [第24章「クライアントを選び、共通のデプロイ手順を使う」](../../Lab/24-automated-deployment-operations-and-cleanup/10-24-10-choose-a-client-and-use-the-same-deployment-procedure.md)に従います。Notebook 04 のコース設定は `ENABLE_UNIFIED_DATA_AGENT=True`、`ENABLE_AI_REFERENCE_ARCHITECTURE=False` です。`APPLY_CHANGES=False` の preview、対象と `PLAN_SHA256` の確認、明示承認、apply の順に進みます。
5. 既存 Item を上書きせず、FileCreated・各増分・Graph・Notebook 05／Power BI を別々に確認します。トリガー不達を無言で手動取り込みへ置換したり、成功済みの取り込みを再実行したりしません。

### FileCreated の開始と配送確認

Notebook 04 は停止状態のルールを作るため、構築後に `start_rule` またはポータルの Start で正式に開始します。定義の `shouldRun=true` や UI の Running 表示だけでは稼働を確認したことになりません。自動化では [manage_activation.py の手順](../../tools/provisioning/activation.md)の preview と明示承認を使い、配布 SHA-256 と一致する完成 CSV を `If-None-Match: *` で作成します。

実 FileCreated、native activation、新しい Completed Pipeline Job を ID と Type／Subject／Source で対応付けます。Copy と SourceFile 別 KQL の件数・金額も確認してから次のファイルへ進みます。履歴の `DataNotAvailable` や複数イベントは停止条件です。終了時は `stop_rule` または Stop を使い、遅延 Job と実データを確認します。

### 評価

- **標準:** 現行ガイドの10問・84条件をそのまま使い、1問1会話で記録します。標準の手動評価とオフライン抽出に内部問題集は不要です。CI 演習は別枠です。
- **自動 campaign:** 標準に加えて、利用者が用意した非空の private held-out suite が必要です。`schema_version: 1`、`kind: "heldout"`、固有 ID・質問・判定条件・必要な query language を持つ `cases` を用意します。改善に使用した追加問題は以後「未見」ではなく回帰用です。
- **保存先:** 設定・問題・正解・生応答・レビューは、Git checkout の外の絶対パスへ保存します。凍結済みファイルは上書きしません。
- **承認:** `doctor`・`freeze`・`plan` は認証取得／ネットワーク送信をしません。実質問の送信は対象・構成・反復回数の確認と別承認後だけで、`--allow-submit-native-questions` が必須です。

## English

### Participant materials

The current participant materials are the bilingual HTML guide, numbered GitHub Lab
and participant ZIP. The ZIP contains notebooks, data, configuration, tools and
text-based reference attachments. Verify the HTML and ZIP SHA-256 values in the
[checksum list](../SHA256SUMS.txt). The Chapter 15 business requirements attachment
is `business-requirements.txt`.

### Deployment

1. Clone the public repository and pin the commit you will use. On Windows, choose a short clone path because the PBIR directory hierarchy is deep.
2. Explicitly select a Workspace, empty Folder, unused PID `001`–`999`, connections and private configuration/evidence roots for each dev/test/prod environment. Keep IDs and credentials outside Git and out of distributed notebooks.
3. Verify active capacity, permissions and Ontology/Data Agent feature availability. Unified SQL requires `pyodbc` and ODBC Driver 18 on the Fabric Notebook driver.
4. Follow [Chapter 24.10, “Choose a client and use the same deployment procedure”](../../Lab/24-automated-deployment-operations-and-cleanup/10-24-10-choose-a-client-and-use-the-same-deployment-procedure.md). Notebook 04 uses `ENABLE_UNIFIED_DATA_AGENT=True` and `ENABLE_AI_REFERENCE_ARCHITECTURE=False`. Preview with `APPLY_CHANGES=False`, inspect the target and `PLAN_SHA256`, obtain explicit approval, then apply.
5. Do not overwrite mismatched existing Items. Verify FileCreated, each increment, Graph, Notebook 05 and Power BI separately. Do not silently replace a failed trigger with manual ingestion or replay accepted data.

### FileCreated lifecycle and delivery checks

Notebook 04 creates the rule stopped. Explicitly use `start_rule` or portal Start
after provisioning; `shouldRun=true` or a UI Running label alone does not verify
operation. Use preview and explicit approval from the
[manage_activation.py procedure](../../tools/provisioning/activation.md). Create
the complete CSV whose SHA-256 matches the distributed artifact, with
`If-None-Match: *`.

Correlate the native file event, activation and new Completed Pipeline job using
IDs and Type/Subject/Source. Verify Copy and per-SourceFile KQL totals before the
next file. Treat `DataNotAvailable` history or multiple events as stop conditions.
Use `stop_rule` or Stop at completion and check for late jobs and data.

### Evaluation

- **Standard:** Use the guide's 10 questions and 84 conditions verbatim, with a fresh conversation per question. Manual standard evaluation and offline extraction require no internal question pack; CI exercises are separate.
- **Automated campaign:** In addition to the standard suite, provide a nonempty private held-out suite with `schema_version: 1`, `kind: "heldout"`, and `cases` containing unique IDs, questions, conditions and required query languages. Cases used for improvement become regression material, not unseen cases.
- **Storage:** Keep configuration, questions, expected answers, raw replies and reviews at an absolute path outside every Git checkout. Do not overwrite frozen files.
- **Authorization:** `doctor`, `freeze` and `plan` acquire no token and make no network request. Submit questions only after confirming scope, configuration and repetitions, with separate approval and `--allow-submit-native-questions`.
