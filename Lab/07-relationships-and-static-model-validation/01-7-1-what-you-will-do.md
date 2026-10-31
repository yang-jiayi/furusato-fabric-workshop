# 7.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

15の Relationship を作り、向き（Origin → Target）とキー列を実際のデータに合わせます。14の関係は外部キーで直接つなぎ、SupplierProvidesGift だけが対応表（mapping table）を使います。

最後に、居住地・受入地・登録地の3つの経路を、別々に説明できる状態にします。図がつながって見えるだけでは完了ではありません。

準備するもの・確認すること

- 6章で10の Entity type のキーとバインドを確認します。24.6で配置済みの場合、この章の作成・Save 操作は説明として読み、既存の15 Relationship の向き・キー・対応表と実際の行を確認します。関係を追加し直しません。
- 下の表で、15の Relationship の向きと、両側のキー列を持つテーブル（表の「キー列を持つテーブル」）を確認します。対応表として使うのは、SupplierProvidesGift の ot_supplier_gift だけです。

<details>
<summary>English</summary>

## 7.1 What you will do

Create the 15 relationships and match their direction (Origin → Target) and key columns to the actual data. Fourteen relationships use a foreign key directly; only SupplierProvidesGift uses a mapping table.

By the end, you should be able to explain the residence, recipient and registration paths separately. A connected picture alone does not mean you are done.

Before you start

- Check the ten entity keys and bindings in Chapter 6. If deployed in 24.6, read this chapter’s create/Save actions as explanations and inspect the existing 15 relationships, direction, keys, mapping table and actual rows without adding them again.
- In the table below, review the direction of the 15 relationships and the table that holds both key columns (the "Table with the key columns" column). Only ot_supplier_gift, for SupplierProvidesGift, is used as a mapping table.

</details>
