# 9.2 操作手順（4）

[Lab 目次](../README.md) · [この章の目次](README.md)

9. KQL Queryset で、次のクエリの &lt;SourceFile&gt; を donation_events_001.csv に置き換えて（二重引用符は残します）実行し、5,000行、合計 85,098,000円、EventID の欠落が0であることを確認します。

**KQL**

```kql
let targetSourceFile = "<SourceFile>";
DonationEvents
| where SourceFile == targetSourceFile
| summarize
    Rows=count(),
    DistinctEventIDs=count_distinct(EventID),
    MissingEventIDs=countif(isempty(EventID)),
    DistinctDonationIDs=count_distinct(DonationID),
    TotalDonationAmountYen=sum(DonationAmountYen),
    FirstDonatedAtUtc=min(DonatedAt),
    LatestDonatedAtUtc=max(DonatedAt)
```

10. 送信後は履歴を読み取り、遅延を見込んで待ちます。公式の目安は最大10分で、今回の遅延待機は最低2分です。開始前に確認期限を記録し、期限まで activation がなければ再アップロードせず24.7の stop-activator で停止し、イベント・実行履歴・件数を確認します。取り込み済みか不明なまま手動 Pipeline を重ねません。手動回復を選ぶ場合は、先行処理の終了と対象ファイル未取込を確認して1回だけ実行し、元の失敗を保持して「手動」と記録します。Parameters の IncrementFileName はファイル名とし、Type・Subject・Source の入力値が実際に空であることを確認します。図に見える文字列 Value は入力しません。

![Pipeline run の Parameters 表。IncrementFileName は donation_events_001.csv。Type・Subject・Source の欄には Value の表示が見える。実際の入力値が空であることは各自で確認する。](../assets/p30-09-manual-recovery.png)

講師の指示で手動実行するときの Parameters。IncrementFileName にファイル名を入力し、Type・Subject・Source の入力値は実際に空にします。図ではその3欄に Value と表示されていますが、その表示だけでは入力値が空かは判定できません。文字列 Value を入力・コピーしないでください。

> Pipeline は重複を除きません。同じファイルを2回取り込むと、行が2倍になります。

> Ontology の Business Rules を設定しても、Activator は動きません。ファイルの到着で動くのは、この章のルールだけです。

<details>
<summary>English</summary>

## 9.2 Steps

9. In the KQL queryset, replace &lt;SourceFile&gt; in the following query with donation_events_001.csv (keep the double quotes) and run it. Confirm 5,000 rows, a total of JPY 85,098,000 and zero missing EventIDs.

**KQL**

```kql
let targetSourceFile = "<SourceFile>";
DonationEvents
| where SourceFile == targetSourceFile
| summarize
    Rows=count(),
    DistinctEventIDs=count_distinct(EventID),
    MissingEventIDs=countif(isempty(EventID)),
    DistinctDonationIDs=count_distinct(DonationID),
    TotalDonationAmountYen=sum(DonationAmountYen),
    FirstDonatedAtUtc=min(DonatedAt),
    LatestDonatedAtUtc=max(DonatedAt)
```

10. Read history after submission and allow for latency. Published guidance is up to ten minutes; this rule’s late-arrival wait is at least two minutes. Record a deadline beforehand. If no activation appears by then, do not upload again: stop with stop-activator in 24.7 and inspect events, run history and counts. Do not overlap a manual Pipeline while ingestion is uncertain. If choosing manual recovery, first establish that prior processing ended and the file was not ingested, then run once, retaining the failure and labeling the ingestion manual. Set IncrementFileName to the filename and ensure the entered values for Type, Subject and Source are genuinely empty. Do not type the literal Value shown in the example.

![Pipeline run Parameters showing donation_events_001.csv and the visible text Value in Type, Subject and Source; independently ensure their entered values are empty.](../assets/p30-09-manual-recovery.png)

Parameters for an instructor-directed manual run: enter the filename in IncrementFileName and ensure the entered values for Type, Subject and Source are genuinely empty. The image displays Value in those three fields; that display alone does not establish whether an entered value is empty. Do not type or copy the literal string Value.

> The Pipeline does not remove duplicates. Ingesting the same file twice doubles the rows.

> Setting ontology Business Rules does not trigger the Activator. Only the rule in this chapter reacts to file arrivals.

</details>
