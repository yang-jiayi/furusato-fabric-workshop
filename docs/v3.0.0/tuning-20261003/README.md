# Data Agent 再チューニング — 2026-10-03

**同じ開発20問では0 FAILを確認しましたが、拡大した32枠の最新結果は29 PASS／2 FAIL／1 UNKNOWNです。全面的な0 FAIL・品質受入は未達です。**

[Word追補](furusato-data-agent-tuning-20261003.docx) ·
[日英HTML追補](furusato-data-agent-tuning-20261003.html) ·
[件数・ケース判定・hash](result-20261003b.json) ·
[実装・適用境界](../../../workshop/v3.0.0-preview/data-agent/candidates/complete-contract/README.md) ·
[SHA-256](SHA256SUMS.txt) · [文書検証記録](artifact-validation.json)

これは別日付の追補です。元の3.0.0、2026-10-02のWord・HTML、元100枠の
33 PASS／57 FAIL／10 UNKNOWNを上書きしていません。
主Agentと元の比較候補は保持し、変更は隔離した比較用Agentへ反映しています。

## 同じ20問での比較

質問・ソースから作った期待値・必須条件は変更せず、意味のある構成変更ごとに各問1回だけ送信しました。
P=PASS、F=FAIL、U=UNKNOWN。表の各行はその構成の全20回答で、正答の選び集めではありません。

| 構成 | 事実 P / F / U | 必須条件を含む内容 P / F / U |
|---|---:|---:|
| 直前のビュー構成（Round3） | 15 /4 /1 | 12 /7 /1 |
| ソース契約と列説明（Round4） | 10 /10 /0 | 9 /11 /0 |
| 表中心・宣言辞書（Round5） | 19 /1 /0 | 15 /5 /0 |
| 日本語の必須出力・取得先整理（Round6） | 17 /2 /1 | 17 /2 /1 |
| 宣言スキーマを照会可能にした構成（Round7） | **20 /0 /0** | **20 /0 /0** |

途中の退行も保持しています。主要な値が正しくても、必要なID・名前・所在地・時刻・関係が欠ける場合、
または追加説明がソースの意味と矛盾する場合は内容PASSにしません。
これは既知の失敗に焦点を当てた開発回帰であり、一般の質問に対する正答率の推定ではありません。

## 追加質問と最新32枠

Round7を変更せず、別の人物・業者・支払方法・時間帯・メジャー条件を使う未使用12問を各1回確認しました。
初回結果は、事実 **10 P /2 F /0 U**、内容 **9 P /3 F /0 U** でした。
電子決済を「データなし」とする誤り、短い業者一覧での寄附者情報の省略、
高額フラグを「閾値以上」と説明する誤りが見つかりました。

これらを改善に使ったため、その12問は以後**既知の開発問題**です。
元20問と合わせた全32枠を新しい同一構成（Round8）で再評価しました。
過去の成功回答は流用せず、質問・期待値・必須条件を維持しています。

| 最新構成の内訳 | 枠数 | 事実・内容 P / F / U |
|---|---:|---:|
| 元の開発20問 | 20 | 18 /1 /1 |
| 追加12問（この段階では開発用） | 12 | 11 /1 /0 |
| **同一構成・固定32枠** | **32** | **29 /2 /1** |

最初の追加試験で見つかった3問題は最新構成で改善を確認しました。
一方、別の退行として次の2件が残りました。

| 判定 | 残る問題 |
|---|---|
| FAIL | UTCと明示された1時間集計を、JSTの日付に読み替えた期間で回答 |
| FAIL | Goldメジャーの`StaticSeed`条件を、静的SQLの`StaticSyntheticSnapshot`と混同して説明 |
| UNKNOWN | 1問がHTTP500となり、正常な業務回答を取得できず送信結果不明 |

最後の構成に対する新たな独立未使用セットは実施していません。
少数の既知問題が一度全問PASSになったことを、将来の任意質問の無誤答保証とは扱いません。

## 実装した改善

- 4ソースの役割、snapshot名と暦年、居住県と受入県、必須列、全件一覧、UTC/JSTを整理。
- 既存4ビューに加えて、実Ontologyの15関係を照合した`agent_relationship_dictionary`と、
  格納キー・名称・件数・金額・両側の宣言方向を揃えた`agent_prefecture_category_metric`を追加。
- 全662指標行とそのキー・値、80,000寄附／1,344,099,000円を保持し、実SQL定義と全行差分を確認。
- 比較用Agentで実サービスが検出した2つのview型・ID・列型を選択し、重複する元指標テーブルを選択解除。
- 実データのlayer／支払方法の値、空結果の確認、短い一覧でも必要な本人情報、
  Notebook05の厳密な`DonationAmountYen > 57000`・同額除外を明示。
- 最終のSQL15例・KQL5例を直接実行し、ネイティブ画面の検証エラー・処理待ちがないことを確認して公開。

ソースの行・元4ビュー・Ontology定義・Power BIメジャー・Notebook01/05の実行回数・権限は変更していません。
関係辞書は検証済みスキーマのSQLビューであり、実グラフの実行証明やgeneration2 connectorの修復ではありません。
ソースOntologyが変わった場合は明示的な再照合が必要です。

## 通信停止と続行

32枠の初回実行は11業務回答の後、1問のHTTP500（native内部エラー）で送信結果不明となりました。
次の問は送信前の定義取得でタイムアウトし、停止条件に従って終了しました。
**不明の1問は再送していません。RequestIdはMCPの回収用task IDではありません。**

読み取り専用の定義確認が再び成功し、構成が不変であることを確認した後、
元の**未送信20枠だけ**を各1回処理する、事後の明示的な手順変更を1回適用しました。
これは事前登録された再開機構ではありません。追加のサービス障害があれば即停止する条件で、
20業務回答を取得しました。
元のplan、予約、停止batch、失敗、結果不明とレビューは保持し、同じ構成の元32枠だけを照合しています。

| 最新32枠の取得状態 | 件数 |
|---|---:|
| 業務回答を取得・審査 | 31 |
| HTTP500・送信結果不明 | 1 |
| 同一構成の同一問を再送 | 0 |
| 元の枠数 | 32 |

今回の追加チューニング全体では、5つの構成と追加確認で**124送信intent／123業務回答**です。
これを124 PASSや124問の独立評価としては扱いません。

## 判定・証拠・採用境界

審査は固定期待値と実回答の引用、必要に応じた独立ソース照合による**AI補助審査**です。
独立した人間のsign-offはありません。内部SQL/KQL/GQL/DAX、内部rowset、内部会話IDは
**UNOBSERVABLE**です。新しいHTTPクライアントだけでは内部会話の新規性を証明しません。

追加質問の高額フラグでは、57,000円・同額除外と元Notebookのhashは実行前に固定されていましたが、
補足provenanceの参照名が1つ欠けていました。実行後に同じsource hashへの参照を追記し、
質問・期待値・基準・実回答・初回FAILを変更していません。この補足は事前登録済みとは主張しません。

最終構成は実験候補のままで、**主Agent未昇格・品質未受入**です。
自由生成される期間条件や最終説明を、公開のanswer-only APIだけで強制検査できるとは主張しません。
さらに強い保証には、生成クエリと最終出力を機械的に検査する別の実行・表示層が必要ですが、
今回それをネイティブAgentの代用品として導入したわけではありません。

WordとHTMLは同じ公開JSONから生成しています。
構成テスト・SQL検証・文書検証の成功はAI回答のPASSに加算しません。
生成方法は[文書builder](../../../tools/docs/README.md#native-data-agent-tuning-addendum)を参照してください。

## English summary

The same20 known development questions reached20 PASS/0 FAIL/0 UNKNOWN on Round7.
An unchanged-candidate check with12 previously unused variants then returned9 PASS/3 FAIL.
After those failures informed further tuning, all32 became **known development cases**, not an independent holdout.

The latest32-slot result is **29 PASS/2 FAIL/1 UNKNOWN**. The three initially discovered issues were repaired,
but an explicit-UTC interpretation and a cross-layer measure explanation regressed. A single HTTP500 outcome
remains unresolved and was not retried. A disclosed, non-preregistered continuation submitted only original
never-submitted slots; no answer was borrowed from another configuration.

The original studies/releases, main Agent, data, Ontology and source-owned measures are preserved.
This is not zero-failure quality acceptance, production promotion, general-population accuracy or a new release.
