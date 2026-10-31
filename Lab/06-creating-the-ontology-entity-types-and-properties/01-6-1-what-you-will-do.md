# 6.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Ontology を開いて10の Entity type を作り、それぞれのキー・型・Property を ot_* テーブルの列にバインドします。

バインドしていない Property は概念として定義できますが、データを照会できません。この章のゴールは、キー・型・バインドを保存し、Instances に実際の行が表示される状態にすることです。空のカードを作っただけでは完了ではありません。

準備するもの・確認すること

- 5章が完了し、11の ot_* テーブルを SQL で読めることを確認します。
- 標準経路では24.6で作成した1件の Ontology（ONT_Furusato_&lt;PID&gt;）を開きます。以下の作成操作は説明として読み、既存の10 Entity、キー、型、バインド、Instances を確認します。重複作成しません。手動で新規作成する場合だけ、名前を1〜26文字の英数字・ハイフン・アンダースコアとし、先頭と末尾を英数字にします。

<details>
<summary>English</summary>

## 6.1 What you will do

Open the ontology, create the 10 entity types and bind each key, type and property to the columns of the ot_* tables.

An unbound property can be defined as a concept, but its data cannot be queried. The goal of this chapter is to save keys, types and bindings so that Instances shows actual rows. Creating empty cards is not enough.

Before you start

- Confirm that Chapter 5 is complete and that the 11 ot_* tables can be read with SQL.
- In the standard route, open the one ontology (ONT_Furusato_&lt;PID&gt;) created in 24.6. Read the creation steps as explanations and inspect the existing ten entities, keys, types, bindings and Instances without creating duplicates. Only for a new manual build, use a 1–26-character alphanumeric/hyphen/underscore name starting and ending with an alphanumeric character.

</details>
