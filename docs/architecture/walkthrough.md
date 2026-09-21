# Closing architecture walkthrough / 最後に見る全体像

[Architecture home](README.md) · [Japanese explorer](index.html?lang=ja&focus=overview) ·
[English explorer](index.html?lang=en&focus=overview)

Use this section **after the demonstrations**, as the ending of the JA/EN promo videos.
Record the actual local browser explorer at **2560 × 1440, 100% browser zoom**.
The view stays steady while the selected path gains emphasis and its explanation changes.
Click the top flow buttons; the full architecture remains in view.
Timing is a recording guide, not a claim about an assembled video.

実演の後、JA／EN 動画の**締めくくり**として使う台本です。
スライドではなく、ローカルの対話型ページをブラウザーで撮影します。
固定した全体図の中で経路を選び、右側の説明を切り替えます。
収録と動画の編集・公開は、この資料とは別の工程です。

## Browser cues / 画面の順序

| Order | Focus | Visual cue / 画面で示すこと |
|---|---|---|
| 1 | **Overview / 全体像** | Business question; one Agent and three sources / 業務の問い、主 Agent と 3 ソース |
| 2 | **01 Facts & meaning / 事実と意味** | Seed → Notebook 01 → SQL and full Ontology / 静的データから事実と意味へ |
| 3 | **02 Observations / 運用の観測** | FileCreated signal versus CSV Copy; stopped-trigger note / イベント通知と CSV 本体を区別 |
| 4 | **03 One Agent / 1 件の Agent** | SQL, KQL, GQL; returned results → optional Code Interpreter / 照会の根拠と任意の後処理 |
| 5 | **04 Quality & BI / 品質と BI** | Actual Lakehouse inputs → quality / Gold → Direct Lake / 入力、品質、BI の独立経路 |
| 6 | **00 Approved setup / 承認付き構築** | Separate preview / hash / consent control strip / データ経路から分けた承認ゲート |
| 7 | **Learning outcomes / 学びのまとめ** | Positive conclusion with the complete architecture still visible / 全体像を保ったまま価値で締める |

Allow a short pause after each click and hold the last view for several seconds.
Natural pacing is more important than a fixed duration.
Use `?lang=ja&focus=overview` or `?lang=en&focus=overview` to start;
use `focus=outcomes` to reopen the final composition.

## 日本語ナレーション

### 1 — 全体像

最後に、実習で見た機能を、ひとつの全体像でつなぎます。
誰が、どの自治体に寄付し、どの返礼品を選んだのか。
この業務の問いを、事実・関係・運用の観測から読み解きます。

### 2 — 事実と意味

静的な CSV 8 本を、Notebook 01 が 11 個の教材テーブルへ整えます。
SQL は属性と集計、完全な Ontology は業務の関係を担当します。
寄付者の居住地、寄付の受取先、事業者の登録を分けることで、
同じ地名や金額でも、正しい意味で説明できます。

### 3 — 運用の観測

増分は OneLake のファイル到着を起点に、Activator と Pipeline Copy を通って
Eventhouse へ入ります。ここで扱うのは、再送を含む raw の観測です。
図は設計上の経路を示し、デモでは取り込み確認後にトリガーを停止しています。

### 4 — 1 件の Agent

主 Data Agent は SQL・KQL・ネイティブ GQL の 3 ソースを使い分けます。
Code Interpreter は、取得した結果を計算や図へ広げる、同じ Agent の追加ツールです。
出典、対象、指標、単位をそろえることで、回答の根拠をたどれます。

### 5 — 品質と BI

任意の Notebook 05 は、Lakehouse のテーブルと増分 CSV を直接読み取ります。
品質検査と重複排除を経た Gold から、Direct Lake の Power BI 分析へ。
raw の観測と、分析用に受け入れたデータの違いも、明確に保ちます。

### 6 — 承認付き構築

構築は別の制御レーンです。Notebook 04 の preview、plan hash、同意を通じて、
参加者の範囲を確認しながら進めます。

### 7 — 学びのまとめ

この Workshop で学ぶのは、機能の操作だけではありません。
業務の意味をモデル化し、適したエンジンを選び、品質を確かめ、
根拠をもって伝えることです。データ・意味・分析が、ひとつにつながります。

## English narration

### 1 — Overview

To close, let's connect the features we explored into one architecture.
Who donated, which municipality received the donation, and which gift was selected?
The workshop answers that business question through facts, relationships and operational observations.

### 2 — Facts and meaning

Notebook 01 turns eight static CSVs into eleven teaching tables.
SQL supplies attributes and aggregates; the full Ontology supplies business relationships.
Separating donor residence, donation recipients and supplier registration gives each result
the right meaning.

### 3 — Observations

Incremental files arrive in OneLake. FileCreated signals Activator, and Pipeline Copy reads
the CSVs into Eventhouse. This path preserves raw observations, including retransmissions.
The diagram shows the design route; the demo trigger was stopped after ingestion verification.

### 4 — One Agent

One primary Data Agent uses three sources: SQL, KQL and native GQL.
Code Interpreter is an additional tool in that same Agent, turning returned results into
calculations, charts and files. Source, scope, metric and unit make the answer traceable.

### 5 — Quality and BI

Optional Notebook 05 reads Lakehouse tables and incremental CSVs directly.
Quality checks and deduplication prepare Gold for Direct Lake and Power BI.
Raw observations and accepted analytical data keep their distinct meanings.

### 6 — Approved setup

Provisioning has its own control lane. Notebook 04's preview, plan hash and consent
keep setup tied to the participant's approved scope.

### 7 — Learning outcomes

The takeaway goes beyond operating individual features.
Model business meaning, choose the right engine, make quality visible, and communicate
with evidence. One workshop connects data, meaning and analysis.

## Recording boundary / 収録範囲

This page is explanatory and offline. Selecting paths changes only the local presentation.
The closing sequence requires no Fabric queries, ingestion, activation, sign-in or resource changes.
The architecture summary complements the earlier demonstration rather than asserting a fresh
end-to-end execution or an answer-quality certification.

この締めくくりは、説明用のローカル画面だけで成立します。
経路の選択が変えるのは表示です。先に見た実演を整理し、最後は学習成果で締めます。
