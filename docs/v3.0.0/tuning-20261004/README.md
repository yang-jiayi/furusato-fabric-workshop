# UTC・データ層の混同修正 — 2026-10-04

**指定された2件のFAILを修正し、元の失敗2問＋対照8問の同一構成で
10 PASS／0 FAIL／0 UNKNOWNを確認しました。これは既知10問の限定回帰であり、
元32枠・100枠全体の再評価、独立未使用評価、主Agentへの昇格ではありません。**

[Word追補](furusato-data-agent-tuning-20261004.docx) ·
[日英HTML追補](furusato-data-agent-tuning-20261004.html) ·
[全構成の件数・ケース判定・hash](result-20261004.json) ·
[実装と適用手順](../../../workshop/v3.0.0-preview/data-agent/candidates/time-layer-isolation/README.md) ·
[SHA-256](SHA256SUMS.txt) · [文書検証記録](artifact-validation.json)

## 修正した2項目

| 元の問題 | 修正 | 最終の元質問 |
|---|---|---|
| UTCと明示された日付をJST日付へ読み替える | 対象日を絞る`FilterTimezone`と表示時刻の`DisplayTimezone`を分離。同じ日付のUTC/JST例を対にし、UTCの検索開始・終了を明示 | PASS |
| Goldメジャーの`StaticSeed`条件を静的SQLの由来タグと混同する | 比較用Agentで不要なSQL由来タグ列を選択解除し、指示・説明からその値を除去。Goldの実メジャーと同じモデル列の`StaticSeed`／`RealtimeIncrement`に限定して説明 | PASS |

Goldについては、外側フィルターを適用した**実メジャーの戻り値を先に取得してから説明する**
契約も追加しました。`KEEPFILTERS`は同じ列の外側条件と内側条件の交差であり、
互いに排他的な値のときは空集合です。モデル全体に両方のデータが存在することを理由に、
空集合の結果を非空と説明してはいけません。実際のメジャー定義やデータは変更していません。

## 同じ10問での経過

質問・ソース由来の期待値・必須条件はすべて変更していません。
P=PASS、F=FAIL、U=UNKNOWN。各行はその構成の全10回答です。

| 構成 | 事実 P / F / U | 必須条件を含む内容 P / F / U |
|---|---:|---:|
| 前回の同じ10問 | 8 /2 /0 | 8 /2 /0 |
| UTC/JSTとソース値の分離 | 10 /0 /0 | 9 /1 /0 |
| 検索境界と実観測期間の分離 | 8 /2 /0 | 8 /2 /0 |
| **実メジャー結果・受入自治体の集計単位を明確化** | **10 /0 /0** | **10 /0 /0** |

初回は元の2問がPASSになりましたが、JST対照問で実際の観測開始・終了を省く退行がありました。
次の構成ではそれを直した一方、正しいメジャー定義と矛盾する結論、
同じ受入自治体を寄附者の居住県別に分割して順位付けする回答が発生しました。
これらのFAILは削除せず、原因に対応する指示を追加して全10問を再評価しています。
検索窓と実観測時刻を分け、ランキングは受入自治体IDごとに1行としました。

最終構成では、UTCの全24時間の件数・金額・実観測時刻、2つのJST対照日、
逆側のモデルフィルター、Gold全体、前年同期間、2つの支払方法別ランキング、
高額フラグの厳密な不等号を確認しました。期間・名前・ID・順位・値の必要な条件を省いて
PASSにしていません。

今回の3構成は**30送信／30業務回答**です。同じ構成・同じ問の再送は0回です。
過去の正答を選び集めた10 PASSではありません。

## 適用範囲と保存したもの

変更先は隔離した比較用Data Agentだけです。主Agentと前の比較候補は変更していません。
実験候補は最終構成を公開済みで、公開定義の読み戻しを行っています。
SQL15例・KQL6例のネイティブ検証にエラー・処理待ちはありません。
この確認は、回答時に内部でどの例を参照したかを証明するものではありません。

選択解除した列は`dbo.agent_donation_detail.DonationDataLayer`だけです。
物理列・元データ・既存業務列・ソースID・Eventhouseオブジェクト・Ontology定義・
Power BIメジャー・権限・Notebook実行回数は変更していません。
この列は本比較レーンの業務質問には不要ですが、由来タグそのものを照会する用途まで
無条件に対応したとは扱いません。

前回のHTTP500で送信結果不明となった**F30-N10は対象外で、再送していません**。
[前回32枠の29 PASS／2 FAIL／1 UNKNOWN](../tuning-20261003/README.md)、
元100枠の33 PASS／57 FAIL／10 UNKNOWN、元3.0.0と過去のWord・HTML・release tagは
上書きせず保持しています。今回の10問だけで、それらの分母やUNKNOWNを置き換えません。

判定は固定期待値と実回答を照合した**AI補助審査**です。
独立した人間のsign-offはありません。内部SQL/KQL/DAX/GQL、内部rowset、
backend会話IDは**UNOBSERVABLE**です。ソースへの別の読み取り専用照会、
引用一致、構成テスト、文書検証の成功をAI回答のPASSとして加算していません。
最終構成に対する新たな独立未使用セットは未実施で、任意の将来質問の無誤答を保証しません。

WordとHTMLは同じ公開JSONから生成しました。
[文書builder](../../../tools/docs/README.md#native-data-agent-tuning-addendum)と
[適用用compiler](../../../tools/data-agent/time_layer_isolation.py)を公開しています。

## English summary

Both requested regressions are repaired on the published isolated native Agent.
The same two original failures plus eight unchanged contrasts returned
**10 PASS /0 FAIL /0 UNKNOWN** for factual and complete-content judgments.

Filter and display timezones are separate. The unused static-SQL provenance tag
is excluded from this Agent's context, while the actual model source values and
measure definitions are preserved. Explanations must agree with model results
under the requested outer filter. Actual observation spans are distinct from
query windows, and recipient rankings contain one canonical municipality per row.

All three measured configurations remain visible: content9/1, then8/2, then10/0.
There were30 submissions/30 business replies, with no same-configuration replay
or pooling of prior answers. The historical uncertain request was not retried.
This is a focused **known** regression, not a full32/100 reevaluation, independent
holdout, human acceptance, general accuracy guarantee or main-Agent promotion.
