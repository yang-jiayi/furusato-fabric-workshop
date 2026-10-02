# 3.0.0 検証スナップショット — 2026-10-02

[Word](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) ·
[日英HTML](guide/furusato-workshop-v3-0-0-complete.html) ·
[公開評価データ](evaluation100.json) ·
[配布物・ZIP](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/tag/v3.0.0-validation-20261002) ·
[SHA-256](SHA256SUMS.txt) ·
[元の3.0.0](../README.md)

これは再配置と回答品質評価の実測を追加した**日付付きの教材スナップショット**です。
元の`v3.0.0`タグ、Word・HTML・ZIPと、元10問・84条件の76 PASS／8 FAILは変更しません。
今回の100枠と、過去の限定診断14／0・heldout13／0も合算しません。

## 再配置と動作確認

承認された旧フォルダ内の52 Itemを、管理対象の子Itemと回復可能Itemを含めて削除し、
その後に公開3.0.0を新しいフォルダへ配置しました。対象外Itemとフォルダのルートは保持しました。
新しいNotebook01・05はそれぞれ1回だけ実行し、静的・品質処理済みデータを別々に確認しました。

| 確認対象 | 実測 |
|---|---:|
| 静的seed | 80,000件／1,344,099,000円 |
| 手動Pipeline Copy | 3回、各5,000行、すべてCompleted |
| Eventhouse生観測 | 15,000件／253,886,000円、入力の重複を保持 |
| 受入済み増分 | 14,900件／252,058,000円 |
| Gold | 94,900件／1,596,157,000円 |

自動イベント起動は成功を確認できず、**自動0・手動3**として記録しています。
再送や常時稼働設定で実績を作り替えていません。Pipelineの一時的な入力既定値は元へ戻し、
Activatorは停止しています。Eventhouseの照会確認は、常時稼働やcapacity変更を意味しません。
GoldはNotebook05が独立した`Files/increment`入力を処理したもので、Eventhouseを入力にしていません。

主generation2 Ontologyと主Agentを保持したまま、別のSTATIC generation1互換経路を隔離配置しました。
その経路の10エンティティ表示と照会を確認しましたが、generation2 consumer制約を修復したとは扱いません。
後述の評価はこの明示的な互換候補を対象とし、**主Agentへは昇格していません**。

## 固定100枠による回答評価

ソースから期待値を作った日本語口語100問を、開発80問とheldout20問に分けて固定しました。
同じ開発80問で基線と1回の意味ある指示変更を比較し、変更後候補を凍結してheldoutへ進みました。
成功回答だけを選び直したり、基線の回答を改善後の不足へ流用したりはしていません。

| 評価対象 | 分母 | 事実の正確性 P / F / U / N/A | 固定条件を含む回答内容 P / F / U |
|---|---:|---:|---:|
| 基線・開発 | 80 | 46 /29 /5 /0 | 21 /58 /1 |
| 指示変更後・開発 | 80 | 59 /15 /5 /1 | 28 /49 /3 |
| 凍結候補・heldout | 20 | 8 /4 /7 /1 | 5 /8 /7 |
| 最終候補・合算 | 100 | 67 /19 /12 /2 | 33 /57 /10 |

P=PASS、F=FAIL、U=UNKNOWNです。事実の正確性と、必要なID・時刻・関係・フィルター説明などを含む
固定条件の充足を分けています。正しい主要値でも必要な補足項目が欠けると内容判定はFAILになり得ます。
逆に、正しい注意書きがあっても、実際の値・母数・関係が誤っていれば合格にはしません。
これは独立した人間のsign-offではなく、固定期待値と実回答の引用箇所を照合した**AI補助審査**です。

基線に対し、開発80問の正確な事実回答は13問、内容PASSは7問増えました。
seed名の年を暦年フィルターと取り違える問題や、「受入額」と「受入増分」の区別などに改善が見られました。
一方、業者への寄附売上の誤帰属、JOIN後の寄付二重計上、過年度メジャー、
フィルターやキーの取り違え、必要項目の欠落も残っています。**0 FAIL・本番品質合格ではありません。**

N06の固定期待値には、寄付集計が0となる自治体・カテゴリの論理的な組合せキーが含まれます。
独立したソース確認では、その組合せの事前計算済み指標行は存在しませんでした。
論理キーや集計0を、格納された指標行の存在証明に読み替えません。
元の期待値や封印済み判定は書き換えず、この評価上の注意点も保持しています。

## 通信停止と試行の扱い

heldoutの初回実行は2回答の後、HTTP500によって1問が送信結果不明となりました。
この問は再送していません。その後、元の予約済み・未送信17枠だけに限定した
**事後の明示的な実行手順変更**を1回適用しました。これは事前登録済みの再開機構ではなく、
元の「再開なし」という方針を変更したものです。

この限定続行では11回答を取得した後、別の1問がnative RPCエラーとなり、
宣言した停止条件どおり終了しました。残り5問は未送信です。
元のplan・予約・停止batch・応答・エラーを保存し、送信済み／不明の問は再試行していません。
source・transport・候補・質問・rubricを変更せず、heldoutを改善に使っていません。

| 最終候補100枠の取得状態 | 件数 |
|---|---:|
| 業務回答を取得 | 93 |
| native APIエラー応答 | 1 |
| 送信結果不明 | 1 |
| 停止後の未送信 | 5 |
| 合計 | 100 |

**95件の送信intent、93件の業務回答**であり、100問すべてを実行・成功したという主張ではありません。
エラー、不明、未送信を正答・業務上の拒否・分母除外へ変換していません。
元の停止batch hashと追加の照合記録hashは[公開データ](evaluation100.json)に固定しています。

レビュー方式の事前の意図はoperator receiptとfilesystemで補強できますが、独立した事前登録証明ではありません。
正式なreview policy／code bindingは基線capture開始後に確定しました。この差異を隠さず、
hashはadmission時に計算したものとして扱います。実回答の引用一致は、意味的正解を自動的に保証しません。

公開MCPで確認できるのは回答だけです。回答文から内部SQL／KQL／GQL／DAXの実行、
実行回数、返却rowset、別backend会話の成立を推測していません。これらは**UNOBSERVABLE**です。

## 再現可能な変更と配布物

比較候補の最終定義差分は、draft／publishedの`aiInstructions`の2フィールドだけでした。
source binding・選択列・データ・輸送方式・安全設定は不変です。
[検証した指示本文](agent-instructions.experimental.txt)と[profile metadata](agent-profile.json)を公開します。
これは学習用の実験profileであり、未解決の退行があるため既定profileや主Agentへの自動適用はしません。
57,000円の厳密な高額判定は元Notebook05の既存ビジネスルールであり、回答値の埋込みではありません。

Word・日英HTML・日付付きZIPは同じ[公開評価JSON](evaluation100.json)を入力に生成しました。
修正後の文書ペアは203確認項目、パッケージは170入力再確認を通過しました。
Wordは246ページで、Word・日英HTML印刷に空白ページはありません。
これらは配布物の検証であり、AI回答やFabric機能の合格件数には加算しません。
画面は元の審査済み48配置／46画像を保持し、今回の回答品質評価を新しい画面取得の成功証拠とは混同しません。
生成・再検証方法と厳格な公開schemaは[文書ビルド手順](../../../tools/docs/README.md)を参照してください。

## English summary

This dated validation snapshot preserves the original3.0.0 release and its76/8 original84-condition result.
The new deployment separately verified static, raw and accepted-Gold data; all three successful Copies were
**manual**, not automatic event deliveries. The primary generation2/main-Agent configuration was preserved;
the tested STATIC compatibility candidate was not promoted.

Development factual passes increased46→59/80 and complete-content passes21→28/80, but regressions remain.
Final100-slot accounting is93 captured business answers,1 native-error reply,1 uncertain submission and5 unsent
slots. Content is33 PASS/57 FAIL/10 UNKNOWN. This is not100 successful executions, zero-FAIL, product GA,
production acceptance or independent human review.

A disclosed, non-preregistered post-stop amendment submitted only original never-submitted slots, once each.
It retained the first HTTP500 uncertainty, stopped on the next native error and never retried either failed case.
The fixed final candidate, rubric, original evidence and all denominators remain intact. Internal query execution
and backend conversation identity remain UNOBSERVABLE.
