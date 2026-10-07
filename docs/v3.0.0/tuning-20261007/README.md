# 標準ワークショップ契約の復元 — 2026-10-07

> 追記: 同日の第3報（手順の逸脱の完了、対策 E・F・G、残件への候補 R7・R8 と新しい holdout）は
> [followup-20261007](../followup-20261007/README.md) にあります。拡張14問は、その後
> 公開の回帰スイート（B01–B14）として期待値とともに公開しました。

**新規デプロイ直後の正式Agentは、保護された標準10問・84条件で36/84・34/84でした。
原因を特定して回答契約を復元し、6構成を評価した結果、採用構成は74/84・73/84
（T10のnative遮断により上限77）です。事前登録holdout12問は11 PASS／1 FAILでした。
AI回答の0 FAIL・全機能合格・独立した人間の受入ではありません。**

[Word追補](furusato-data-agent-tuning-20261007.docx) ·
[日英HTML追補](furusato-data-agent-tuning-20261007.html) ·
[全構成の件数・判定・hash](result-20261007.json) ·
[実装と適用手順](../../../workshop/v3.0.0-preview/data-agent/candidates/standard-contract-restoration/README.md) ·
[SHA-256](SHA256SUMS.txt) · [文書検証記録](artifact-validation.json)

## 主な原因と修正

| 初回の原因 | 修正 | 最終構成での状態 |
|---|---|---|
| 修正チェーン（time-layer-isolationまで）が元の統合指示を置き換え、標準10問の回答契約が消えていた | `standard-contract-restoration`を4つ目のAgent compilerとして追加し、最優先の全体契約と4ソースの契約を先頭に置く | T01–T07: 2回とも全条件PASS（T02・T05の1回ずつの欠落を除く） |
| 年なしの「8月」を静的seedの2025年と解釈し、2026年8月の生観測を「0件」「存在しない」と回答 | 年なしの8月・流入・観測・イベント・ファイル・増分は2026年8月UTC。2025は明記時のみ。0件・矛盾時は全体期間を確認 | T06・T07・B01・B03・B04で正答 |
| 東京などの県名を受入だけで回答、人気を金額だけで判定 | 受入/在住の両方、人気は件数と金額・ID・全国スコープ | T02・T03・B10で正答 |
| 宮崎県の自治体数をLakehouseで数え、手で数えて27と誤答 | OntologyでMunicipalityInPrefectureを逆にたどるCOUNTと固定3行 | T04: 最終構成で2回とも11/11 |
| 静的80,000件と観測15,000件の合算依頼で合計を出す・再掲する | 固定の回答形式で拒否し、利用者の合計値を書かない。`Recipient schema`行を出力 | T08: R5以降の4回すべて7/7 |
| 倍率・増減率の取り違え、CatalogGiftCount・DAXの誤説明 | 差・倍率・増減率の3行、列とKEEPFILTERSメジャーの実定義に限定 | B07・B09は正答。B02は最終構成で1回誤り |
| 生成クエリの脆弱性（英語名で照会、指標の組合せの取り違え） | Ontologyは接尾辞付き日本語名で照合し再試行、KQLは1回のsummarizeから両指標 | T04・T09の値は最終構成で正答 |

ソースID・選択・Published部分・データ・Power BIメジャーは変更していません。
新しいSQL/KQL例6件を含む全26例は実ソースで実行し、行を返すことを確認しました。

## 全構成の結果

質問・期待値・84条件は変更していません。標準10問は各構成2回、拡張14問は1回です。
開発34回答は標準20回答と拡張14回答の合計です。P / F / U = PASS / FAIL / UNKNOWN。

| 構成 | 標準84条件（1回目／2回目） | 開発34回答 事実 P / F / U | 内容 P / F / U |
|---|---:|---:|---:|
| R1 デプロイ直後 | 36 ／ 34 | 20 / 14 / 0 | 10 / 24 / 0 |
| R2 標準契約の復元 | 67 ／ 65 | 29 / 5 / 0 | 20 / 14 / 0 |
| R3 根拠行・数値と説明の忠実性 | 72 ／ 68 | 30 / 4 / 0 | 23 / 11 / 0 |
| R4 固定出力行・3ソース手順 | 73 ／ 73 | 32 / 2 / 0 | 27 / 7 / 0 |
| R5 合算拒否・比較の回答形式 | 75 ／ 65 | 29 / 5 / 0 | 27 / 7 / 0 |
| **R6 名前照合・単一集計（採用）** | **74 ／ 73** | **32 / 2 / 0** | **27 / 7 / 0** |

R5では1回目が最高の75でしたが、2回目にOntologyの英語名照会（0件）と観測値の組合せ誤りが出ました。
これらのFAILを削除せず、汎用的な対策を加えたR6を評価しています。
採用規則（R6の平均73.0以上かつ拡張の内容PASS12以上、満たさなければR4–R6の最良を再適用）は
R6の結果を見る前に記録しました。3.0.0 release時の記録は76/84（T10 0/7）です。

**事前登録holdout 12問**（R1の失敗分類から作成し、構成変更前に固定。採用構成で1回だけ実行）は
**事実11 / 1 / 0、内容11 / 1 / 0**です。著者が作成した問題であり、独立した評価ではありません。
送信は全体で221回（業務回答209、T10のnative遮断12、通信エラー・UNKNOWN 0）です。
R3でB05のモデル照会が失敗した後の診断再送3回（3回とも正答）とR1の診断2問は分母に含めていません。

## 残る事項

- **T10**（高額寄附者の年収・控除額の推定）は全構成でnativeのコンテンツフィルターに遮断されます。
  指示では回避せず、FAILとして報告します。製品サポートへのエスカレーションを推奨します。
- **T09**は値・順位は正しいものの、所属県をOntologyでたどらずLakehouseの県列を使うため、
  3ソース表示と突き合わせキーの条件を満たしません（最終構成は2回とも6/8）。
- 最終構成でも再現しない欠落があります。T02のMunicipalityId欠落、T05の寄附金額欠落、
  B02でKEEPFILTERSの有無に関わらず空になると一般化（各1回）。
- **holdout H09**（特定CSV内の重複の有無）で、バケットキーの一意性から「重複なし」と断定しました。
  正しくはEventIDがないため判定不能です。重複除外の契約を「重複の有無」の質問へ広げる対策を
  提案しますが、未適用・未検証です。
- 評価は公開MCPで回答文だけを観測しました。内部SQL/KQL/GQL/DAX・実行ソース・backend会話IDは
  **UNOBSERVABLE**です。回答中のソース表記は実行の証明ではありません。

## 適用範囲と保存したもの

利用者の指示により、2026-10-07の正式配置（指定フォルダの正式Agent1件）へ直接適用しました。
各構成の適用前に直前の公開定義と一致することを読み戻しで確認し、公開後にPublishedとDraftの一致を
確認しています。ネイティブUIのExample queries画面での検証状態はAPI経路のため確認していません。

判定は固定期待値と実回答を照合した**AI補助審査**で、独立した人間のsign-offはありません。
元3.0.0のrelease tag・配布物、2026-10-02/03/04の記録、過去のWord・HTMLは変更していません。
拡張14問とholdoutの質問・期待値・回答本文・private基準は公開していません。

WordとHTMLは同じ公開JSONから
[文書builder](../../../tools/docs/README.md#native-data-agent-tuning-addendum)で生成しました。

## English summary

A clean deployment of the time-layer-isolation formal Agent scored **36/84 and 34/84**
on the protected standard ten/84: the corrected profile chain had lost the standard
answer contracts, and a year-less “August” was read as the static 2025 label. The new
`standard-contract-restoration` compiler restores them without changing sources,
selections, data or measures.

All six configurations remain visible. The adopted round 6 returned **74/84 and 73/84**
(ceiling 77 because T10 is blocked by the native content filter and is never bypassed);
the 34-answer development cohort moved from content 10/24 to 27/7. The pre-registered,
author-written holdout ran once on the adopted configuration: **11 PASS /1 FAIL /0 UNKNOWN**.
Residuals: T10 platform block, T09 Ontology provenance, single nonreproducible omissions
and the H09 duplicate-existence answer. This is AI-assisted review of answer text only,
not independent human acceptance, GA or a general accuracy guarantee.
