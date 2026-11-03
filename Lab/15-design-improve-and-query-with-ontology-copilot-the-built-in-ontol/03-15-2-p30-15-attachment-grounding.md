# 15.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

4. B：Aが FAIL・未確認でも、その結果を残して未適用プレビューを閉じます。AIの回答ではなく実際の主 Ontology の定義を再取得し、基準の10 Entity・15 Relationship、既存の ID・型・関係の始点／終点と向き・キー・バインド・共有参照・継承が不変であることを照合します。基準が不正・取得不能・変更済みの場合、または Plan・書き込みなしを確認できない場合は演習全体を停止します。不変と安全を確認できた場合だけ、ページを更新して新しい会話を始めます（前の会話は終了します）。Plan を選択・再確認し、business-requirements.txt、data-dictionary.txt、domain-model.png、revision-requirements.txt を添付してAと同じ依頼をそのまま送ります。適用・保存は行いません。
5. B の回答で、ファイル名が示され、資料から分かること（StaticSeed、品質処理した Gold、登録と発送の区別など）と、実際の Ontology の事実とが分けて書かれているかを確認します。回答の最後で、検証の結果（エラーと警告）と Preview ontology ボタンも確認します。

![PDF ビューア画面には `business-requirements.pdf` と表示されていますが、現行 ZIP の添付は `attachments/business-requirements.txt` です。回答例は既存 Entity の列挙が主 Ontology と一致しません。](../assets/p30-15-attachment-grounding.png)

添付回答の PDF ビューア画面例です。図には `business-requirements.pdf`、現行 ZIP には `attachments/business-requirements.txt` が表示され、演習では ZIP 内の TXT を選びます。日本語の回答は StaticSeed（静的データ）、RealtimeIncrement（品質処理済み増分）、Gold（Notebook 05 の品質処理後）を区別しますが、既存 Entity に AdministrativeArea と Municipality を挙げています。「既存項目を変更しない」という提案だけでは主 Ontology の保持を証明しません。実定義が10 Entity・15 Relationship と一致するかを照合し、不一致なら停止してください。SupplierProvidesGift はカタログ登録であり、実際の発送・履行の実績を示しません。

<details>
<summary>English</summary>

## 15.2 Steps

4. B: Even if A is FAIL or unverified, retain that result and close its unapplied preview. Re-read the authoritative actual main ontology definition, not an AI assertion, and compare the ten-entity/fifteen-relationship baseline and all existing IDs, types, relationship endpoints/directions, keys, bindings, shared references and inheritance: all must be unchanged. Stop the whole exercise if the actual baseline is wrong, unavailable or changed, or Plan/no-write safety cannot be confirmed. Only after confirming unchanged baseline and safety, refresh to a new conversation (ending the previous one), select and recheck Plan, attach business-requirements.txt, data-dictionary.txt, domain-model.png and revision-requirements.txt, and send exactly the same request as in A. Do not apply or save.
5. In B's answer, check that the file names are shown and that what the documents say (StaticSeed, quality-processed Gold, registration versus shipment and so on) is written separately from the facts of the actual ontology. At the end of the answer, also check the validation results (errors and warnings) and the Preview ontology button.

![The PDF-viewer screen shows `business-requirements.pdf`; the current ZIP supplies `attachments/business-requirements.txt`. The answer example’s existing-entity list does not match the main ontology.](../assets/p30-15-attachment-grounding.png)

PDF-viewer example of an answer with an attachment. The figure shows `business-requirements.pdf`, while the current ZIP contains `attachments/business-requirements.txt`; select the supplied TXT for the exercise. The Japanese answer distinguishes static donations, Eventhouse observations and Notebook 05 quality-processed Gold, including StaticSeed as static data and RealtimeIncrement as quality-accepted increments. However, it lists AdministrativeArea and Municipality as existing entities and claims that existing entities, keys and bindings are unchanged. This does not establish preservation of the main ontology. Verify the claim against the actual ten-entity, fifteen-relationship definition, and stop on a mismatch. SupplierProvidesGift is catalog registration rather than fulfillment; the answer does not establish shipment.

</details>
