# 17.7 現在の Agent と選択契約を読み取る

[Lab 目次](../README.md) · [この章の目次](README.md)

既存 Agent の実定義から ID-only binding を解決し、selection-contract.json の path・type・is_selected と照合します。対象は資産ファイルに列挙された選択だけです。欠落・曖昧・予期しない差分があれば停止します。UI で親を再選択して子要素を増やしたり、存在しない ID を作ったりしません。

**実際の flat selection contract**

**Readable field list — source order from `workshop/v3.0.0-preview/data-agent/profiles/current-experimental/selection-contract.json`**

<p><strong>レコード 1</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views<br>
<strong>Type:</strong> kusto<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Materialized Views<br>
<strong>説明:</strong> Selected Eventhouse KQL materialized views.
</p>

<p><strong>レコード 2</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent<br>
<strong>Type:</strong> kusto.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationObservationSummaryForAgent<br>
<strong>説明:</strong> Curated operational aggregates that exclude Donation, Donor, Gift, Supplier, payment, fulfillment, approval, deduplication, and lifecycle identifiers or state.
</p>

<p><strong>レコード 3</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / MunicipalityID<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityID<br>
<strong>説明:</strong> Recipient Municipality identifier for the grouped operational observations.
</p>

<p><strong>レコード 4</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / EventMinute<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> EventMinute<br>
<strong>説明:</strong> One-minute time bucket for the grouped operational observations.
</p>

<p><strong>レコード 5</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / WorkshopRunId<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> WorkshopRunId<br>
<strong>説明:</strong> Unique workshop publication run identifier.
</p>

<p><strong>レコード 6</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / ParticipantAlias<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ParticipantAlias<br>
<strong>説明:</strong> Short participant alias for the workshop run.
</p>

<p><strong>レコード 7</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / SourceFile<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SourceFile<br>
<strong>説明:</strong> Workshop publisher or source-file label.
</p>

<p><strong>レコード 8</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / ObservationCount<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ObservationCount<br>
<strong>説明:</strong> Number of operational observations represented by this aggregate row; sum this column for observation totals.
</p>

<p><strong>レコード 9</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / ObservedAmountYen<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ObservedAmountYen<br>
<strong>説明:</strong> Total incoming observed amount in Japanese yen represented by this aggregate row; sum this column for amount totals.
</p>

<p><strong>レコード 10</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / FirstObservedAt<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> FirstObservedAt<br>
<strong>説明:</strong> Earliest operational event timestamp represented by this aggregate row.
</p>

<p><strong>レコード 11</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / LastObservedAt<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> LastObservedAt<br>
<strong>説明:</strong> Latest operational event timestamp represented by this aggregate row.
</p>

<p><strong>レコード 12</strong><br>
<strong>論理ソース:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / LastPublishedAtUtc<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> LastPublishedAtUtc<br>
<strong>説明:</strong> Latest UTC timestamp when the workshop publisher sent an observation represented by this aggregate row.
</p>

<p><strong>レコード 13</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas<br>
<strong>Type:</strong> schema_grouping<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Schemas<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 14</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo<br>
<strong>Type:</strong> lakehouse_tables.schema<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> dbo<br>
<strong>説明:</strong> Curated Furusato static snapshot tables.
</p>

<p><strong>レコード 15</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables<br>
<strong>Type:</strong> table_grouping<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Tables<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 16</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_prefecture<br>
<strong>説明:</strong> Japanese prefecture (都道府県) used in two separate geography paths: recipient geography through Municipality and donor-residence geography through Donor. It is a reference dimension, not a Donation fact grain.
</p>

<p><strong>レコード 17</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureId<br>
<strong>説明:</strong> Stable numeric identifier for one Japanese Prefecture entity. Use it to disambiguate names and as the relationship key; do not aggregate it. If the user explicitly asks for a 都道府県 or Prefecture result, keep this grain and never substitute a Municipality.
</p>

<p><strong>レコード 18</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefectureName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureName<br>
<strong>説明:</strong> Official Japanese display label of the prefecture (都道府県名). Preserve the exact stored Japanese text in output.
</p>

<p><strong>レコード 19</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefectureNameEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureNameEn<br>
<strong>説明:</strong> Canonical English label of the prefecture. Use it for English lookup and display; PrefectureId remains the identity.
</p>

<p><strong>レコード 20</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefReceivedStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefReceivedStaticCount<br>
<strong>説明:</strong> Pre-aggregated count of static Donations received by municipalities in this Prefecture.
</p>

<p><strong>レコード 21</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefReceivedTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefReceivedTotalYen<br>
<strong>説明:</strong> Pre-aggregated JPY amount received by municipalities in this Prefecture.
</p>

<p><strong>レコード 22</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefReceivedAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefReceivedAmountRank<br>
<strong>説明:</strong> Received-amount rank of this Prefecture across all Prefectures. Deterministic row-number rank (row_number) over PrefReceivedTotalYen desc, PrefectureId asc: equal amounts never share a rank because PrefectureId breaks the tie ascending.
</p>

<p><strong>レコード 23</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefResidentStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefResidentStaticCount<br>
<strong>説明:</strong> Pre-aggregated count of static Donations made by Donors who live in this Prefecture.
</p>

<p><strong>レコード 24</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefResidentTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefResidentTotalYen<br>
<strong>説明:</strong> Pre-aggregated JPY amount donated by Donors who live in this Prefecture.
</p>

<p><strong>レコード 25</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefResidentAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefResidentAmountRank<br>
<strong>説明:</strong> Resident-amount rank of this Prefecture across all Prefectures. Deterministic row-number rank (row_number) over PrefResidentTotalYen desc, PrefectureId asc: equal amounts never share a rank because PrefectureId breaks the tie ascending.
</p>

<p><strong>レコード 26</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_municipality<br>
<strong>説明:</strong> Japanese municipality (自治体／市区町村) that may receive zero or more Donations. It also keys operational time-series observations; those observations are not Donation entities and have no Donor, Gift, or Supplier identity. SQL joins: PrefectureId supports MunicipalityInPrefecture.
</p>

<p><strong>レコード 27</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityId<br>
<strong>説明:</strong> Stable identifier for one Municipality entity. Preserve leading zeros if present and use it as the relationship key; do not aggregate it.
</p>

<p><strong>レコード 28</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityName<br>
<strong>説明:</strong> Japanese municipality name (自治体名／市区町村名) without a prefecture qualifier. Names are not globally unique, so include MunicipalityId or MunicipalityDisplayName when ambiguity is possible.
</p>

<p><strong>レコード 29</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityDisplayName<br>
<strong>説明:</strong> Display-only composite label in the format MunicipalityName, PrefectureName, and MunicipalityId. Use MunicipalityId as the identity and this property only for unambiguous human-readable output.
</p>

<p><strong>レコード 30</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityStaticCount<br>
<strong>説明:</strong> Pre-aggregated count of static Donations received by this Municipality.
</p>

<p><strong>レコード 31</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityStaticTotalYen<br>
<strong>説明:</strong> Pre-aggregated static Donation amount received by this Municipality in JPY.
</p>

<p><strong>レコード 32</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityAmountRank<br>
<strong>説明:</strong> Received-amount rank of this Municipality across all Municipalities. Deterministic row-number rank (row_number) over MunicipalityStaticTotalYen desc, MunicipalityId asc: equal amounts never share a rank because MunicipalityId breaks the tie ascending.
</p>

<p><strong>レコード 33</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityPrefAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityPrefAmountRank<br>
<strong>説明:</strong> Received-amount rank of this Municipality inside its containing Prefecture. Deterministic row-number rank (row_number) over MunicipalityStaticTotalYen desc, MunicipalityId asc within each PrefectureId: equal amounts never share a rank because MunicipalityId breaks the tie ascending.
</p>

<p><strong>レコード 34</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureId<br>
<strong>説明:</strong> Foreign key used by MunicipalityInPrefecture.
</p>

<p><strong>レコード 35</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_donor<br>
<strong>説明:</strong> Synthetic workshop donor (寄付者／寄附者) who may make zero or more Donations. Residence is defined only by DonorLivesInPrefecture and must never be interpreted as recipient geography. SQL joins: PrefectureId supports DonorLivesInPrefecture.
</p>

<p><strong>レコード 36</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorId<br>
<strong>説明:</strong> Stable numeric identifier for one synthetic Donor entity. Names aren't guaranteed unique, so use this ID to disambiguate people.
</p>

<p><strong>レコード 37</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorName<br>
<strong>説明:</strong> Synthetic Japanese personal-style name of the donor (寄付者名／支援者名). It is not guaranteed to be unique and does not represent a real person.
</p>

<p><strong>レコード 38</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorDisplayName<br>
<strong>説明:</strong> Display-only composite of DonorName and DonorId. Use DonorId for identity and this property for human-readable output.
</p>

<p><strong>レコード 39</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorAge<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorAge<br>
<strong>説明:</strong> Whole-year age of the synthetic donor (年齢) in the static donor record. It is not derived from the Donation timestamp and must not be summed.
</p>

<p><strong>レコード 40</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorOccupation<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorOccupation<br>
<strong>説明:</strong> Japanese controlled occupation or job label (職業／職種／仕事) for the synthetic donor. It describes the donor's job category, not employer, recipient, or Supplier type.
</p>

<p><strong>レコード 41</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorOccupationEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorOccupationEn<br>
<strong>説明:</strong> Canonical English occupation label for DonorOccupation. Use it for English filtering and grouping; preserve DonorOccupation when returning the stored Japanese label.
</p>

<p><strong>レコード 42</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorStaticCount<br>
<strong>説明:</strong> Pre-aggregated number of static Donations made by this Donor.
</p>

<p><strong>レコード 43</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorStaticTotalYen<br>
<strong>説明:</strong> Pre-aggregated cumulative static Donation amount made by this Donor in JPY.
</p>

<p><strong>レコード 44</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorStaticMaxYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorStaticMaxYen<br>
<strong>説明:</strong> Maximum single static Donation amount made by this Donor in JPY; it is not the cumulative amount.
</p>

<p><strong>レコード 45</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorOverallAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorOverallAmountRank<br>
<strong>説明:</strong> Cumulative static donation-amount rank of this Donor nationwide. Deterministic row-number rank (row_number) over DonorStaticTotalYen desc, DonorId asc: equal amounts never share a rank because DonorId breaks the tie ascending.
</p>

<p><strong>レコード 46</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorResidenceAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorResidenceAmountRank<br>
<strong>説明:</strong> Cumulative static donation-amount rank of this Donor inside the residence Prefecture. Deterministic row-number rank (row_number) over DonorStaticTotalYen desc, DonorId asc within each PrefectureId: equal amounts never share a rank because DonorId breaks the tie ascending.
</p>

<p><strong>レコード 47</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureId<br>
<strong>説明:</strong> Foreign key used by DonorLivesInPrefecture.
</p>

<p><strong>レコード 48</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_gift_category<br>
<strong>説明:</strong> Controlled classification of return-gift options (返礼品カテゴリ). Category counts and amounts must be aggregated from Donation through DonationSelectedGift and GiftInCategory; the category itself is not a transaction fact.
</p>

<p><strong>レコード 49</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryId<br>
<strong>説明:</strong> Stable numeric identifier for one GiftCategory entity. Use it with the stored category labels and never sum or average it.
</p>

<p><strong>レコード 50</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryName<br>
<strong>説明:</strong> Canonical Japanese return-gift category label (返礼品カテゴリ／返礼品分類). Category metrics must be calculated from Donation, not from this label.
</p>

<p><strong>レコード 51</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryNameEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryNameEn<br>
<strong>説明:</strong> Canonical English return-gift category label paired one-to-one with CategoryName. Use it for English filtering, grouping, and display; CategoryId remains the identity.
</p>

<p><strong>レコード 52</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategorySearchTerms<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategorySearchTerms<br>
<strong>説明:</strong> Lowercase pipe-delimited Japanese and English aliases with leading and trailing boundary pipes, used only to resolve colloquial return-gift category wording such as 海鮮系, 魚介, seafood, or equivalent bounded terms. If CategoryName does not match, query this alias index before claiming no category data. Never display, group, count, or treat this property as the category identity.
</p>

<p><strong>レコード 53</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryStaticCount<br>
<strong>説明:</strong> Pre-aggregated static Donation count for this GiftCategory across the full snapshot.
</p>

<p><strong>レコード 54</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryStaticTotalYen<br>
<strong>説明:</strong> Pre-aggregated static Donation amount for this GiftCategory across the full snapshot.
</p>

<p><strong>レコード 55</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryAmountRank<br>
<strong>説明:</strong> Static donation-amount rank of this GiftCategory across all GiftCategories. Deterministic row-number rank (row_number) over CategoryStaticTotalYen desc, CategoryId asc: equal amounts never share a rank because CategoryId breaks the tie ascending.
</p>

<p><strong>レコード 56</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_gift<br>
<strong>説明:</strong> Synthetic return-gift option selected by a Donation (返礼品／お礼品／商品). It is a catalog dimension, not the donated money and not a transaction fact. If a Municipality is named, resolve that Municipality and traverse MunicipalityCatalogsGift before applying a GiftName CONTAINS candidate filter. Resolve exactly one stable GiftId before Supplier or Donation traversal. SQL joins: CategoryId supports GiftInCategory; MunicipalityId supports MunicipalityCatalogsGift.
</p>

<p><strong>レコード 57</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftId<br>
<strong>説明:</strong> Stable numeric identifier for one Gift catalog entity. Use it to connect Donations, catalog Municipalities, categories, and registered Suppliers.
</p>

<p><strong>レコード 58</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftName<br>
<strong>説明:</strong> Core Japanese product or service name of the return-gift option (返礼品名／お礼品名／商品名). It usually opens with a place-of-origin word such as a prefecture name, which is display text and not authoritative geography. For a Municipality-qualified colloquial label, traverse MunicipalityCatalogsGift first, filter this property with CONTAINS on the core noun, and verify the remaining numeric and descriptive tokens. Core names can repeat, so resolve one stable GiftId before further traversal.
</p>

<p><strong>レコード 59</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftDisplayName<br>
<strong>説明:</strong> Canonical human-readable municipality-qualified catalog label copied from the source Gift name before the core GiftName is derived. Use it for exact full-label resolution and GiftId as the stable identity.
</p>

<p><strong>レコード 60</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftSearchTerms<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftSearchTerms<br>
<strong>説明:</strong> Normalized search-only text for resolving shortened or colloquial Gift wording. It contains the Gift name, catalog Municipality, Prefecture, and GiftId with whitespace and punctuation removed. Filter it with every distinctive noun and numeric token supplied by the user; never display, group, count, or treat it as Gift identity.
</p>

<p><strong>レコード 61</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftNotes<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftNotes<br>
<strong>説明:</strong> Japanese free-text note, notes, remarks, or description for the return-gift option (備考／注意事項／説明). Notes are descriptive only and do not define Supplier, recipient geography, category, or monetary amount.
</p>

<p><strong>レコード 62</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftStaticCount<br>
<strong>説明:</strong> Authoritative pre-aggregated count of static Donations that selected this Gift. After resolving one GiftId, use this property directly for an all-time Gift count; do not join Suppliers or recount Donation detail.
</p>

<p><strong>レコード 63</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftStaticTotalYen<br>
<strong>説明:</strong> Authoritative pre-aggregated JPY amount of static Donations that selected this Gift. After resolving one GiftId, use this property directly for an all-time Gift total; do not join Suppliers or use SUM(DISTINCT DonationAmountYen).
</p>

<p><strong>レコード 64</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftAmountRank<br>
<strong>説明:</strong> Static donation-amount rank of this Gift across all Gifts. Deterministic row-number rank (row_number) over GiftStaticTotalYen desc, GiftId asc: equal amounts never share a rank because GiftId breaks the tie ascending.
</p>

<p><strong>レコード 65</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryId<br>
<strong>説明:</strong> Foreign key used by GiftInCategory.
</p>

<p><strong>レコード 66</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityId<br>
<strong>説明:</strong> Foreign key used by MunicipalityCatalogsGift.
</p>

<p><strong>レコード 67</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_supplier<br>
<strong>説明:</strong> Synthetic workshop business that may provide zero or more return-gift options (返礼品提供事業者). It is neither the Donation recipient nor a Donor; location is defined by SupplierInPrefecture. SQL joins: PrefectureId supports SupplierInPrefecture.
</p>

<p><strong>レコード 68</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierId<br>
<strong>説明:</strong> Stable numeric identifier for one synthetic registered Supplier entity. It identifies a catalog provider, not an actual fulfillment event.
</p>

<p><strong>レコード 69</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierName<br>
<strong>説明:</strong> Synthetic Japanese organization-style name of the Supplier or vendor (事業者名／提供事業者名). It is not a Donation recipient.
</p>

<p><strong>レコード 70</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierDisplayName<br>
<strong>説明:</strong> Display-only composite of SupplierName and SupplierId. Use SupplierId for identity and this property for human-readable output.
</p>

<p><strong>レコード 71</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierType<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierType<br>
<strong>説明:</strong> Japanese controlled supplier classification or business-type label (事業者種別／事業者区分) for the Supplier or vendor. It describes the provider, not the Gift category or Donation recipient.
</p>

<p><strong>レコード 72</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierTypeEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierTypeEn<br>
<strong>説明:</strong> Canonical English business-type label for SupplierType. Use it for English filtering and grouping; it describes the provider and not the Gift category or Donation recipient.
</p>

<p><strong>レコード 73</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierProvidedGiftCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierProvidedGiftCount<br>
<strong>説明:</strong> Count of distinct Gifts linked to this Supplier in the registered catalog; it is not a Donation or fulfillment metric.
</p>

<p><strong>レコード 74</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureId<br>
<strong>説明:</strong> Foreign key used by SupplierInPrefecture.
</p>

<p><strong>レコード 75</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_donation<br>
<strong>説明:</strong> Synthetic static baseline hometown-tax Donation row (ふるさと納税の寄付／寄附) and the only static fact grain for transaction counts and JPY amounts. It is an independent snapshot, not an approved, promoted, deduplicated, or finalized form of an Eventhouse observation. Each entity links to exactly one Donor, one recipient Municipality, and one selected Gift option in this dataset. SQL joins: DonorId supports DonorMadeDonation; MunicipalityId supports DonationToMunicipality; GiftId supports DonationSelectedGift.
</p>

<p><strong>レコード 76</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationId<br>
<strong>説明:</strong> Stable numeric identifier for one static Donation transaction. When a user says 寄付ID or Donation ID followed by a number, filter this property for exact identity; never reinterpret that number as DonationAmountYen. It is the transaction key and must not be used as a grouping dimension for an overall aggregate.
</p>

<p><strong>レコード 77</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationDisplayName<br>
<strong>説明:</strong> Display-only label in the format Donation followed by DonationId. Use DonationId for identity.
</p>

<p><strong>レコード 78</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationAmountYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationAmountYen<br>
<strong>説明:</strong> Completed donation amount (寄付金額／寄附金額／納税額) in whole Japanese yen for exactly one static Donation. SUM this property for donation totals and never sum IDs or Municipality time-series observations into the same result.
</p>

<p><strong>レコード 79</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonatedAtUtc<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonatedAtUtc<br>
<strong>説明:</strong> Canonical UTC timestamp of the static baseline Donation. Use it for exact sorting, filtering, minimum, maximum, and deterministic latest-record selection.
</p>

<p><strong>レコード 80</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonatedAtJstText<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonatedAtJstText<br>
<strong>説明:</strong> Display-only representation of DonatedAtUtc in Japan Standard Time (日本時間). Do not use this string for chronological sorting when DonatedAtUtc is available.
</p>

<p><strong>レコード 81</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationDateJst<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationDateJst<br>
<strong>説明:</strong> Japan Standard Time calendar date of the Donation (寄付日／寄附日). Use it for local-day filtering and grouping, not for exact timestamp ordering.
</p>

<p><strong>レコード 82</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationYearMonthJst<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationYearMonthJst<br>
<strong>説明:</strong> Japan Standard Time calendar year and month of the Donation (寄付年月／寄附年月). Use it for local-month filtering and grouping. Normalize an unambiguous Japanese two-digit Gregorian year such as 25年 to 2025 before matching the stored yyyy-MM value.
</p>

<p><strong>レコード 83</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationYearMonthJaShort<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationYearMonthJaShort<br>
<strong>説明:</strong> Japanese short Gregorian year-month label for the Donation, formatted yyyy年M月, such as 2025年1月. Use it only when the user supplies that short Japanese month wording; DonationYearMonthJst remains the canonical yyyy-MM calendar key.
</p>

<p><strong>レコード 84</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationPaymentMethod<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationPaymentMethod<br>
<strong>説明:</strong> Stored payment method, payment channel, checkout channel, or tender label (支払方法／決済方法／決済手段) for the completed Donation. It is a controlled Japanese-or-brand label and must not be interpreted as a Supplier.
</p>

<p><strong>レコード 85</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationPaymentMethodEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationPaymentMethodEn<br>
<strong>説明:</strong> Canonical English payment-method label for DonationPaymentMethod. Use it for English filtering and grouping; return both labels when the user asks for a translation.
</p>

<p><strong>レコード 86</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationDataLayer<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonationDataLayer<br>
<strong>説明:</strong> Canonical layer label for this detail entity. Its only value is StaticSyntheticSnapshot, which is not a payment method or time-series event type.
</p>

<p><strong>レコード 87</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonorId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> DonorId<br>
<strong>説明:</strong> Foreign key used by DonorMadeDonation.
</p>

<p><strong>レコード 88</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityId<br>
<strong>説明:</strong> Foreign key used by DonationToMunicipality.
</p>

<p><strong>レコード 89</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / GiftId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftId<br>
<strong>説明:</strong> Foreign key used by DonationSelectedGift.
</p>

<p><strong>レコード 90</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_mun_category_metric<br>
<strong>説明:</strong> Pre-aggregated current-static-snapshot metric for one Municipality and one GiftCategory pair with at least one Donation. It excludes time-series observations and Suppliers; values must not be summed again outside this grain. SQL joins: MunicipalityId supports MunHasCategoryMetric; CategoryId supports MunMetricForCategory.
</p>

<p><strong>レコード 91</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryMetricId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunCategoryMetricId<br>
<strong>説明:</strong> Synthetic stable identifier for one Municipality x GiftCategory snapshot metric row. The measure values are separate properties on this entity.
</p>

<p><strong>レコード 92</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunCategoryStaticCount<br>
<strong>説明:</strong> Pre-aggregated static Donation count for one Municipality x GiftCategory pair.
</p>

<p><strong>レコード 93</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunCategoryTotalYen<br>
<strong>説明:</strong> Pre-aggregated static Donation amount for one Municipality x GiftCategory pair.
</p>

<p><strong>レコード 94</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunCategoryAmountRank<br>
<strong>説明:</strong> Amount rank of this GiftCategory inside one Municipality. Deterministic row-number rank (row_number) over MunCategoryTotalYen desc, CategoryId asc within each MunicipalityId: equal amounts never share a rank because CategoryId breaks the tie ascending.
</p>

<p><strong>レコード 95</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityId<br>
<strong>説明:</strong> Foreign key used by MunHasCategoryMetric.
</p>

<p><strong>レコード 96</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryId<br>
<strong>説明:</strong> Foreign key used by MunMetricForCategory.
</p>

<p><strong>レコード 97</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_pref_category_metric<br>
<strong>説明:</strong> Pre-aggregated current-static-snapshot metric for one recipient Prefecture and one GiftCategory pair with at least one Donation. It excludes time-series observations and Suppliers; values must not be summed again outside this grain. SQL joins: PrefectureId supports PrefHasCategoryMetric; CategoryId supports PrefMetricForCategory.
</p>

<p><strong>レコード 98</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryMetricId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefCategoryMetricId<br>
<strong>説明:</strong> Synthetic stable identifier for one recipient Prefecture x GiftCategory snapshot metric row. The measure values are separate properties on this entity.
</p>

<p><strong>レコード 99</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefCategoryStaticCount<br>
<strong>説明:</strong> Pre-aggregated static Donation count for one recipient Prefecture x GiftCategory pair.
</p>

<p><strong>レコード 100</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefCategoryTotalYen<br>
<strong>説明:</strong> Pre-aggregated static Donation amount for one recipient Prefecture x GiftCategory pair.
</p>

<p><strong>レコード 101</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefCategoryAmountRank<br>
<strong>説明:</strong> Amount rank of this GiftCategory inside one recipient Prefecture. Deterministic row-number rank (row_number) over PrefCategoryTotalYen desc, CategoryId asc within each PrefectureId: equal amounts never share a rank because CategoryId breaks the tie ascending.
</p>

<p><strong>レコード 102</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureId<br>
<strong>説明:</strong> Foreign key used by PrefHasCategoryMetric.
</p>

<p><strong>レコード 103</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> CategoryId<br>
<strong>説明:</strong> Foreign key used by PrefMetricForCategory.
</p>

<p><strong>レコード 104</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_pref_donation_flow<br>
<strong>説明:</strong> Pre-aggregated current-static-snapshot flow from Donor residence Prefecture to Donation recipient Prefecture. Origin and destination are not interchangeable. It excludes time-series observations and Suppliers. SQL joins: ResidencePrefectureId supports ResidencePrefHasFlow; RecipientPrefectureId supports FlowToRecipientPref.
</p>

<p><strong>レコード 105</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefDonationFlowId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefDonationFlowId<br>
<strong>説明:</strong> Synthetic stable identifier for one donor-residence Prefecture x recipient Prefecture snapshot flow row. Directional measures are separate properties.
</p>

<p><strong>レコード 106</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefFlowStaticCount<br>
<strong>説明:</strong> Pre-aggregated count of static Donations from one residence Prefecture to one recipient Prefecture.
</p>

<p><strong>レコード 107</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefFlowTotalYen<br>
<strong>説明:</strong> Pre-aggregated JPY amount from one residence Prefecture to one recipient Prefecture.
</p>

<p><strong>レコード 108</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowOriginRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefFlowOriginRank<br>
<strong>説明:</strong> Amount rank of this recipient Prefecture among the destinations of one donor-residence Prefecture: the window is partitioned by the origin, so rank 1 is the destination that received the most from that origin. Deterministic row-number rank (row_number) over PrefFlowTotalYen desc, RecipientPrefectureId asc within each ResidencePrefectureId: equal amounts never share a rank because RecipientPrefectureId breaks the tie ascending.
</p>

<p><strong>レコード 109</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowDestinationRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefFlowDestinationRank<br>
<strong>説明:</strong> Amount rank of this donor-residence Prefecture among the origins of one recipient Prefecture: the window is partitioned by the destination, so rank 1 is the origin that sent the most to that destination. Deterministic row-number rank (row_number) over PrefFlowTotalYen desc, ResidencePrefectureId asc within each RecipientPrefectureId: equal amounts never share a rank because ResidencePrefectureId breaks the tie ascending.
</p>

<p><strong>レコード 110</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / ResidencePrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ResidencePrefectureId<br>
<strong>説明:</strong> Foreign key used by ResidencePrefHasFlow.
</p>

<p><strong>レコード 111</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / RecipientPrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> RecipientPrefectureId<br>
<strong>説明:</strong> Foreign key used by FlowToRecipientPref.
</p>

<p><strong>レコード 112</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier_gift<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> ot_supplier_gift<br>
<strong>説明:</strong> Many-to-many registered Supplier-to-Gift bridge. Never use it in Donation count or amount aggregation.
</p>

<p><strong>レコード 113</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier_gift / SupplierId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> SupplierId<br>
<strong>説明:</strong> Registered Supplier identifier; joins to ot_supplier.SupplierId.
</p>

<p><strong>レコード 114</strong><br>
<strong>論理ソース:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier_gift / GiftId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftId<br>
<strong>説明:</strong> Registered Gift identifier; joins to ot_gift.GiftId.
</p>

<p><strong>レコード 115</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> Prefecture<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Prefecture<br>
<strong>説明:</strong> PrefectureId,PrefectureName,PrefectureNameEn,PrefReceivedStaticCount,PrefReceivedTotalYen,PrefReceivedAmountRank,PrefResidentStaticCount,PrefResidentTotalYen,PrefResidentAmountRank
</p>

<p><strong>レコード 116</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> Municipality<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Municipality<br>
<strong>説明:</strong> MunicipalityId,MunicipalityName,MunicipalityDisplayName,MunicipalityStaticCount,MunicipalityStaticTotalYen,MunicipalityAmountRank,MunicipalityPrefAmountRank
</p>

<p><strong>レコード 117</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> Donor<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Donor<br>
<strong>説明:</strong> DonorId,DonorName,DonorDisplayName,DonorAge,DonorOccupation,DonorOccupationEn,DonorStaticCount,DonorStaticTotalYen,DonorStaticMaxYen,DonorOverallAmountRank,DonorResidenceAmountRank
</p>

<p><strong>レコード 118</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> GiftCategory<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> GiftCategory<br>
<strong>説明:</strong> CategoryId,CategoryName,CategoryNameEn,CategorySearchTerms,CategoryStaticCount,CategoryStaticTotalYen,CategoryAmountRank
</p>

<p><strong>レコード 119</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> Gift<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Gift<br>
<strong>説明:</strong> GiftId,GiftName,GiftDisplayName,GiftSearchTerms,GiftNotes,GiftStaticCount,GiftStaticTotalYen,GiftAmountRank
</p>

<p><strong>レコード 120</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> Supplier<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Supplier<br>
<strong>説明:</strong> SupplierId,SupplierName,SupplierDisplayName,SupplierType,SupplierTypeEn,SupplierProvidedGiftCount
</p>

<p><strong>レコード 121</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> Donation<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> Donation<br>
<strong>説明:</strong> DonationId,DonationDisplayName,DonationAmountYen,DonatedAtUtc,DonatedAtJstText,DonationDateJst,DonationYearMonthJst,DonationYearMonthJaShort,DonationPaymentMethod,DonationPaymentMethodEn,DonationDataLayer
</p>

<p><strong>レコード 122</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> MunicipalityCategoryMetric<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> MunicipalityCategoryMetric<br>
<strong>説明:</strong> MunCategoryMetricId,MunCategoryStaticCount,MunCategoryTotalYen,MunCategoryAmountRank
</p>

<p><strong>レコード 123</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> PrefectureCategoryMetric<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureCategoryMetric<br>
<strong>説明:</strong> PrefCategoryMetricId,PrefCategoryStaticCount,PrefCategoryTotalYen,PrefCategoryAmountRank
</p>

<p><strong>レコード 124</strong><br>
<strong>論理ソース:</strong> ontology<br>
<strong>Semantic path:</strong> PrefectureDonationFlow<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> PrefectureDonationFlow<br>
<strong>説明:</strong> PrefDonationFlowId,PrefFlowStaticCount,PrefFlowTotalYen,PrefFlowOriginRank,PrefFlowDestinationRank
</p>

<p><strong>レコード 125</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 126</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 静的寄附総額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 静的寄附総額<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 127</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 静的寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 静的寄附件数<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 128</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 受入増分寄附総額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 受入増分寄附総額<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 129</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 受入増分寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 受入増分寄附件数<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 130</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附総額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附総額<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 131</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附件数<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 132</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 平均寄附額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 平均寄附額<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 133</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附総額 前年同期間<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附総額 前年同期間<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 134</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 自治体別シェア (%)<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 自治体別シェア (%)<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 135</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 高額寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 高額寄附件数<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 136</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 137</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附金額<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附金額<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 138</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附日時 UTC<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附日時 UTC<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 139</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附日<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附日<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 140</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 決済方法<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 決済方法<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 141</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / データソース<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> データソース<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 142</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 高額寄附フラグ<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 高額寄附フラグ<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 143</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附者ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附者ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 144</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 自治体ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 自治体ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 145</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 返礼品ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 返礼品ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 146</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附者<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 147</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 寄附者ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附者ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 148</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 寄附者名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附者名<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 149</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 寄附者表示名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附者表示名<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 150</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 年齢<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 年齢<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 151</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 職業<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 職業<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 152</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 居住都道府県<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 居住都道府県<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 153</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 日付<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 154</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 日付キー<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 日付キー<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 155</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 日付<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 日付<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 156</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 年<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 年<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 157</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 四半期<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 四半期<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 158</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 月番号<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 月番号<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 159</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 月<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 月<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 160</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 年月<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 年月<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 161</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 自治体<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 162</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 自治体ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 自治体ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 163</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 自治体名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 自治体名<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 164</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 自治体表示名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 自治体表示名<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 165</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 寄附先都道府県<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 寄附先都道府県<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 166</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 返礼品<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 167</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / 返礼品ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 返礼品ID<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 168</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / 返礼品名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 返礼品名<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 169</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / 返礼品表示名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> 返礼品表示名<br>
<strong>説明:</strong>
</p>

<p><strong>レコード 170</strong><br>
<strong>論理ソース:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / カテゴリ<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>表示名:</strong> カテゴリ<br>
<strong>説明:</strong>
</p>

<details>
<summary>English</summary>

## 17.7 Read the current agent and selection contract

Resolve ID-only bindings from the existing agent's live definition and compare them with path, type and is_selected in selection-contract.json. Only selections listed in the asset are in scope. Stop on missing, ambiguous or unexpected differences. Do not reselect parent items to expand children or invent IDs.

**Actual flat selection contract**

**Readable field list — source order from `workshop/v3.0.0-preview/data-agent/profiles/current-experimental/selection-contract.json`**

<p><strong>Record 1</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views<br>
<strong>Type:</strong> kusto<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Materialized Views<br>
<strong>Description:</strong> Selected Eventhouse KQL materialized views.
</p>

<p><strong>Record 2</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent<br>
<strong>Type:</strong> kusto.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationObservationSummaryForAgent<br>
<strong>Description:</strong> Curated operational aggregates that exclude Donation, Donor, Gift, Supplier, payment, fulfillment, approval, deduplication, and lifecycle identifiers or state.
</p>

<p><strong>Record 3</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / MunicipalityID<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityID<br>
<strong>Description:</strong> Recipient Municipality identifier for the grouped operational observations.
</p>

<p><strong>Record 4</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / EventMinute<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> EventMinute<br>
<strong>Description:</strong> One-minute time bucket for the grouped operational observations.
</p>

<p><strong>Record 5</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / WorkshopRunId<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> WorkshopRunId<br>
<strong>Description:</strong> Unique workshop publication run identifier.
</p>

<p><strong>Record 6</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / ParticipantAlias<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ParticipantAlias<br>
<strong>Description:</strong> Short participant alias for the workshop run.
</p>

<p><strong>Record 7</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / SourceFile<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SourceFile<br>
<strong>Description:</strong> Workshop publisher or source-file label.
</p>

<p><strong>Record 8</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / ObservationCount<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ObservationCount<br>
<strong>Description:</strong> Number of operational observations represented by this aggregate row; sum this column for observation totals.
</p>

<p><strong>Record 9</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / ObservedAmountYen<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ObservedAmountYen<br>
<strong>Description:</strong> Total incoming observed amount in Japanese yen represented by this aggregate row; sum this column for amount totals.
</p>

<p><strong>Record 10</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / FirstObservedAt<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> FirstObservedAt<br>
<strong>Description:</strong> Earliest operational event timestamp represented by this aggregate row.
</p>

<p><strong>Record 11</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / LastObservedAt<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> LastObservedAt<br>
<strong>Description:</strong> Latest operational event timestamp represented by this aggregate row.
</p>

<p><strong>Record 12</strong><br>
<strong>Source kind:</strong> kusto<br>
<strong>Semantic path:</strong> Materialized Views / DonationObservationSummaryForAgent / LastPublishedAtUtc<br>
<strong>Type:</strong> kusto.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> LastPublishedAtUtc<br>
<strong>Description:</strong> Latest UTC timestamp when the workshop publisher sent an observation represented by this aggregate row.
</p>

<p><strong>Record 13</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas<br>
<strong>Type:</strong> schema_grouping<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Schemas<br>
<strong>Description:</strong>
</p>

<p><strong>Record 14</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo<br>
<strong>Type:</strong> lakehouse_tables.schema<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> dbo<br>
<strong>Description:</strong> Curated Furusato static snapshot tables.
</p>

<p><strong>Record 15</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables<br>
<strong>Type:</strong> table_grouping<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Tables<br>
<strong>Description:</strong>
</p>

<p><strong>Record 16</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_prefecture<br>
<strong>Description:</strong> Japanese prefecture (都道府県) used in two separate geography paths: recipient geography through Municipality and donor-residence geography through Donor. It is a reference dimension, not a Donation fact grain.
</p>

<p><strong>Record 17</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureId<br>
<strong>Description:</strong> Stable numeric identifier for one Japanese Prefecture entity. Use it to disambiguate names and as the relationship key; do not aggregate it. If the user explicitly asks for a 都道府県 or Prefecture result, keep this grain and never substitute a Municipality.
</p>

<p><strong>Record 18</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefectureName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureName<br>
<strong>Description:</strong> Official Japanese display label of the prefecture (都道府県名). Preserve the exact stored Japanese text in output.
</p>

<p><strong>Record 19</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefectureNameEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureNameEn<br>
<strong>Description:</strong> Canonical English label of the prefecture. Use it for English lookup and display; PrefectureId remains the identity.
</p>

<p><strong>Record 20</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefReceivedStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefReceivedStaticCount<br>
<strong>Description:</strong> Pre-aggregated count of static Donations received by municipalities in this Prefecture.
</p>

<p><strong>Record 21</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefReceivedTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefReceivedTotalYen<br>
<strong>Description:</strong> Pre-aggregated JPY amount received by municipalities in this Prefecture.
</p>

<p><strong>Record 22</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefReceivedAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefReceivedAmountRank<br>
<strong>Description:</strong> Received-amount rank of this Prefecture across all Prefectures. Deterministic row-number rank (row_number) over PrefReceivedTotalYen desc, PrefectureId asc: equal amounts never share a rank because PrefectureId breaks the tie ascending.
</p>

<p><strong>Record 23</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefResidentStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefResidentStaticCount<br>
<strong>Description:</strong> Pre-aggregated count of static Donations made by Donors who live in this Prefecture.
</p>

<p><strong>Record 24</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefResidentTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefResidentTotalYen<br>
<strong>Description:</strong> Pre-aggregated JPY amount donated by Donors who live in this Prefecture.
</p>

<p><strong>Record 25</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_prefecture / PrefResidentAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefResidentAmountRank<br>
<strong>Description:</strong> Resident-amount rank of this Prefecture across all Prefectures. Deterministic row-number rank (row_number) over PrefResidentTotalYen desc, PrefectureId asc: equal amounts never share a rank because PrefectureId breaks the tie ascending.
</p>

<p><strong>Record 26</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_municipality<br>
<strong>Description:</strong> Japanese municipality (自治体／市区町村) that may receive zero or more Donations. It also keys operational time-series observations; those observations are not Donation entities and have no Donor, Gift, or Supplier identity. SQL joins: PrefectureId supports MunicipalityInPrefecture.
</p>

<p><strong>Record 27</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityId<br>
<strong>Description:</strong> Stable identifier for one Municipality entity. Preserve leading zeros if present and use it as the relationship key; do not aggregate it.
</p>

<p><strong>Record 28</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityName<br>
<strong>Description:</strong> Japanese municipality name (自治体名／市区町村名) without a prefecture qualifier. Names are not globally unique, so include MunicipalityId or MunicipalityDisplayName when ambiguity is possible.
</p>

<p><strong>Record 29</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityDisplayName<br>
<strong>Description:</strong> Display-only composite label in the format MunicipalityName, PrefectureName, and MunicipalityId. Use MunicipalityId as the identity and this property only for unambiguous human-readable output.
</p>

<p><strong>Record 30</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityStaticCount<br>
<strong>Description:</strong> Pre-aggregated count of static Donations received by this Municipality.
</p>

<p><strong>Record 31</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityStaticTotalYen<br>
<strong>Description:</strong> Pre-aggregated static Donation amount received by this Municipality in JPY.
</p>

<p><strong>Record 32</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityAmountRank<br>
<strong>Description:</strong> Received-amount rank of this Municipality across all Municipalities. Deterministic row-number rank (row_number) over MunicipalityStaticTotalYen desc, MunicipalityId asc: equal amounts never share a rank because MunicipalityId breaks the tie ascending.
</p>

<p><strong>Record 33</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / MunicipalityPrefAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityPrefAmountRank<br>
<strong>Description:</strong> Received-amount rank of this Municipality inside its containing Prefecture. Deterministic row-number rank (row_number) over MunicipalityStaticTotalYen desc, MunicipalityId asc within each PrefectureId: equal amounts never share a rank because MunicipalityId breaks the tie ascending.
</p>

<p><strong>Record 34</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_municipality / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureId<br>
<strong>Description:</strong> Foreign key used by MunicipalityInPrefecture.
</p>

<p><strong>Record 35</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_donor<br>
<strong>Description:</strong> Synthetic workshop donor (寄付者／寄附者) who may make zero or more Donations. Residence is defined only by DonorLivesInPrefecture and must never be interpreted as recipient geography. SQL joins: PrefectureId supports DonorLivesInPrefecture.
</p>

<p><strong>Record 36</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorId<br>
<strong>Description:</strong> Stable numeric identifier for one synthetic Donor entity. Names aren't guaranteed unique, so use this ID to disambiguate people.
</p>

<p><strong>Record 37</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorName<br>
<strong>Description:</strong> Synthetic Japanese personal-style name of the donor (寄付者名／支援者名). It is not guaranteed to be unique and does not represent a real person.
</p>

<p><strong>Record 38</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorDisplayName<br>
<strong>Description:</strong> Display-only composite of DonorName and DonorId. Use DonorId for identity and this property for human-readable output.
</p>

<p><strong>Record 39</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorAge<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorAge<br>
<strong>Description:</strong> Whole-year age of the synthetic donor (年齢) in the static donor record. It is not derived from the Donation timestamp and must not be summed.
</p>

<p><strong>Record 40</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorOccupation<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorOccupation<br>
<strong>Description:</strong> Japanese controlled occupation or job label (職業／職種／仕事) for the synthetic donor. It describes the donor's job category, not employer, recipient, or Supplier type.
</p>

<p><strong>Record 41</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorOccupationEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorOccupationEn<br>
<strong>Description:</strong> Canonical English occupation label for DonorOccupation. Use it for English filtering and grouping; preserve DonorOccupation when returning the stored Japanese label.
</p>

<p><strong>Record 42</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorStaticCount<br>
<strong>Description:</strong> Pre-aggregated number of static Donations made by this Donor.
</p>

<p><strong>Record 43</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorStaticTotalYen<br>
<strong>Description:</strong> Pre-aggregated cumulative static Donation amount made by this Donor in JPY.
</p>

<p><strong>Record 44</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorStaticMaxYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorStaticMaxYen<br>
<strong>Description:</strong> Maximum single static Donation amount made by this Donor in JPY; it is not the cumulative amount.
</p>

<p><strong>Record 45</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorOverallAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorOverallAmountRank<br>
<strong>Description:</strong> Cumulative static donation-amount rank of this Donor nationwide. Deterministic row-number rank (row_number) over DonorStaticTotalYen desc, DonorId asc: equal amounts never share a rank because DonorId breaks the tie ascending.
</p>

<p><strong>Record 46</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / DonorResidenceAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorResidenceAmountRank<br>
<strong>Description:</strong> Cumulative static donation-amount rank of this Donor inside the residence Prefecture. Deterministic row-number rank (row_number) over DonorStaticTotalYen desc, DonorId asc within each PrefectureId: equal amounts never share a rank because DonorId breaks the tie ascending.
</p>

<p><strong>Record 47</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donor / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureId<br>
<strong>Description:</strong> Foreign key used by DonorLivesInPrefecture.
</p>

<p><strong>Record 48</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_gift_category<br>
<strong>Description:</strong> Controlled classification of return-gift options (返礼品カテゴリ). Category counts and amounts must be aggregated from Donation through DonationSelectedGift and GiftInCategory; the category itself is not a transaction fact.
</p>

<p><strong>Record 49</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryId<br>
<strong>Description:</strong> Stable numeric identifier for one GiftCategory entity. Use it with the stored category labels and never sum or average it.
</p>

<p><strong>Record 50</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryName<br>
<strong>Description:</strong> Canonical Japanese return-gift category label (返礼品カテゴリ／返礼品分類). Category metrics must be calculated from Donation, not from this label.
</p>

<p><strong>Record 51</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryNameEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryNameEn<br>
<strong>Description:</strong> Canonical English return-gift category label paired one-to-one with CategoryName. Use it for English filtering, grouping, and display; CategoryId remains the identity.
</p>

<p><strong>Record 52</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategorySearchTerms<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategorySearchTerms<br>
<strong>Description:</strong> Lowercase pipe-delimited Japanese and English aliases with leading and trailing boundary pipes, used only to resolve colloquial return-gift category wording such as 海鮮系, 魚介, seafood, or equivalent bounded terms. If CategoryName does not match, query this alias index before claiming no category data. Never display, group, count, or treat this property as the category identity.
</p>

<p><strong>Record 53</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryStaticCount<br>
<strong>Description:</strong> Pre-aggregated static Donation count for this GiftCategory across the full snapshot.
</p>

<p><strong>Record 54</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryStaticTotalYen<br>
<strong>Description:</strong> Pre-aggregated static Donation amount for this GiftCategory across the full snapshot.
</p>

<p><strong>Record 55</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift_category / CategoryAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryAmountRank<br>
<strong>Description:</strong> Static donation-amount rank of this GiftCategory across all GiftCategories. Deterministic row-number rank (row_number) over CategoryStaticTotalYen desc, CategoryId asc: equal amounts never share a rank because CategoryId breaks the tie ascending.
</p>

<p><strong>Record 56</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_gift<br>
<strong>Description:</strong> Synthetic return-gift option selected by a Donation (返礼品／お礼品／商品). It is a catalog dimension, not the donated money and not a transaction fact. If a Municipality is named, resolve that Municipality and traverse MunicipalityCatalogsGift before applying a GiftName CONTAINS candidate filter. Resolve exactly one stable GiftId before Supplier or Donation traversal. SQL joins: CategoryId supports GiftInCategory; MunicipalityId supports MunicipalityCatalogsGift.
</p>

<p><strong>Record 57</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftId<br>
<strong>Description:</strong> Stable numeric identifier for one Gift catalog entity. Use it to connect Donations, catalog Municipalities, categories, and registered Suppliers.
</p>

<p><strong>Record 58</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftName<br>
<strong>Description:</strong> Core Japanese product or service name of the return-gift option (返礼品名／お礼品名／商品名). It usually opens with a place-of-origin word such as a prefecture name, which is display text and not authoritative geography. For a Municipality-qualified colloquial label, traverse MunicipalityCatalogsGift first, filter this property with CONTAINS on the core noun, and verify the remaining numeric and descriptive tokens. Core names can repeat, so resolve one stable GiftId before further traversal.
</p>

<p><strong>Record 59</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftDisplayName<br>
<strong>Description:</strong> Canonical human-readable municipality-qualified catalog label copied from the source Gift name before the core GiftName is derived. Use it for exact full-label resolution and GiftId as the stable identity.
</p>

<p><strong>Record 60</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftSearchTerms<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftSearchTerms<br>
<strong>Description:</strong> Normalized search-only text for resolving shortened or colloquial Gift wording. It contains the Gift name, catalog Municipality, Prefecture, and GiftId with whitespace and punctuation removed. Filter it with every distinctive noun and numeric token supplied by the user; never display, group, count, or treat it as Gift identity.
</p>

<p><strong>Record 61</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftNotes<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftNotes<br>
<strong>Description:</strong> Japanese free-text note, notes, remarks, or description for the return-gift option (備考／注意事項／説明). Notes are descriptive only and do not define Supplier, recipient geography, category, or monetary amount.
</p>

<p><strong>Record 62</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftStaticCount<br>
<strong>Description:</strong> Authoritative pre-aggregated count of static Donations that selected this Gift. After resolving one GiftId, use this property directly for an all-time Gift count; do not join Suppliers or recount Donation detail.
</p>

<p><strong>Record 63</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftStaticTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftStaticTotalYen<br>
<strong>Description:</strong> Authoritative pre-aggregated JPY amount of static Donations that selected this Gift. After resolving one GiftId, use this property directly for an all-time Gift total; do not join Suppliers or use SUM(DISTINCT DonationAmountYen).
</p>

<p><strong>Record 64</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / GiftAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftAmountRank<br>
<strong>Description:</strong> Static donation-amount rank of this Gift across all Gifts. Deterministic row-number rank (row_number) over GiftStaticTotalYen desc, GiftId asc: equal amounts never share a rank because GiftId breaks the tie ascending.
</p>

<p><strong>Record 65</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryId<br>
<strong>Description:</strong> Foreign key used by GiftInCategory.
</p>

<p><strong>Record 66</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_gift / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityId<br>
<strong>Description:</strong> Foreign key used by MunicipalityCatalogsGift.
</p>

<p><strong>Record 67</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_supplier<br>
<strong>Description:</strong> Synthetic workshop business that may provide zero or more return-gift options (返礼品提供事業者). It is neither the Donation recipient nor a Donor; location is defined by SupplierInPrefecture. SQL joins: PrefectureId supports SupplierInPrefecture.
</p>

<p><strong>Record 68</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierId<br>
<strong>Description:</strong> Stable numeric identifier for one synthetic registered Supplier entity. It identifies a catalog provider, not an actual fulfillment event.
</p>

<p><strong>Record 69</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierName<br>
<strong>Description:</strong> Synthetic Japanese organization-style name of the Supplier or vendor (事業者名／提供事業者名). It is not a Donation recipient.
</p>

<p><strong>Record 70</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierDisplayName<br>
<strong>Description:</strong> Display-only composite of SupplierName and SupplierId. Use SupplierId for identity and this property for human-readable output.
</p>

<p><strong>Record 71</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierType<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierType<br>
<strong>Description:</strong> Japanese controlled supplier classification or business-type label (事業者種別／事業者区分) for the Supplier or vendor. It describes the provider, not the Gift category or Donation recipient.
</p>

<p><strong>Record 72</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierTypeEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierTypeEn<br>
<strong>Description:</strong> Canonical English business-type label for SupplierType. Use it for English filtering and grouping; it describes the provider and not the Gift category or Donation recipient.
</p>

<p><strong>Record 73</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / SupplierProvidedGiftCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierProvidedGiftCount<br>
<strong>Description:</strong> Count of distinct Gifts linked to this Supplier in the registered catalog; it is not a Donation or fulfillment metric.
</p>

<p><strong>Record 74</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureId<br>
<strong>Description:</strong> Foreign key used by SupplierInPrefecture.
</p>

<p><strong>Record 75</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_donation<br>
<strong>Description:</strong> Synthetic static baseline hometown-tax Donation row (ふるさと納税の寄付／寄附) and the only static fact grain for transaction counts and JPY amounts. It is an independent snapshot, not an approved, promoted, deduplicated, or finalized form of an Eventhouse observation. Each entity links to exactly one Donor, one recipient Municipality, and one selected Gift option in this dataset. SQL joins: DonorId supports DonorMadeDonation; MunicipalityId supports DonationToMunicipality; GiftId supports DonationSelectedGift.
</p>

<p><strong>Record 76</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationId<br>
<strong>Description:</strong> Stable numeric identifier for one static Donation transaction. When a user says 寄付ID or Donation ID followed by a number, filter this property for exact identity; never reinterpret that number as DonationAmountYen. It is the transaction key and must not be used as a grouping dimension for an overall aggregate.
</p>

<p><strong>Record 77</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationDisplayName<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationDisplayName<br>
<strong>Description:</strong> Display-only label in the format Donation followed by DonationId. Use DonationId for identity.
</p>

<p><strong>Record 78</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationAmountYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationAmountYen<br>
<strong>Description:</strong> Completed donation amount (寄付金額／寄附金額／納税額) in whole Japanese yen for exactly one static Donation. SUM this property for donation totals and never sum IDs or Municipality time-series observations into the same result.
</p>

<p><strong>Record 79</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonatedAtUtc<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonatedAtUtc<br>
<strong>Description:</strong> Canonical UTC timestamp of the static baseline Donation. Use it for exact sorting, filtering, minimum, maximum, and deterministic latest-record selection.
</p>

<p><strong>Record 80</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonatedAtJstText<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonatedAtJstText<br>
<strong>Description:</strong> Display-only representation of DonatedAtUtc in Japan Standard Time (日本時間). Do not use this string for chronological sorting when DonatedAtUtc is available.
</p>

<p><strong>Record 81</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationDateJst<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationDateJst<br>
<strong>Description:</strong> Japan Standard Time calendar date of the Donation (寄付日／寄附日). Use it for local-day filtering and grouping, not for exact timestamp ordering.
</p>

<p><strong>Record 82</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationYearMonthJst<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationYearMonthJst<br>
<strong>Description:</strong> Japan Standard Time calendar year and month of the Donation (寄付年月／寄附年月). Use it for local-month filtering and grouping. Normalize an unambiguous Japanese two-digit Gregorian year such as 25年 to 2025 before matching the stored yyyy-MM value.
</p>

<p><strong>Record 83</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationYearMonthJaShort<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationYearMonthJaShort<br>
<strong>Description:</strong> Japanese short Gregorian year-month label for the Donation, formatted yyyy年M月, such as 2025年1月. Use it only when the user supplies that short Japanese month wording; DonationYearMonthJst remains the canonical yyyy-MM calendar key.
</p>

<p><strong>Record 84</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationPaymentMethod<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationPaymentMethod<br>
<strong>Description:</strong> Stored payment method, payment channel, checkout channel, or tender label (支払方法／決済方法／決済手段) for the completed Donation. It is a controlled Japanese-or-brand label and must not be interpreted as a Supplier.
</p>

<p><strong>Record 85</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationPaymentMethodEn<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationPaymentMethodEn<br>
<strong>Description:</strong> Canonical English payment-method label for DonationPaymentMethod. Use it for English filtering and grouping; return both labels when the user asks for a translation.
</p>

<p><strong>Record 86</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonationDataLayer<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonationDataLayer<br>
<strong>Description:</strong> Canonical layer label for this detail entity. Its only value is StaticSyntheticSnapshot, which is not a payment method or time-series event type.
</p>

<p><strong>Record 87</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / DonorId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> DonorId<br>
<strong>Description:</strong> Foreign key used by DonorMadeDonation.
</p>

<p><strong>Record 88</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityId<br>
<strong>Description:</strong> Foreign key used by DonationToMunicipality.
</p>

<p><strong>Record 89</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_donation / GiftId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftId<br>
<strong>Description:</strong> Foreign key used by DonationSelectedGift.
</p>

<p><strong>Record 90</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_mun_category_metric<br>
<strong>Description:</strong> Pre-aggregated current-static-snapshot metric for one Municipality and one GiftCategory pair with at least one Donation. It excludes time-series observations and Suppliers; values must not be summed again outside this grain. SQL joins: MunicipalityId supports MunHasCategoryMetric; CategoryId supports MunMetricForCategory.
</p>

<p><strong>Record 91</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryMetricId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunCategoryMetricId<br>
<strong>Description:</strong> Synthetic stable identifier for one Municipality x GiftCategory snapshot metric row. The measure values are separate properties on this entity.
</p>

<p><strong>Record 92</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunCategoryStaticCount<br>
<strong>Description:</strong> Pre-aggregated static Donation count for one Municipality x GiftCategory pair.
</p>

<p><strong>Record 93</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunCategoryTotalYen<br>
<strong>Description:</strong> Pre-aggregated static Donation amount for one Municipality x GiftCategory pair.
</p>

<p><strong>Record 94</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunCategoryAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunCategoryAmountRank<br>
<strong>Description:</strong> Amount rank of this GiftCategory inside one Municipality. Deterministic row-number rank (row_number) over MunCategoryTotalYen desc, CategoryId asc within each MunicipalityId: equal amounts never share a rank because CategoryId breaks the tie ascending.
</p>

<p><strong>Record 95</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / MunicipalityId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityId<br>
<strong>Description:</strong> Foreign key used by MunHasCategoryMetric.
</p>

<p><strong>Record 96</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_mun_category_metric / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryId<br>
<strong>Description:</strong> Foreign key used by MunMetricForCategory.
</p>

<p><strong>Record 97</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_pref_category_metric<br>
<strong>Description:</strong> Pre-aggregated current-static-snapshot metric for one recipient Prefecture and one GiftCategory pair with at least one Donation. It excludes time-series observations and Suppliers; values must not be summed again outside this grain. SQL joins: PrefectureId supports PrefHasCategoryMetric; CategoryId supports PrefMetricForCategory.
</p>

<p><strong>Record 98</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryMetricId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefCategoryMetricId<br>
<strong>Description:</strong> Synthetic stable identifier for one recipient Prefecture x GiftCategory snapshot metric row. The measure values are separate properties on this entity.
</p>

<p><strong>Record 99</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefCategoryStaticCount<br>
<strong>Description:</strong> Pre-aggregated static Donation count for one recipient Prefecture x GiftCategory pair.
</p>

<p><strong>Record 100</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefCategoryTotalYen<br>
<strong>Description:</strong> Pre-aggregated static Donation amount for one recipient Prefecture x GiftCategory pair.
</p>

<p><strong>Record 101</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefCategoryAmountRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefCategoryAmountRank<br>
<strong>Description:</strong> Amount rank of this GiftCategory inside one recipient Prefecture. Deterministic row-number rank (row_number) over PrefCategoryTotalYen desc, CategoryId asc within each PrefectureId: equal amounts never share a rank because CategoryId breaks the tie ascending.
</p>

<p><strong>Record 102</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / PrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureId<br>
<strong>Description:</strong> Foreign key used by PrefHasCategoryMetric.
</p>

<p><strong>Record 103</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_category_metric / CategoryId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> CategoryId<br>
<strong>Description:</strong> Foreign key used by PrefMetricForCategory.
</p>

<p><strong>Record 104</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_pref_donation_flow<br>
<strong>Description:</strong> Pre-aggregated current-static-snapshot flow from Donor residence Prefecture to Donation recipient Prefecture. Origin and destination are not interchangeable. It excludes time-series observations and Suppliers. SQL joins: ResidencePrefectureId supports ResidencePrefHasFlow; RecipientPrefectureId supports FlowToRecipientPref.
</p>

<p><strong>Record 105</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefDonationFlowId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefDonationFlowId<br>
<strong>Description:</strong> Synthetic stable identifier for one donor-residence Prefecture x recipient Prefecture snapshot flow row. Directional measures are separate properties.
</p>

<p><strong>Record 106</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowStaticCount<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefFlowStaticCount<br>
<strong>Description:</strong> Pre-aggregated count of static Donations from one residence Prefecture to one recipient Prefecture.
</p>

<p><strong>Record 107</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowTotalYen<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefFlowTotalYen<br>
<strong>Description:</strong> Pre-aggregated JPY amount from one residence Prefecture to one recipient Prefecture.
</p>

<p><strong>Record 108</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowOriginRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefFlowOriginRank<br>
<strong>Description:</strong> Amount rank of this recipient Prefecture among the destinations of one donor-residence Prefecture: the window is partitioned by the origin, so rank 1 is the destination that received the most from that origin. Deterministic row-number rank (row_number) over PrefFlowTotalYen desc, RecipientPrefectureId asc within each ResidencePrefectureId: equal amounts never share a rank because RecipientPrefectureId breaks the tie ascending.
</p>

<p><strong>Record 109</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / PrefFlowDestinationRank<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefFlowDestinationRank<br>
<strong>Description:</strong> Amount rank of this donor-residence Prefecture among the origins of one recipient Prefecture: the window is partitioned by the destination, so rank 1 is the origin that sent the most to that destination. Deterministic row-number rank (row_number) over PrefFlowTotalYen desc, ResidencePrefectureId asc within each RecipientPrefectureId: equal amounts never share a rank because ResidencePrefectureId breaks the tie ascending.
</p>

<p><strong>Record 110</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / ResidencePrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ResidencePrefectureId<br>
<strong>Description:</strong> Foreign key used by ResidencePrefHasFlow.
</p>

<p><strong>Record 111</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_pref_donation_flow / RecipientPrefectureId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> RecipientPrefectureId<br>
<strong>Description:</strong> Foreign key used by FlowToRecipientPref.
</p>

<p><strong>Record 112</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier_gift<br>
<strong>Type:</strong> lakehouse_tables.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> ot_supplier_gift<br>
<strong>Description:</strong> Many-to-many registered Supplier-to-Gift bridge. Never use it in Donation count or amount aggregation.
</p>

<p><strong>Record 113</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier_gift / SupplierId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> SupplierId<br>
<strong>Description:</strong> Registered Supplier identifier; joins to ot_supplier.SupplierId.
</p>

<p><strong>Record 114</strong><br>
<strong>Source kind:</strong> lakehouse_tables<br>
<strong>Semantic path:</strong> Schemas / dbo / Tables / ot_supplier_gift / GiftId<br>
<strong>Type:</strong> lakehouse_tables.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftId<br>
<strong>Description:</strong> Registered Gift identifier; joins to ot_gift.GiftId.
</p>

<p><strong>Record 115</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> Prefecture<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Prefecture<br>
<strong>Description:</strong> PrefectureId,PrefectureName,PrefectureNameEn,PrefReceivedStaticCount,PrefReceivedTotalYen,PrefReceivedAmountRank,PrefResidentStaticCount,PrefResidentTotalYen,PrefResidentAmountRank
</p>

<p><strong>Record 116</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> Municipality<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Municipality<br>
<strong>Description:</strong> MunicipalityId,MunicipalityName,MunicipalityDisplayName,MunicipalityStaticCount,MunicipalityStaticTotalYen,MunicipalityAmountRank,MunicipalityPrefAmountRank
</p>

<p><strong>Record 117</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> Donor<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Donor<br>
<strong>Description:</strong> DonorId,DonorName,DonorDisplayName,DonorAge,DonorOccupation,DonorOccupationEn,DonorStaticCount,DonorStaticTotalYen,DonorStaticMaxYen,DonorOverallAmountRank,DonorResidenceAmountRank
</p>

<p><strong>Record 118</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> GiftCategory<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> GiftCategory<br>
<strong>Description:</strong> CategoryId,CategoryName,CategoryNameEn,CategorySearchTerms,CategoryStaticCount,CategoryStaticTotalYen,CategoryAmountRank
</p>

<p><strong>Record 119</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> Gift<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Gift<br>
<strong>Description:</strong> GiftId,GiftName,GiftDisplayName,GiftSearchTerms,GiftNotes,GiftStaticCount,GiftStaticTotalYen,GiftAmountRank
</p>

<p><strong>Record 120</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> Supplier<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Supplier<br>
<strong>Description:</strong> SupplierId,SupplierName,SupplierDisplayName,SupplierType,SupplierTypeEn,SupplierProvidedGiftCount
</p>

<p><strong>Record 121</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> Donation<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> Donation<br>
<strong>Description:</strong> DonationId,DonationDisplayName,DonationAmountYen,DonatedAtUtc,DonatedAtJstText,DonationDateJst,DonationYearMonthJst,DonationYearMonthJaShort,DonationPaymentMethod,DonationPaymentMethodEn,DonationDataLayer
</p>

<p><strong>Record 122</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> MunicipalityCategoryMetric<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> MunicipalityCategoryMetric<br>
<strong>Description:</strong> MunCategoryMetricId,MunCategoryStaticCount,MunCategoryTotalYen,MunCategoryAmountRank
</p>

<p><strong>Record 123</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> PrefectureCategoryMetric<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureCategoryMetric<br>
<strong>Description:</strong> PrefCategoryMetricId,PrefCategoryStaticCount,PrefCategoryTotalYen,PrefCategoryAmountRank
</p>

<p><strong>Record 124</strong><br>
<strong>Source kind:</strong> ontology<br>
<strong>Semantic path:</strong> PrefectureDonationFlow<br>
<strong>Type:</strong> ontology.entity<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> PrefectureDonationFlow<br>
<strong>Description:</strong> PrefDonationFlowId,PrefFlowStaticCount,PrefFlowTotalYen,PrefFlowOriginRank,PrefFlowDestinationRank
</p>

<p><strong>Record 125</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附<br>
<strong>Description:</strong>
</p>

<p><strong>Record 126</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 静的寄附総額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 静的寄附総額<br>
<strong>Description:</strong>
</p>

<p><strong>Record 127</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 静的寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 静的寄附件数<br>
<strong>Description:</strong>
</p>

<p><strong>Record 128</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 受入増分寄附総額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 受入増分寄附総額<br>
<strong>Description:</strong>
</p>

<p><strong>Record 129</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 受入増分寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 受入増分寄附件数<br>
<strong>Description:</strong>
</p>

<p><strong>Record 130</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附総額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附総額<br>
<strong>Description:</strong>
</p>

<p><strong>Record 131</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附件数<br>
<strong>Description:</strong>
</p>

<p><strong>Record 132</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 平均寄附額<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 平均寄附額<br>
<strong>Description:</strong>
</p>

<p><strong>Record 133</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附総額 前年同期間<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附総額 前年同期間<br>
<strong>Description:</strong>
</p>

<p><strong>Record 134</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 自治体別シェア (%)<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 自治体別シェア (%)<br>
<strong>Description:</strong>
</p>

<p><strong>Record 135</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 高額寄附件数<br>
<strong>Type:</strong> semantic_model.measure<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 高額寄附件数<br>
<strong>Description:</strong>
</p>

<p><strong>Record 136</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 137</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附金額<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附金額<br>
<strong>Description:</strong>
</p>

<p><strong>Record 138</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附日時 UTC<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附日時 UTC<br>
<strong>Description:</strong>
</p>

<p><strong>Record 139</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附日<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附日<br>
<strong>Description:</strong>
</p>

<p><strong>Record 140</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 決済方法<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 決済方法<br>
<strong>Description:</strong>
</p>

<p><strong>Record 141</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / データソース<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> データソース<br>
<strong>Description:</strong>
</p>

<p><strong>Record 142</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 高額寄附フラグ<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 高額寄附フラグ<br>
<strong>Description:</strong>
</p>

<p><strong>Record 143</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 寄附者ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附者ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 144</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 自治体ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 自治体ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 145</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附 / 返礼品ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 返礼品ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 146</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附者<br>
<strong>Description:</strong>
</p>

<p><strong>Record 147</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 寄附者ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附者ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 148</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 寄附者名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附者名<br>
<strong>Description:</strong>
</p>

<p><strong>Record 149</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 寄附者表示名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附者表示名<br>
<strong>Description:</strong>
</p>

<p><strong>Record 150</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 年齢<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 年齢<br>
<strong>Description:</strong>
</p>

<p><strong>Record 151</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 職業<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 職業<br>
<strong>Description:</strong>
</p>

<p><strong>Record 152</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 寄附者 / 居住都道府県<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 居住都道府県<br>
<strong>Description:</strong>
</p>

<p><strong>Record 153</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 日付<br>
<strong>Description:</strong>
</p>

<p><strong>Record 154</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 日付キー<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 日付キー<br>
<strong>Description:</strong>
</p>

<p><strong>Record 155</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 日付<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 日付<br>
<strong>Description:</strong>
</p>

<p><strong>Record 156</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 年<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 年<br>
<strong>Description:</strong>
</p>

<p><strong>Record 157</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 四半期<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 四半期<br>
<strong>Description:</strong>
</p>

<p><strong>Record 158</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 月番号<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 月番号<br>
<strong>Description:</strong>
</p>

<p><strong>Record 159</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 月<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 月<br>
<strong>Description:</strong>
</p>

<p><strong>Record 160</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 日付 / 年月<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 年月<br>
<strong>Description:</strong>
</p>

<p><strong>Record 161</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 自治体<br>
<strong>Description:</strong>
</p>

<p><strong>Record 162</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 自治体ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 自治体ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 163</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 自治体名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 自治体名<br>
<strong>Description:</strong>
</p>

<p><strong>Record 164</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 自治体表示名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 自治体表示名<br>
<strong>Description:</strong>
</p>

<p><strong>Record 165</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 自治体 / 寄附先都道府県<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 寄附先都道府県<br>
<strong>Description:</strong>
</p>

<p><strong>Record 166</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品<br>
<strong>Type:</strong> semantic_model.table<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 返礼品<br>
<strong>Description:</strong>
</p>

<p><strong>Record 167</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / 返礼品ID<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 返礼品ID<br>
<strong>Description:</strong>
</p>

<p><strong>Record 168</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / 返礼品名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 返礼品名<br>
<strong>Description:</strong>
</p>

<p><strong>Record 169</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / 返礼品表示名<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> 返礼品表示名<br>
<strong>Description:</strong>
</p>

<p><strong>Record 170</strong><br>
<strong>Source kind:</strong> semantic_model<br>
<strong>Semantic path:</strong> 返礼品 / カテゴリ<br>
<strong>Type:</strong> semantic_model.column<br>
<strong>is_selected:</strong> true<br>
<strong>Display name:</strong> カテゴリ<br>
<strong>Description:</strong>
</p>

</details>
