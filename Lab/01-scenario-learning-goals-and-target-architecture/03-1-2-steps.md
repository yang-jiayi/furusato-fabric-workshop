# 1.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

3. 図の上に Ontology を置き、Entity type・Property・Relationship、データへのバインド、Metrics、自然言語の Business Rules を書き込みます。Ontology は業務の意味と経路を宣言する層であり、データを保管する場所や、すべての集計を実行するエンジンではありません。
4. 問いごとに使うエンジンを書きます。通常の件数や合計は SQL（Lakehouse）・KQL（Eventhouse）・DAX（Semantic model）で求めます。関係の経路そのものが問われるときだけ、必要な部分を Graph として実体化し、GQL を使います。
5. AI の位置を書き込みます。Data Agent は1件だけ作り、Lakehouse・KQL Database・Ontology・Semantic model の4つをソースにして、Code Interpreter をその Agent のツールとして使います。Ontology agent（Ontology Copilot）は Ontology に組み込まれた別の機能です。
6. 手順1の4つの問いそれぞれについて、意味（何を数えるか）、データの層（静的データ・8月の観測データ・Gold）、粒度、期間、使うエンジンを1行で書きます。

> この章の図は、後の章で何度も見返します。分からない部分は空欄のままにして、該当する章で埋めてください。

<details>
<summary>English</summary>

## 1.2 Steps

3. Place the ontology on top of the sketch and add entity types, properties, relationships, data bindings, Metrics and natural-language Business Rules. The ontology declares business meaning and paths; it is neither a place to store data nor an engine that runs every calculation.
4. Write down the engine for each question. Ordinary counts and totals come from SQL (Lakehouse), KQL (Eventhouse) and DAX (semantic model). Only when the relationship path itself matters do you materialize the needed part as a graph and use GQL.
5. Add the AI components. You create only one Data Agent; its four sources are the Lakehouse, the KQL database, the ontology and the semantic model, and Code Interpreter is a tool of that agent. The Ontology agent (Ontology Copilot) is a separate feature built into the ontology.
6. For each of the four questions in step 1, write one line covering its meaning (what is counted), data layer (static data, August observation data or Gold), grain, period and engine.

> You will return to this sketch in later chapters. Leave unclear parts blank and fill them in when you reach the relevant chapter.

</details>
