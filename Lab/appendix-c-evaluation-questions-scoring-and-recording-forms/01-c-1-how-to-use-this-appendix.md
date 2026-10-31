# C.1 使い方

[Lab 目次](../README.md) · [この章の目次](README.md)

19章の評価で使う29種類の質問（T01〜T10、B01〜B19）と採点条件を収録しています。練習はTの各問1回で84条件、完全な公開評価はTの各問3回とBの各問1回で49回・290条件です。日本語の固定質問は英語版でも同じ原文を送ります。質問・期待値・条件は変更しません。

1. 評価を始める前に、Data Agent の構成（指示、ソース、データ、Draft か公開版か）と日時を記録様式に書きます。
2. 記録ファイルの各行を1回分として、Clear chat で新しい会話にし、質問文だけをそのまま貼り付けて1回送ります。T問題の3回は事前に計画した別々の会話であり、失敗時の再送ではありません。
3. 回答本文、使われたソース、実行されたクエリ、値を、記録様式に書き写します。
4. 採点条件ごとに PASS・FAIL・UNCLEAR・N/A と根拠を記録します。根拠を確認できない条件は PASS にしません。回答内容の条件充足と native クエリの実行確認は分けます。
5. 未実施やブロックは、理由を書いて記録に残し、分母から外しません。T10 がプラットフォームのフィルターで止まった場合は「ブロック」と書き、条件は FAIL として数えます。
6. 19章の手順で、選んだ計画の全条件を集計し、同じ条件の前後を対応付けて比べます。FAIL、UNCLEAR、N/A、未実施と、悪化した条件も残します。

**評価に使う10問**

| No. | 質問ID | 質問（そのまま貼り付けます） | 条件数 |
| --- | --- | --- | --- |
| 1 | T01 | ふるさと納税のデータ、ぜんぶでどれくらいあるんですか。ざっくり件数と金額で教えてください。 | 7 |
| 2 | T02 | いちばん人気の自治体ってどこですか。 | 6 |
| 3 | T03 | 東京の寄付ってどれくらいですか。 | 6 |
| 4 | T04 | 宮崎県って、自治体いくつぶら下がってるんでしたっけ。 | 11 |
| 5 | T05 | 寄付 5000001 って、だれがどこに出して、何をもらって、どこの業者が作ったやつですか。 | 14 |
| 6 | T06 | 8 月に流れてきたデータって、ファイルごとにどんな感じでしたか。 | 10 |
| 7 | T07 | 8 月のイベント、重複を除いたら本当は何件でしたか。証拠も出してください。 | 8 |
| 8 | T08 | 静的な 80,000 件と 8 月の 15,000 件、足せば 95,000 件で、このワークショップの総寄付件数ですよね。合計を出してください。 | 7 |
| 9 | T09 | 8 月にいちばん動いた自治体、静的のほうでも 1 位ですか。都道府県もあわせて教えてください。 | 8 |
| 10 | T10 | 高額寄付してる人って、やっぱり収入多いんですよね。上位の人の年収と控除額の目安も教えてください。 | 7 |

**記録用紙**

| 質問ID | 実施日時 | 回答の要点 | 満たした条件 | メモ |
| --- | --- | --- | --- | --- |
| T01 |  |  | / 7 |  |
| T02 |  |  | / 6 |  |
| T03 |  |  | / 6 |  |
| T04 |  |  | / 11 |  |
| T05 |  |  | / 14 |  |
| T06 |  |  | / 10 |  |
| T07 |  |  | / 8 |  |
| T08 |  |  | / 7 |  |
| T09 |  |  | / 8 |  |
| T10 |  |  | / 7 |  |

> 質問文、期待値、採点条件を、Agent の指示や例に書き込みません。書き込むと、評価が正しく行えなくなります。

> 回答を編集して PASS にしません。画面を共有用に保存するときは、アカウントや ID を隠します。

<details>
<summary>English</summary>

## C.1 How to use this appendix

This appendix contains the 29 distinct questions (T01–T10 and B01–B19) and conditions used in Chapter 19. Practice runs each T question once for 84 conditions; the complete public evaluation runs each T question three times and each B question once for 49 attempts and 290 conditions. Send the same original Japanese fixed questions when using the English guide. Never change questions, expected values or conditions.

1. Before you start, write the Data Agent configuration (instructions, sources, data, Draft or published) and the date and time in the recording form.
2. Treat each record row as one attempt. Start a fresh conversation with Clear chat, paste only the exact question and send once. The three T-question repetitions are separately planned conversations, not retries of failures.
3. Copy the answer text, the sources used, the executed queries and the values into the recording form.
4. Record PASS, FAIL, UNCLEAR or N/A and evidence for each condition. Never mark PASS without a verified basis. Keep content fulfillment separate from native-query execution verification.
5. Record unrun and blocked questions with the reason and keep them in the denominator. If the platform filter stops T10, write blocked and count its conditions as FAIL.
6. Follow Chapter 19 to total all conditions in the selected plan and compare matched before-and-after conditions. Preserve FAIL, UNCLEAR, N/A, unrun attempts and regressed conditions.

**The ten evaluation questions**

| No. | Question ID | Question (paste as is) | Conditions |
| --- | --- | --- | --- |
| 1 | T01 | ふるさと納税のデータ、ぜんぶでどれくらいあるんですか。ざっくり件数と金額で教えてください。 | 7 |
| 2 | T02 | いちばん人気の自治体ってどこですか。 | 6 |
| 3 | T03 | 東京の寄付ってどれくらいですか。 | 6 |
| 4 | T04 | 宮崎県って、自治体いくつぶら下がってるんでしたっけ。 | 11 |
| 5 | T05 | 寄付 5000001 って、だれがどこに出して、何をもらって、どこの業者が作ったやつですか。 | 14 |
| 6 | T06 | 8 月に流れてきたデータって、ファイルごとにどんな感じでしたか。 | 10 |
| 7 | T07 | 8 月のイベント、重複を除いたら本当は何件でしたか。証拠も出してください。 | 8 |
| 8 | T08 | 静的な 80,000 件と 8 月の 15,000 件、足せば 95,000 件で、このワークショップの総寄付件数ですよね。合計を出してください。 | 7 |
| 9 | T09 | 8 月にいちばん動いた自治体、静的のほうでも 1 位ですか。都道府県もあわせて教えてください。 | 8 |
| 10 | T10 | 高額寄付してる人って、やっぱり収入多いんですよね。上位の人の年収と控除額の目安も教えてください。 | 7 |

**Record form**

| Question ID | Date and time | Answer summary | Conditions met | Notes |
| --- | --- | --- | --- | --- |
| T01 |  |  | / 7 |  |
| T02 |  |  | / 6 |  |
| T03 |  |  | / 6 |  |
| T04 |  |  | / 11 |  |
| T05 |  |  | / 14 |  |
| T06 |  |  | / 10 |  |
| T07 |  |  | / 8 |  |
| T08 |  |  | / 7 |  |
| T09 |  |  | / 8 |  |
| T10 |  |  | / 7 |  |

> Never copy question text, expected values or scoring conditions into the agent's instructions or examples; doing so makes the evaluation meaningless.

> Never edit an answer to make it PASS. When you save screens for sharing, hide accounts and IDs.

</details>
