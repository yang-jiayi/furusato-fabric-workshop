# 手順の逸脱と対策 — 2026-10-07（第3報〜第6報）

[結果 JSON](result-followup-20261007.json) ·
[製品サポートへの報告内容](platform-support-cases.md) ·
[R8 の指示差分（採用）](r8-candidate-contracts.diff) ·
[R10 の指示差分（不採用）](r10-candidate-contracts.diff) ·
[R11 の指示差分（不採用）](r11-candidate-contracts.diff) ·
[運用手順（引き継ぎ）](../../../workshop/v3.0.0-preview/README-runtime.md) ·
[回帰ゲート](../../../tools/data-agent/README.md) ·
[SHA-256](SHA256SUMS.txt)

## 第6報 — Agent の指示の追加（R11）、モデルの説明の言葉、構成図（2026-10-09）

**B16・B19 の対策として Agent の指示を2つ加えた候補 R11 を、これまでと同じ手順で評価しました。
標準10問・84条件は 84／78 に上がりましたが、事前に決めた採用基準（回帰19問の内容 PASS 16 以上、B19 の PASS）に
届かず、本番は R8 のままです。Semantic model の説明は、ふだんの言葉に直して本番のモデルに反映しました。
手順書の1章には、v3 の構成図を加えました。**

### R11 の評価（B16・B19 の対策）

R8 に、次の2つの指示を加えました。

- ファイルの中やファイル間の重複を聞かれたら、判定できない理由とあわせて、ファイルごとの件数と金額を示す。
- 寄附金額と高額寄附フラグはモデルでは非表示だが、DAX では使える。

採用基準は、評価の前に記録しました。標準2回の平均が 74.5 以上、回帰19問（1回）の内容 PASS が 16 以上・事実 PASS が 17 以上、
B16 と B19 の内容がともに PASS。満たさなければ R8 に戻し、結果を見てから指示を直して再評価することはしない（候補は R11 だけ）、としました。

| 構成 | 標準84（1回目／2回目） | 回帰19問 事実／内容 | B16 事実／内容 | B19 事実／内容 | 判定 |
|---|---:|---:|:---:|:---:|---|
| R8（本番） | 76 ／ 74 | 16 ／ 14（1問は判定不能） | PASS ／ FAIL | FAIL ／ FAIL | — |
| R11 | **84 ／ 78** | 17 ／ 15 | PASS ／ PASS | FAIL ／ FAIL | 不採用（内容 15 が基準の 16 に届かず、B19 も FAIL） |

- **B16 は直りました。** 判定できない理由とあわせて、ファイルごとの件数と金額を示しました。
- **B19 は直りませんでした。** Agent は「行ごとの金額の列が公開されていないため数えられない」と答えます。
  Data Agent はモデルで非表示の列を使わないため、指示を加えるだけでは直せないと判断しました（下の「次の対策の候補」の1）。
- R11 で新しく失敗した問があります。B06（合計の 1,392件を書かずに内訳だけを示した）、B12（全国の順位を1位と答えた。正しくは2位）、
  B18（件数だけで、聞かれた金額を示さなかった）。
- 送り直しや通信の失敗はありません。各問は新しい会話で1回だけ送りました。
- 本番は R8 に戻し、定義が R8 の記録と一致することを確かめました。違いは公開時の説明文だけで、内部の名前を並べた英語の説明から
  「Furusato ワークショップの寄付データ（Lakehouse・Eventhouse・Ontology・Semantic model）について質問に答えます。」に変えました。

**T10 について:** R11 では2回とも、プラットフォームに止められずに回答しました（7／7）。本番の R8 でも採点に含めずに2回送ったところ、
1回目は止められ、2回目は回答しました。止められるかどうかは Agent の指示ではなく、プラットフォーム側の判定で変わると考えられます
（製品サポートへの報告は継続中です）。

### 4回目の未公開の確認問題12問（本番の構成で1回）

R11 を作る前に問題と期待値を固定し、採否を決めた後の本番の構成（R8）で1回だけ実行しました。

- **事実 11／12、内容 10／12。**
- Q04: 高額寄附フラグが付いた寄付の件数（1,392件）は正しいが、金額（114,690,000円）を「取得できない」と答えた。B19 と同じ原因です。
- Q11 の内容: 事業者の10社と ID は正しいが、カタログへの登録と実際の発送を分けて書いていない（厳しめに FAIL としました）。
- 著者が作成した問題で、独立した評価ではありません。
- 12問のうち7問の回答に「seed」「スナップショット」「raw」の言葉が残っています（下の「次の対策の候補」の2）。

### Semantic model の説明の言葉

- 寄附テーブルの説明7か所（テーブル1、メジャー5、列1）で、「静的seed」「静的スナップショット」「生観測」などの言葉を、
  「静的データ（配布した寄付データ全体）」「受入済みの増分」「Eventhouse の観測データ」などのふだんの言葉に直しました。
  12章の Metrics の画面に表示されます。メジャーの式は変えていません。
- 本番のモデルに反映して読み戻し、リポジトリと一致すること、変わったのは寄附テーブルの説明だけであることを確かめました。
  DAX の結果は変わりません（Gold 94,900件・1,596,157,000円、高額寄附 1,392件）。
- 配布する Notebook02〜04 はモデルの定義を含むため、作り直しました。

### 手順書

- 1章に v3 の構成図（Lakehouse・Eventhouse・Ontology・Semantic model・Data Agent のつながり）を加えました。
- **ポータルの画面の撮り直し（Version history、MCP の設定、Data Agent のソース、Graph の一部の選択）は、まだできていません。**
  この環境では、サインイン済みのブラウザー（InPrivate）のアドレスを確認できないため、画面の画像を取得できない仕組みになっています。

### 次の対策の候補（未実施）

1. **モデルの列「寄附金額」「高額寄附フラグ」を表示にする**（B19・Q04 の対策）。モデルの変更のため、ご承認をいただいてから、
   同じ手順（採用基準を先に記録し、標準2回・回帰19問・新しい確認問題）で評価します。
2. **Agent の回答に残る言葉を直す。** Agent の指示と例の言い方を直す必要があります。R9・R10 の経験から、データの呼び名に年を入れません。

### English summary (sixth report)

Candidate R11 added two instructions to R8: when duplicates cannot be determined,
also show each file's count and amount; the hidden model columns 寄附金額 and
高額寄附フラグ are usable in DAX. Measured with the same procedure and a rule recorded
in advance, it scored 84/84 and 78/84 on the standard ten (T10 was not blocked by
the platform in either run) and fact 17 / content 15 on the 19 regression questions.
B16 was fixed, but B19 still failed and B06, B12 and B18 regressed, so R11 missed the
rule (content ≥ 16 and B19 PASS) and production was restored to R8 and verified; only
the published description changed, to a plain sentence. Two informational T10 runs
on R8 were blocked once and answered once, so the block depends on the platform. The
fourth frozen 12-question check set, run once on the final configuration, scored fact
11/12 and content 10/12; Q04 failed for the same reason as B19 (the Data Agent does not
use hidden model columns). Seven semantic-model descriptions were reworded in plain
language and deployed (read back; DAX results unchanged), and a v3 architecture diagram
was added to chapter 1 of the guide. The portal screenshots could not be recaptured
from this environment. Next candidates: unhide the two model columns (needs approval)
and reword the Agent's instructions and examples that still produce internal terms.

---

## 第5報 — 追加5問の評価と参加者用の手順書（2026-10-08）

**本番の R8 で、第4報で追加した回帰の5問（B15〜B19）を1回ずつ実行しました。事実 4／5、内容 3／5 です。
あわせて、Word と HTML の手順書を参加者に配布する版に作り直し、手順に関係しない内容をすべて除きました。**

### 追加5問（B15〜B19）の結果（R8）

実行の前に、本番の定義が R8 と全17パーツで一致することを確かめました。各問は新しい会話で1回だけ送り、再送していません。
採点は、コミット済みの回帰スイートの条件をそのまま使いました。

| 問 | 内容 | 事実 | 内容 | 回答の要点 |
|---|---|:---:|:---:|---|
| B15 | 8月の観測で金額3位の自治体は、2025年の寄付データで何位か（3つのデータの突き合わせ） | PASS | PASS | 012190 紋別市、全国3位、北海道。突き合わせのキーも明示 |
| B16 | 2つのファイルの両方に同じ寄付があるか | PASS | FAIL | 判定できない理由（EventID がない）は正しいが、ファイルごとの件数と金額を示さなかった |
| B17 | 別のメジャーで結果が BLANK になる理由 | PASS | PASS | KEEPFILTERS と外側の条件の交差で説明 |
| B18 | 2025年3月と8月の観測の合算の依頼 | PASS | PASS | 合算を断り、2025年3月（日本時間）と8月の観測を別々に提示 |
| B19 | モデルで金額がちょうど100,000円の寄付の件数 | FAIL | FAIL | 「金額の列がない」と答えて件数を出さなかった（列は非表示なだけで、正しくは384件） |

- 19問の合計（B01〜B14 は 10/7 に同じ定義で測定）: 事実 16 PASS・2 FAIL・1 判定不能、内容 14 PASS・4 FAIL・1 判定不能。
- B16 と B19 の失敗は、第4報の確認問題（P02・P03）と同じ種類です。対策としては、Agent の指示に
  「ファイル間の重複を聞かれたら、判定できない理由とあわせてファイルごとの件数と金額を示す」
  「寄附金額・高額寄附フラグはモデルで非表示だが DAX で使える」を加える案が考えられます。
  Agent の設定は変えていません（ご指示があれば、これまでと同じ手順で候補として評価します）。
- B15・B17・B18 の回答には、まだ「seed」「スナップショット」などの言葉が残っています（R8 の既知の課題）。

### 参加者用の手順書（Word・HTML）

- **作り直した内容:** 各章を「この章で行うこと」「操作手順」「完了の確認」「参照表」「参考資料」だけで構成しました。
  手順の文章は、実際の画面操作をもとにした v3 の手順から書き直し、ふだんの言葉にそろえています。
- **除いた内容:** 旧版（v2.7）の本文の写し、評価の結果や過去の実行の記録、画面の撮影日時と「合格を証明しない」といった注記、
  リリースの注記、成果物のハッシュとコミット、作業用のメモ。配布用の ZIP からも評価レポートとリリースの状態ファイルを除きました。
- **画面のキャプチャ:** 48枚をすべて確認し、手順の確認に役立つ 28 枚を手順の該当箇所に置きました。説明文はすべて書き直しています。
  失敗した状態や古い手順の画面、作業用のメモや内部の版名が写っている画面は使っていません。
  旧版の構成図は「v2.7.0」の表示と古い説明が残っているため使っていません。
- **訂正:** 第3報・第4報で「時系列の設定の後に Notebook02 を実行する（98 オブジェクト）」と書きましたが、v3 の Notebook02 は
  handoff-ontology の記録後は動かない仕様で、件数の確認もありません。運用手順書を訂正し、記録後の Business Rule の編集は Ontology の画面で行う手順にしました。
- **確認:** Word 94 ページ、日英 HTML とあわせて 155 検査／0 FAIL。参加者用の版に作業用・履歴の言葉が含まれていないことも、検査で確かめています。

## 第4報 — 対策の順にすべて対応（同日 23:00 以降）

**R8 をご指示どおり本番に採用しました（標準10問・84条件 76/84・74/84）。言葉づかいをふだんの言葉に
直した候補 R9・R10 も評価しましたが、事前に決めた採用基準に届かず、本番は R8 のままです。
製品サポートへの報告2件を Fabric の管理ポータルから起票しました。Activator の自動配送と
時系列の設定は、ポータルの画面でしか行えない手順が残っています。**

### 回答精度（A〜D）

| 構成 | 標準84（1回目／2回目） | 公開の回帰14問 事実／内容 | 追加の確認12問（2回目のセット） 事実／内容 | 判定 |
|---|---:|---:|---:|---|
| R6（第2報の採用） | 74 ／ 73 | 14 ／ 13 | 9 ／ 7 | — |
| **R8（採用）** | **76 ／ 74** | 12 ／ 11（1問は通信タイムアウト） | 11 ／ 8 | ご指示で採用 |
| R9 ふだんの言葉＋重複・期間・金額・BLANK の型 | 76 ／ 70 | 13 ／ 13 | 12 ／ 12 | 不採用（標準の平均 73.0。2回目の1問は通信失敗で回答なし） |
| R10 R9＋合計の転記・倍率の確認 | 77 ／ 70 | 12 ／ 12 | 10 ／ 10 | 不採用（標準の平均 73.5。最後の候補） |

- 採用基準（標準2回の平均 74.5 以上、回帰の内容 PASS が R8 より2問以上多い、回帰の事実 PASS 13 以上、
  専門用語を含む回答が2件以下）は、各候補の結果を見る前に記録しました。
- R9 は専門用語を含む回答を 28件から 0件にし、回帰の質問も R8 より正確でしたが、標準の2回目で通信失敗が1問（6条件）あり、
  基準に届きませんでした。R10 では「2025年の寄付データ」という言い方が年での絞り込みと受け取られ、件数を誤る回答が出ました。
  次に言葉づかいを直すときは、データの呼び名に年を入れないことを勧めます。
- 本番は R8 に戻し、定義の14パーツがすべて R8 と一致することを確認しました。
- **新しく事前に固定した未公開の確認問題12問**（R8 の採用前に固定し、R8 で1回だけ実行）: 事実 11／12、内容 10／12。
  失敗は、2つのファイルの件数を別々に示さなかった問と、モデルで非表示の列を「存在しない」と答えた問です。
  著者が作成した問題で、独立した評価ではありません。

### サポートへの報告（E）

Azure のサポート API は Microsoft Fabric の問い合わせを Fabric の管理ポータルへ案内するため、
管理ポータルの「Help + support」から2件を起票しました（重大度 C、診断データへのアクセスは許可していません）。
内容は[報告内容](platform-support-cases.md)と同じです。

あわせて、Fabric のサービス正常性に「Ontology V2 を使う Data Agent で操作が完了しない」という
障害（2026-10-02 から、10-09 までに修正予定、回避策は V1 の Ontology を使うこと）が出ていました。
正式 Agent は V1 の互換 Ontology を使っており、この回避策と同じ構成です。

### 回帰ゲート（F）

公開の回帰スイートを 14問から **19問** にしました。追加した5問（B15〜B19）は、今回の確認問題で見つかった
失敗の種類（3つのデータを突き合わせる質問の順位違い、ファイル間の重複、別のメジャーの BLANK、
期間を指定した合算の依頼、モデルでの金額ちょうどの件数）を、リポジトリのデータから期待値を計算して確かめます。

### 手順書（G）と、ポータルで残る作業

- Activator のアクションは、この配置の Pipeline を正しく指していました（第3報の記述を訂正）。
  ポータルで必要なのは、Edit action → Apply → Save による遅延の許容時間の保存と、配送ごとの
  イベントの書き出しです。Pipeline の Copy の記録は、新しい読み取り専用ツールで API から取得できるようにしました。
- この環境のブラウザーは Activator と Ontology の編集画面（別ドメインの枠の中）を操作できず、
  サインイン済みの別のブラウザーも最小化されていて内容を読み取れなかったため、
  画面の操作は行っていません。**KQL のデータは消していません**（自動配送をやり直せる見込みがないまま消すと、
  8月の観測についての回答ができなくなるためです）。
- 時系列の設定・Notebook02・Generate Ontology（Metrics）も、ポータルの画面での作業が必要です。手順は[運用手順](../../../workshop/v3.0.0-preview/README-runtime.md)にあります。

### English summary (fourth report)

R8 was adopted on the user's instruction (standard ten/84: 76 and 74). Two
plain-wording candidates, R9 and R10, met the wording goal (answers with internal
terms fell from 28 to none) but missed the pre-recorded bar (standard means 73.0 and
73.5; R9 lost one answer to a network failure, and R10 read the plain dataset label
as a year filter once), so production was restored to R8 and verified part-for-part.
A newly frozen 12-question check set, run once on R8, scored fact 11/12 and content
10/12. Both support cases were filed through the Fabric admin portal (the Azure
Support API redirects Fabric). A Fabric service-health advisory affects Data Agents
that use Ontology V2; the formal Agent already uses the V1 compatibility ontology.
The public regression suite grew to 19 cases. The Activator action was found to
target the deployed Pipeline already (correcting the third report); the remaining
Activator and Ontology steps need the native portal UI, and the KQL data was left intact.

---

## 第3報（同日）

**2026-10-07 の配置で残っていた手順の逸脱4件と、対策 E・F・G、残件（T09・H09・欠落・B02・観測性）を
優先度順に実施しました。逸脱は2件完了、2件は UI でしか行えない手順が残り、手順書（引き継ぎ）を整備しました。
残件への新しい候補 R7・R8 は、その時点では事前に記録した採用規則を満たさなかったため採用せず、
本番の Agent は第2報の採用構成（R6）のままでした（第4報で、ご指示により R8 を採用）。**

### 手順からの逸脱

| # | 逸脱 | 状態 | 内容 |
|---|---|---|---|
| 1 | Activator による増分の自動配送 | **引き継ぎ（UI）** | ルールのアクションは、この配置の Pipeline を指しています（第3報の時点で「バンドル側の Pipeline を参照」と書いたのは誤りで、第4報で訂正しました）。配送の前に必要な遅延の許容時間の保存は、Activator の UI（Edit action → Apply → Save）でしか行えません。増分は手動で取り込み済みのため、再配送には承認されたリセット（KQL の clear と CSV 削除）が先に必要です。読み戻しの基準とリセット手順を手順書に記載しました |
| 2 | Agent の SQL ビュー要素 | **完了（サービスで確認）** | 公開の Data Agent 管理 API で、6つのビューが View・Available・選択済み、列が INFORMATION_SCHEMA と一致（`agent_donation_detail` の `DonationDataLayer` は未選択）、重複する `ot_*` テーブルは未選択であることを確認 |
| 3 | 時系列バインドと native Metrics | **一部完了・引き継ぎ（UI）** | `handoff-ontology` を承認済みのソースで記録。Eventhouse の時系列バインドは定義形式が公開されておらず、Generate Ontology にも API がないため UI 専用。設定値、331件 / 5,737,000円の確認、Business Rule のメタデータ（引き継ぎの記録後は Notebook02 が動かない仕様のため、Ontology の画面で編集。第5報で訂正）、Temp での Metrics を手順書に記載 |
| 4 | 任意の Power BI レポート | **完了** | 既存モデルに接続するレポートだけを配置し、定義を読み戻し。テナントで画像出力が無効なため PDF で表示を確認。DAX で Gold 94,900件 / 1,596,157,000円、高額 1,392件と一致。フォルダーは 22 Items |

### 対策

| 対策 | 実施内容 |
|---|---|
| **E** T10 の遮断 | 採点に「プラットフォーム遮断」の区分を追加（厳密な分母は変えず FAIL のまま、診断用の内訳だけを別に出す）。ガイド19章に教材の注記。サポートへの報告案。関連する3つの質問では遮断されず Agent が正しく拒否したため、遮断は「特定の上位個人」＋「年収・控除額」の組合せに限られます |
| **F** 回帰ゲート | 拡張14問（B01–B14）を公開の回帰スイートとして追加。期待値は同梱 CSV・TMDL・Notebook05・Ontology 契約から再計算し、調整時にライブソースで確かめた値と全問一致。`evaluate_native.py` が `regression` を凍結・事前登録・実行・報告できるようにしました |
| **G** 手順書 | 承認済みコミットでの段階実行、Notebook05 の plan hash（ヘルパー付き）、ビューと例の検証状態のサービス確認（ツール付き）、レポートのみの配置、Activator と時系列の引き継ぎ |

### 残件への候補（採用せず）

採用規則（標準10問2回の平均 ≥ 73.5、拡張の内容 PASS ≥ 13、事実 PASS ≥ 13）は、各候補の結果を見る前に記録しました。

| 構成 | 標準84（1回目／2回目） | 拡張 事実 / 内容 | 判定 |
|---|---:|---:|---|
| R6（採用中） | 74 ／ 73 | 14 / 13 | — |
| R7 3ソースの順序・重複の有無・回答前確認・KEEPFILTERS 対比 | 69 ／ 76 | 13 / 13 | 不採用（平均 72.5） |
| R8 R7＋突き合わせキーを先頭に・人気の値を必須に | 76 ／ 74 | 12 / 11（B11 は通信タイムアウトで不明） | 不採用（拡張の内容 11） |

R8 では T09 が2回とも 8/8 になり、標準の平均は 75.0 でした。一方で T07 の重複を含む総数の欠落、B08 の取得失敗、
B02 の KEEPFILTERS に触れない説明が出ました。規則どおり R6 に戻し、Draft・Published の 14 パーツすべてが
R6 と一致することを確認しています。R8 の指示差分は[こちら](r8-candidate-contracts.diff)にあり、採否はご判断ください。

**事前に固定した未公開の確認問題12問**（R7 の前に SHA-256 で固定し、当時採用中の R6 で1回だけ実行）は
**事実 9 / 12、内容 7 / 12** でした。失敗は、3ソースの複合質問で Ontology を使わない、重複の有無を断定する、
BLANK の理由に KEEPFILTERS を使わない、合算を断る際に対象の月ではなく全期間の件数を示す、
57,000円ちょうどの件数を「算出できない」とする、の5件です。前の3つは R7・R8 が対象とした分類と同じです。
著者が作成した問題で、独立した評価ではありません。

### 観測性とサービスの状態

- Fabric ノートブック内の SDK の run steps で実行内容を確認しました（Temp の一時ノートブックで実行し、使用後に削除）。
  R6 の標準 T09 は Kusto と LakehouseTables だけを実行し、Ontology は実行していません（第2報の推定を確認）。
- Example queries の検証状態: Lakehouse の SQL 例 17件はすべて Invalid（検証がエンドポイントに接続できない）、
  KQL 9件はすべて Valid。run steps では SQL 例も読み込まれますが、例の照合で返ったのは KQL だけでした。
  サポートへの報告案に含めています。

判定は固定期待値と回答本文を照合した AI 補助審査です。環境の ID・回答本文・未公開の確認問題は公開していません。

### English summary

All four procedural deviations of the 2026-10-07 deployment were addressed in priority
order. Two are complete: the Data Agent's six SQL views are verified through the public
management API, and the optional Power BI report is deployed and reconciled (22 items).
Two depend on native UI steps that cannot be automated here, so they are documented as
hand-offs: initializing the Activator action (plus an approved reset before any
re-delivery) and the Eventhouse time-series binding, Notebook02 and native Metrics
(`handoff-ontology` is recorded).

Countermeasures E, F and G are implemented: a strict-denominator-preserving
`platform_blocked` classification, a guide note and support drafts for T10; a public
regression suite B01–B14 whose expected values are recomputed from repository sources
and wired into `evaluate_native.py`; and runbook sections with helper tools.

Two residual-fix candidates were evaluated against an adoption rule recorded before
their results: R7 (69/76; extended 13/13) and R8 (76/74; extended 12/11 with one
transport timeout). Neither met the rule, so production was rolled back to R6 and
verified part-for-part. A new pre-registered 12-question holdout, run once on R6,
scored fact 9/12 and content 7/12; its failures repeat the residual categories.
SDK run steps confirmed that R6 answers T09 without executing the Ontology. All 17
Lakehouse SQL examples fail service validation while all 9 KQL examples pass; both
platform issues are drafted for product support. This is AI-assisted review of answer
text, not independent human acceptance.
