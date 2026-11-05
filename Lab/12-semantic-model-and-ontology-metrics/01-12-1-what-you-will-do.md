# 12.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Semantic model（SM_Furusato_Analytics_&lt;PID&gt;）は Gold を Direct Lake で読み、寄附総額・寄附件数などの DAX メジャーを持ちます。DAX は Semantic model 側で定義され、Ontology の Metrics はそのメジャーを参照するだけです。

この章では、Semantic model に定義された DAX とフィルターの意味を確認します。native Metrics の確認には、講師が同じ主 Ontology に Metrics を事前設定し、利用可能であることを確認しておく必要があります。この章はその事前設定を実施する手順ではありません。標準構成の Ontology は1件のままにします。

準備するもの・確認すること

- 11章（Notebook 05）が完了し、Gold が作成されていることを確認します。
- 24.8の verify-gold、deploy-semantic-model、refresh-model、verify-model を完了し、自分で作成した Semantic model（SM_Furusato_Analytics_&lt;PID&gt;）を開きます。Read・Build 権限を確認します。DAX の式の表示にはモデルの Write 権限も必要です。

<details>
<summary>English</summary>

## 12.1 What you will do

The semantic model (SM_Furusato_Analytics_&lt;PID&gt;) reads Gold through Direct Lake and owns DAX measures such as 寄附総額 and 寄附件数. The DAX is defined in the semantic model; ontology Metrics only refer to those measures.

Check the DAX and filter behavior defined in the semantic model. Native Metrics verification requires the instructor to configure Metrics on that same main ontology beforehand and confirm availability. This chapter does not provide the native setup procedure. Keep exactly one ontology in the standard setup.

Before you start

- Confirm that Chapter 11 (Notebook 05) is complete and that Gold exists.
- Complete verify-gold, deploy-semantic-model, refresh-model and verify-model in 24.8, then open the semantic model you created (SM_Furusato_Analytics_&lt;PID&gt;). Confirm Read and Build permissions; displaying DAX definitions also needs Write permission.

</details>
