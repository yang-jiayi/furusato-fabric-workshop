# 15.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

4. B：Aが FAIL・未確認でも、その結果を残して未適用プレビューを閉じます。AIの回答ではなく実際の主 Ontology の定義を再取得し、基準の10 Entity・15 Relationship、既存の ID・型・関係の始点／終点と向き・キー・バインド・共有参照・継承が不変であることを照合します。基準が不正・取得不能・変更済みの場合、または Plan・書き込みなしを確認できない場合は演習全体を停止します。不変と安全を確認できた場合だけ、ページを更新して新しい会話を始めます（前の会話は終了します）。Plan を選択・再確認し、business-requirements.txt、data-dictionary.txt、domain-model.png、revision-requirements.txt を添付してAと同じ依頼をそのまま送ります。適用・保存は行いません。
5. B の回答で、ファイル名が示され、資料から分かること（StaticSeed、品質処理した Gold、登録と発送の区別など）と、実際の Ontology の事実とが分けて書かれているかを確認します。回答の最後で、検証の結果（エラーと警告）と Preview ontology ボタンも確認します。

![参考画面には business-requirements.pdf と表示されていますが、現在の配布ファイルは business-requirements.txt です。ZIP の attachments から .txt を選びます。不一致の回答例は、4資料名、層の区別、不足点、DonationQualityScope の追加案を示しますが、既存 Entity に AdministrativeArea を挙げ、既存項目の保持は未確認です。](../assets/p30-15-attachment-grounding.png)

添付あり（B）の回答の参考例。画面には business-requirements.pdf と表示されていますが、現在の配布物は attachments/business-requirements.txt です。添付操作では ZIP 内の .txt を選びます。回答は4つの資料から層の違いを説明していますが、既存 Entity として AdministrativeArea と Municipality を挙げており、この章の主 Ontology の定義を正しく保持した証拠ではありません。資料の読み取りと定義の正しさは別に確認し、10 Entity・15 Relationship と一致しない回答は不一致として停止します。

<details>
<summary>English</summary>

## 15.2 Steps

4. B: Even if A is FAIL or unverified, retain that result and close its unapplied preview. Re-read the authoritative actual main ontology definition, not an AI assertion, and compare the ten-entity/fifteen-relationship baseline and all existing IDs, types, relationship endpoints/directions, keys, bindings, shared references and inheritance: all must be unchanged. Stop the whole exercise if the actual baseline is wrong, unavailable or changed, or Plan/no-write safety cannot be confirmed. Only after confirming unchanged baseline and safety, refresh to a new conversation (ending the previous one), select and recheck Plan, attach business-requirements.txt, data-dictionary.txt, domain-model.png and revision-requirements.txt, and send exactly the same request as in A. Do not apply or save.
5. In B's answer, check that the file names are shown and that what the documents say (StaticSeed, quality-processed Gold, registration versus shipment and so on) is written separately from the facts of the actual ontology. At the end of the answer, also check the validation results (errors and warnings) and the Preview ontology button.

![The reference image shows business-requirements.pdf, but the current distributed file is business-requirements.txt; select the .txt file from the ZIP attachments. Mismatched answer example: it names four files, distinguishes data layers, identifies missing links and proposes DonationQualityScope, but lists AdministrativeArea as existing. Its claim to preserve existing items is not verified.](../assets/p30-15-attachment-grounding.png)

Answer with attachments (B): the reference image displays business-requirements.pdf, but the current distribution supplies attachments/business-requirements.txt. Select the supplied .txt file from the ZIP when attaching files. The Japanese response uses all four files to distinguish static donations, Eventhouse observations and Notebook 05 quality-processed Gold, but lists AdministrativeArea and Municipality as existing entities. It does not establish preservation of the main ontology. Visible Japanese answer (translated summary; illustrative, not an accepted result): the files describe StaticSeed as static data, RealtimeIncrement as quality-accepted increments, and Gold as input-validated and deduplicated; they do not represent actual shipment or delivery, and SupplierProvidesGift is catalog registration rather than fulfillment. The answer says the layer connections and an actually fulfilling supplier are not represented in the inspected ontology, then proposes one keyless, unbound DonationQualityScope with a String DataLayer property and says existing entities, keys and bindings are unchanged. Check document grounding separately from definition fidelity; stop on assertions inconsistent with the ten-entity, fifteen-relationship baseline. It does not infer delivery or shipment.

</details>
