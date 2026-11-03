# 6.2 操作手順（1）

[Lab 目次](../README.md) · [この章の目次](README.md)

1. Home の Add entity type を選び、名前（例：Prefecture）を入力して Add Entity Type を選びます。Explorer で作成した Entity type を選び、View Entity Type details を開きます。
2. Configure に Manage property bindings が表示される場合はそれを開きます。表示されず Configure の toolbar に Bind data がある場合は Bind data を選びます。どちらの入口でも、画面に実際に表示されるコントロールだけを使います。新しい binding 画面や初回案内で、対象テーブル・キー・列を確認できない場合は作成・保存せず停止して講師に確認します。
3. Add binding and properties（Property が無い場合は Add properties from data）、Property binding の Add、Entity type properties が実際に表示される場合に限り、その画面で LH_Furusato_&lt;PID&gt; の対応テーブル（Prefecture なら ot_prefecture）と Property 名・元列・型（String または Integer）を照合します。Add shared property は選ばず、本章の表にある Local Property だけを確認します。Create と Entity type updated successfully が表示された場合は Cancel で閉じ、Configure を開き直して保存内容を読み戻します。これらの確認可能な項目や保存結果が画面にない場合は、変更せず講師に確認します。
4. Entity type key を設定します。キーは下の表のとおり、変わらない String または Integer の列にします。MunicipalityId は先頭のゼロを含む6桁の String です。キーの無い Entity type は Graph の対象になりません。
5. 残りの9つの Entity type も同じ手順で作ります。表の元テーブルと Property 数に合わせ、10の Entity type の静的 Property が合計72になることを確認します。
6. Municipality の時系列 Property（IncomingDonationAmountYen）は10章でバインドします。すでに定義されている場合、この時点では Data source が Unbound と表示されますが、正常です。

![Municipality の Properties 表。キー MunicipalityId、Local の各 Property の型と Data source（ot_municipality）、時系列 Property は Unbound](../assets/p30-06-entities.png)

Municipality の Configure 画面例。キーは MunicipalityId、静的 Property は ot_municipality にバインドされ、時系列 Property は10章で設定するまで Unbound です。自分の画面で表示される binding の入口を使います。

<details>
<summary>English</summary>

## 6.2 Steps

1. Select Add entity type on Home, enter a name (for example Prefecture) and select Add Entity Type. Select the new entity type in Explorer and open View Entity Type details.
2. If Configure shows Manage property bindings, open it. If that entry is absent and the Configure toolbar shows Bind data, select Bind data instead. Use only controls actually shown on screen. If a new binding screen or first-run tour does not let you verify the source table, key and columns, stop without creating or saving and ask the instructor.
3. Only when Add binding and properties (or Add properties from data when there are no properties), Property binding → Add, and Entity type properties are actually shown, use those controls to verify the matching LH_Furusato_&lt;PID&gt; table (ot_prefecture for Prefecture), property names, source columns and types (String or Integer). Do not select Add shared property; this chapter uses the Local properties listed in its table. If Create and Entity type updated successfully appear, close with Cancel and reopen Configure to read back the saved values. If the screen does not expose these verifiable fields or a saved result, make no change and ask the instructor.
4. Set the Entity type key. As the table shows, the key is a stable String or Integer column. MunicipalityId is a six-character String that includes leading zeros. An entity type without a key cannot be included in a graph.
5. Create the remaining nine entity types in the same way. Follow the source table and property count in the table, and confirm that the 10 entity types have 72 static properties in total.
6. The time-series property of Municipality (IncomingDonationAmountYen) is bound in Chapter 10. If it is already defined, its Data source shows Unbound at this point; that is expected.

![Municipality Properties table: key MunicipalityId, Local properties with their types bound to ot_municipality, and an Unbound time-series property.](../assets/p30-06-entities.png)

Municipality Configure example: MunicipalityId is the key, static properties are bound to ot_municipality, and the time-series property stays Unbound until Chapter 10. Use the binding entry shown in your own view.

</details>
