# 英語ミラー: 翻訳ルールと用語集 / English mirror — translation rules and glossary

[日本語](#日本語) | [English](#english)

---

## 日本語

### 概要

正本は Word 版の参加者ガイドであり、日本語で執筆されています。HTML 配布物は
**同一の**コンテンツモデルを 2 回描画します。1 回は日本語、もう 1 回は英語です。
そのため `furusato_html.i18n` は、キャプチャしたコンテンツモデルが生成する
すべての日本語文字列に対して英語文字列を 1 つ保持し、キーは日本語の原文文字列そのものです。

キャプチャされた日本語文字列に対応する英語エントリが無い場合、ビルドは失敗します。
したがって、このマップが Word ガイドから静かに遅れることはありません。

### ハードルール

1. **ミラーであり、要約ではない。** 日本語原文にあるすべての文、節、数値、警告、
   留保は、英語文字列にも必ず現れなければなりません。
2. **技術トークンを決して変更しない。** 識別子、テーブル名・列名、Notebook 名・
   アイテム名、ファイル名、パス、パラメーター名、KQL/SQL/GQL 断片、ハッシュ、URL、
   日付、時刻、件数、金額は逐語的にコピーします。
3. **インラインコードのマーカーを保つ。** 日本語文字列の `` `backtick` `` スパンは
   英語でもバッククォートのスパンのままとし、同一のトークンを包みます。
4. **UI ラベルの括弧を保つ。** `［Add entity type］` は `［Add entity type］` のままです。
   全角括弧はコントロールラベルを表すハウスルールです。日本語のコントロールラベルは
   出荷されている英語版 Fabric のラベルにします
   （`［新規］` → `［New］`、`［新規アイテム］` → `［New item］`）。
5. **数値の書式を保つ。** `1,344,099,000 円` は `1,344,099,000 JPY` になり、
   `15,000 行` は `15,000 rows` になります。数字と区切り記号を再整形することはありません。
6. **文体を保つ。** 手順ステップは指示的な命令形、根拠の説明は叙述形にします。
   新たな宣伝的形容詞を加えません。
7. **代替テキストは説明的に保つ。** 図の代替テキストは、スクリーンショットや図版が
   見えない人に対して、日本語と同じ詳細度で「何が見えるか」を説明します。

これらのルールは安全性に関わります。特にルール 1 と 2 は、警告・拒否・境界の
記述を弱めたり省略したりすることを禁じます。日本語側で拒否や禁止を述べている文は、
英語側でも同じ強さの拒否・禁止として現れなければなりません。

### 用語集

| 日本語 | 英語 |
|---|---|
| ふるさと納税 | Furusato hometown-tax donation |
| 参加者 | participant |
| 完成アーキテクチャ | target architecture |
| 到達点 | outcome |
| 静的シード | static seed |
| 増分 | increment |
| 観測窓 | observation window |
| 粒度 | grain |
| 業務識別子 | business identifier |
| 代理キー | surrogate key |
| 同一性 | identity |
| 意味の境界 | semantic boundary |
| 判断フロー | decision flow |
| 逆方向トラバース | reverse traversal |
| 多段トラバース | multi-hop traversal |
| 重複排除 | de-duplication |
| 合算 | addition (of two totals) |
| 属性推論 | attribute inference |
| 拒否する | refuse |
| ゲート | gate |
| 検証 | validation |
| 期待値 | expected value |
| 既定値 | default |
| 安全ゲート | safety gate |
| 復旧経路 | recovery path |
| 冪等 | idempotent |
| 手戻り | rework |
| 突き合わせ | reconciliation |
| 目視確認 | visual check |
| 受入 Prefecture | recipient prefecture |
| 在住 Prefecture | residence prefecture |
| 返礼品 | return gift |
| 事業者 | supplier |
| 自治体 | municipality |
| 寄付者 | donor |
| 例クエリ | example query |
| 口語 | colloquial |
| 曖昧語 | ambiguous term |
| 恒久 | permanent |
| 一括登録 | bulk registration |
| 正本 | source of truth |

製品名、ワークロード名、オブジェクト名は、両言語とも出荷されている英語形のままにします。
Microsoft Fabric、Fabric IQ、Ontology、Entity Type、Relationship Type、Property、
Lakehouse、Eventhouse、KQL Queryset、Data Pipeline、OneLake、Notebook、Data Agent、
Activator、Materialized View、Direct Lake、Power BI。

### ファイル

| ファイル | 内容 |
|---|---|
| `guide-NN.json` | キャプチャしたガイド内容に対する `{ "<japanese>": "<english>" }`。レビューしやすさのためだけに順序付きのチャンクへ分割しています。 |
| `ui.json` | HTML にのみ存在する chrome、コントロール、状態、live region の文字列。 |

チャンクの境界に意味はありません。ローダーはすべての `guide-*.json` を 1 つのマップへ
統合し、値が矛盾する重複キーを拒否します。

---

## English

### Overview

The Word participant guide is canonical and authored in Japanese. The HTML
deliverable renders the **same** content model twice: once in Japanese and once
in English. `furusato_html.i18n` therefore keeps one English string for every
Japanese string the captured content model produces, keyed by the exact
Japanese source string.

The build fails if a captured Japanese string has no English entry, so the map
can never silently fall behind the Word guide.

### Hard rules

1. **Mirror, do not summarise.** Every sentence, clause, number, warning and
   caveat in the Japanese source must appear in the English string.
2. **Never change technical tokens.** Identifiers, table and column names,
   notebook and item names, file names, paths, parameter names, KQL/SQL/GQL
   fragments, hashes, URLs, dates, times, counts and yen amounts are copied
   verbatim.
3. **Keep inline code markers.** A `` `backtick` `` span in the Japanese string
   stays a backtick span in English, wrapping the identical token.
4. **Keep UI-label brackets.** `［Add entity type］` stays `［Add entity type］`;
   the full-width brackets are the house convention for a control label.
   Japanese control labels become the shipped English Fabric label
   (`［新規］` → `［New］`, `［新規アイテム］` → `［New item］`).
5. **Keep numeric formatting.** `1,344,099,000 円` becomes
   `1,344,099,000 JPY`; `15,000 行` becomes `15,000 rows`. Digits and
   separators are never re-formatted.
6. **Keep the register.** Instructional imperative for procedure steps,
   declarative for rationale. No new marketing adjectives.
7. **Alt text stays descriptive.** Figure alt text describes what is visible in
   the screenshot or diagram for someone who cannot see it, at the same level of
   detail as the Japanese.

These rules are safety-relevant. Rules 1 and 2 in particular forbid weakening or
dropping any warning, refusal or boundary statement. A sentence that states a
refusal or a prohibition in Japanese must appear as an equally strong refusal or
prohibition in English.

### Glossary

| Japanese | English |
|---|---|
| ふるさと納税 | Furusato hometown-tax donation |
| 参加者 | participant |
| 完成アーキテクチャ | target architecture |
| 到達点 | outcome |
| 静的シード | static seed |
| 増分 | increment |
| 観測窓 | observation window |
| 粒度 | grain |
| 業務識別子 | business identifier |
| 代理キー | surrogate key |
| 同一性 | identity |
| 意味の境界 | semantic boundary |
| 判断フロー | decision flow |
| 逆方向トラバース | reverse traversal |
| 多段トラバース | multi-hop traversal |
| 重複排除 | de-duplication |
| 合算 | addition (of two totals) |
| 属性推論 | attribute inference |
| 拒否する | refuse |
| ゲート | gate |
| 検証 | validation |
| 期待値 | expected value |
| 既定値 | default |
| 安全ゲート | safety gate |
| 復旧経路 | recovery path |
| 冪等 | idempotent |
| 手戻り | rework |
| 突き合わせ | reconciliation |
| 目視確認 | visual check |
| 受入 Prefecture | recipient prefecture |
| 在住 Prefecture | residence prefecture |
| 返礼品 | return gift |
| 事業者 | supplier |
| 自治体 | municipality |
| 寄付者 | donor |
| 例クエリ | example query |
| 口語 | colloquial |
| 曖昧語 | ambiguous term |
| 恒久 | permanent |
| 一括登録 | bulk registration |
| 正本 | source of truth |

Product, workload and object names keep their shipped English form in both
languages: Microsoft Fabric, Fabric IQ, Ontology, Entity Type, Relationship
Type, Property, Lakehouse, Eventhouse, KQL Queryset, Data Pipeline, OneLake,
Notebook, Data Agent, Activator, Materialized View, Direct Lake, Power BI.

### Files

| File | Contents |
|---|---|
| `guide-NN.json` | `{ "<japanese>": "<english>" }` for the captured guide content, split into ordered chunks purely for reviewability. |
| `ui.json` | Chrome, control, status and live-region strings that exist only in the HTML. |

Chunk boundaries carry no meaning; the loader merges every `guide-*.json` into
one map and rejects duplicate keys with conflicting values.
