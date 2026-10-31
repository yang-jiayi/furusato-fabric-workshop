# 10.2 操作手順（1）

[Lab 目次](../README.md) · [この章の目次](README.md)

1. Files/increment に donation_events_002.csv を1回だけアップロードし、9章と同じ順番（イベント、activation、Pipeline、Copy、KQL）で確認します。SourceFile が donation_events_002.csv の行は、5,000行・84,687,000円です。
2. 002 の確認が終わってから donation_events_003.csv をアップロードし、同じように確認します（5,000行・84,101,000円）。
3. 3ファイルの確認が終わったら、24.7の stop-activator を1回実行し、実行中の Pipeline が無いことを確認します。停止済みなら状態を確認するだけにします。
4. ビューの合計を確認します。ObservationCount が 15,000、ObservedAmountYen が 253,886,000円、最初の観測が 2026-08-01T00:02:47Z、最後の観測が 2026-08-31T23:58:20Z です。

**KQL**

```kql
DonationObservationSummaryForAgent
| summarize
    ObservationCount=sum(ObservationCount),
    ObservedAmountYen=sum(ObservedAmountYen),
    FirstObservedAt=min(FirstObservedAt),
    LastObservedAt=max(LastObservedAt)
```

5. EventID の一意な件数を正確に数えます。結果は 14,900 です。近似値を返す dcount は使いません。

**KQL**

```kql
DonationEvents
| summarize by EventID
| count
```

6. 重複の件数を数えます。結果は 100 です。重複を除いた金額は 252,058,000円で、重複を含む 253,886,000円とは別の値です。

**KQL**

```kql
DonationEvents
| summarize Rows=count() by EventID
| summarize DuplicateRows=sum(Rows - 1)
```

7. 日ごとの分布を確認します。UTC で 2026-08-01〜08-31 の31日すべてに行があり、1日 450〜582行です。2026-08-11 が 582行と多いのは、重複がこの日に集中しているためです。

**KQL**

```kql
DonationEvents
| summarize Rows=count(), TotalYen=sum(DonationAmountYen) by UtcDay=bin(DonatedAt, 1d)
| order by UtcDay asc
```

8. Ontology で Municipality を開き、Configure → Manage property bindings → Add binding and properties を選びます。EH_Furusato_&lt;PID&gt; の DonationEvents テーブルを追加します（ビューの DonationObservationSummaryForAgent は選びません）。共通の列として DonationEvents の MunicipalityID と Municipality の MunicipalityId を対応させ、Save します。
9. Entity type properties で、IncomingDonationAmountYen に DonationEvents.DonationAmountYen を対応させます（定義済みならその Property を選び、まだ無い場合はこの名前で作ります）。型が Timeseries&lt;Integer&gt;、Timestamp column が DonatedAt（UTC）であることを確認します。_2 などが付いた別名の Property を作らないようにし、保存の前後で Property の一覧を比べます。

![Property の対応表。静的 Property は ot_municipality の列、IncomingDonationAmountYen は Timeseries&lt;Integer&gt; で、Timestamp column は DonatedAt](../assets/p30-10-timeseries.png)

IncomingDonationAmountYen を DonationEvents の金額の列に対応させた状態。型は Timeseries&lt;Integer&gt;、Timestamp column は DonatedAt

<details>
<summary>English</summary>

## 10.2 Steps

1. Upload donation_events_002.csv to Files/increment once and check it in the same order as in Chapter 9 (event, activation, Pipeline, Copy and KQL). The rows with SourceFile donation_events_002.csv are 5,000 rows and JPY 84,687,000.
2. After 002 is confirmed, upload donation_events_003.csv and check it in the same way (5,000 rows and JPY 84,101,000).
3. After verifying all three files, run stop-activator in 24.7 once and confirm that no Pipeline is running. If already stopped, only inspect its state.
4. Check the totals of the view: ObservationCount 15,000, ObservedAmountYen JPY 253,886,000, first observation 2026-08-01T00:02:47Z and last observation 2026-08-31T23:58:20Z.

**KQL**

```kql
DonationObservationSummaryForAgent
| summarize
    ObservationCount=sum(ObservationCount),
    ObservedAmountYen=sum(ObservedAmountYen),
    FirstObservedAt=min(FirstObservedAt),
    LastObservedAt=max(LastObservedAt)
```

5. Count unique EventIDs exactly. The result is 14,900. Do not use dcount, which returns an approximation.

**KQL**

```kql
DonationEvents
| summarize by EventID
| count
```

6. Count the duplicates. The result is 100. The amount without duplicates is JPY 252,058,000, which differs from JPY 253,886,000 including duplicates.

**KQL**

```kql
DonationEvents
| summarize Rows=count() by EventID
| summarize DuplicateRows=sum(Rows - 1)
```

7. Check the daily distribution. Every one of the 31 UTC days from 2026-08-01 to 08-31 has rows, with 450 to 582 rows per day. 2026-08-11 has 582 rows because the duplicates are concentrated on that day.

**KQL**

```kql
DonationEvents
| summarize Rows=count(), TotalYen=sum(DonationAmountYen) by UtcDay=bin(DonatedAt, 1d)
| order by UtcDay asc
```

8. In the ontology, open Municipality and select Configure → Manage property bindings → Add binding and properties. Add the DonationEvents table of EH_Furusato_&lt;PID&gt; (do not choose the view DonationObservationSummaryForAgent). Map MunicipalityID in DonationEvents to MunicipalityId in Municipality as the common column, then Save.
9. In Entity type properties, map DonationEvents.DonationAmountYen to IncomingDonationAmountYen (select the existing property if it is already defined; otherwise create it with this name). Confirm that the type is Timeseries&lt;Integer&gt; and that the Timestamp column is DonatedAt (UTC). Avoid creating a duplicate property with a suffix such as _2, and compare the property list before and after saving.

![Binding table: static properties map to ot_municipality columns; IncomingDonationAmountYen uses Timeseries&lt;Integer&gt; and Timestamp column DonatedAt.](../assets/p30-10-timeseries.png)

Time-series binding: IncomingDonationAmountYen is mapped to the DonationEvents amount column as Timeseries&lt;Integer&gt;, with Timestamp column DonatedAt.

</details>
