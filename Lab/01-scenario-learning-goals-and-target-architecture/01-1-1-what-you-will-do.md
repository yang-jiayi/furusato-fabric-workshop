# 1.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

この Lab または HTML と、同じ版の参加者用 ZIP を1組で使います。ZIP の guide に手順書、attachments に添付資料、source に Notebook・データ・実行ツールがあります。初回は4章から24.4〜24.6へ進んで自分で基盤を配置し、5〜8章で作成済みの内容を確認します。24.7と9〜11章で取り込みと品質処理、24.8でモデルと Agent の配置を終えます。17章で調整済み構成を適用し、19章と付録Cで評価します。利用できないプレビュー機能は別に記録します。

このワークショップでは、ふるさと納税を題材にした合成データを使います。Microsoft Fabric の Lakehouse・Eventhouse・Ontology・Semantic model・Data Agent を組み合わせて、業務の意味を共有できるデータ基盤を作ります。自治体名と自治体コードだけが実在の参照ラベルで、寄付・寄付者・事業者・返礼品はすべて架空のデータです。

「東京の寄付」は、東京都の自治体が受け入れた寄付でしょうか、それとも東京都に住む人が行った寄付でしょうか。同じ言葉でも、チームやツールによって意味が変わります。この章では、完成するシステムの全体像を自分で図にして、どの問いをどのデータとエンジンで答えるかを整理します。

学習目標：業務の意味（Ontology）、データの保管（Lakehouse・Eventhouse）、計算（SQL・KQL・DAX・GQL）、AI による説明（Ontology agent・Data Agent）を分けて設計します。手作業での構築から、変更管理、回答品質の評価までを一通り体験します。

準備するもの・確認すること

- 紙やホワイトボードなど、図を書けるものを用意します。
- 付録Aの期待値の表を開いておきます。

<details>
<summary>English</summary>

## 1.1 What you will do

Use this Lab or HTML guide together with the participant ZIP of the same version. In the ZIP, guide contains instructions, attachments the reference files, and source the Notebooks, data and tools. On your first run, go from Chapter 4 to 24.4–24.6 to deploy your own core resources, then inspect them in Chapters 5–8. Complete ingestion and quality processing through 24.7 and Chapters 9–11, then deploy the model and Agent in 24.8. Apply the tuned configuration in Chapter 17 and evaluate in Chapter 19 and Appendix C. Record unavailable preview features separately.

In this workshop you use synthetic data about furusato (hometown tax) donations and combine Microsoft Fabric Lakehouse, Eventhouse, Ontology, semantic model and Data Agent into a data platform that shares business meaning. Only municipality names and codes are real reference labels; all donations, donors, suppliers and gifts are fictitious.

Do "Tokyo donations" mean donations received by municipalities in Tokyo, or donations made by people who live in Tokyo? The same words can mean different things to different teams and tools. In this chapter you sketch the overall architecture yourself and decide which data and engine answer each question.

Learning goals: design business meaning (Ontology), storage (Lakehouse and Eventhouse), calculation (SQL, KQL, DAX and GQL) and AI explanations (Ontology agent and Data Agent) as separate concerns, and experience the whole cycle from manual construction to change management and answer-quality evaluation.

Before you start

- Have paper or a whiteboard ready for sketching.
- Open the expected-value tables in Appendix A.

</details>
