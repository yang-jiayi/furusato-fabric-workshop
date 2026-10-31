# 13.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| Rule・関連付け・Metadata が保存されている | 開き直して消えている場合は、Save の前に Cancel していないかを確認し、入力し直します。 |
| Rule によって説明が良くなったかを、実際の回答で確認している | Rule を登録しただけで効果があったとは判断しません。新しい会話で同じ質問をして比べます。 |
| （Notebook 02 を使った場合）プレビューで変更内容を確認してから適用している | 適用が「Explicit expected-definition SHA differs」で止まった場合は、プレビューの後に定義が変わっています。プレビューをやり直し、出力の beforeDefinitionSha256 を EXPECTED_DEFINITION_SHA256 に設定します。 |

<details>
<summary>English</summary>

## 13.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| The rule, its linked concepts and the metadata are saved | If they are gone after reopening, check that you did not select Cancel before Save, and enter them again. |
| You checked with actual answers whether the rule improved the explanations | Do not assume an effect just because a rule is registered. Ask the same question in a new conversation and compare. |
| (If you used Notebook 02) You reviewed the changes in the preview before applying | If the apply run stops with "Explicit expected-definition SHA differs", the definition changed after the preview. Run the preview again and set EXPECTED_DEFINITION_SHA256 to the beforeDefinitionSha256 value in its output. |

</details>
