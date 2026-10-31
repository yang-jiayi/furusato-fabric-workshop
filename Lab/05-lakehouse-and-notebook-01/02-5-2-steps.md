# 5.2 操作手順

[Lab 目次](../README.md) · [この章の目次](README.md)

1. Lakehouse を開き、Files の下にフォルダーを作って、パスが Files/furusato/seed になるようにします（furusato フォルダーの中に、もう1つフォルダーを作ります）。ここに8つの CSV をアップロードします。8月の観測データ（donation_events_001〜003.csv）はここに置きません。
2. 続けて、Files の下に空の increment フォルダー（Files/increment）を作ります。9章でこのフォルダーへのファイルの到着を監視するため、今は何も置きません。
3. アップロードしたファイルのサイズを data フォルダーの dataset-manifest.json と比べ、8ファイルがそろっていることを確認します。
4. Notebook 01 を作業フォルダーにインポートし、LH_Furusato_&lt;PID&gt; を接続（attach）します。
5. 先頭のパラメーターセルで PARTICIPANT_ID を自分の &lt;PID&gt; に変更します。ほかの値は変更しません（INPUT_DIR は "Files/furusato/seed" のままにします）。
6. すべてのセルを先頭から順に実行します（Run all）。最後に「READY: Furusato ontology data v3.0.0」で始まる行と、20テーブルの確認が出力されれば完了です。
7. 11の ot_* テーブルの件数を付録Aと照合します（ot_donation 80,000、ot_municipality 1,741、ot_supplier_gift 14,514 など）。寄付が0件の Donor 18件と、受け入れが0件の Municipality 10件が残っているのが正しい状態です。
8. SQL analytics endpoint に反映されてから同じテーブルを SQL で読み、ot_donation が 80,000件、DonationAmountYen の合計が 1,344,099,000円であることを確認します。MunicipalityId の先頭のゼロが残っていることも確かめます。

> Notebook 01 は、検証済みのテーブルを安全に置き換える仕組みを持っています。完了した Notebook 01 を理由なく何度も実行しないでください。

<details>
<summary>English</summary>

## 5.2 Steps

1. Open the Lakehouse and create folders under Files so that the path is Files/furusato/seed (a furusato folder with one more folder inside it). Upload the eight CSV files there. Do not put the August observation data (donation_events_001 to 003.csv) here.
2. Next, create an empty increment folder under Files (Files/increment). Chapter 9 watches this folder for file arrivals, so leave it empty for now.
3. Compare the uploaded file sizes with dataset-manifest.json in the data folder and confirm that all eight files are present.
4. Import Notebook 01 into your work folder and attach LH_Furusato_&lt;PID&gt;.
5. In the first parameter cell, change PARTICIPANT_ID to your &lt;PID&gt;. Leave all other values unchanged (INPUT_DIR stays "Files/furusato/seed").
6. Run all cells from the top (Run all). It is complete when the output ends with a line starting "READY: Furusato ontology data v3.0.0" and a confirmation for all 20 tables.
7. Check the counts of the 11 ot_* tables against Appendix A (ot_donation 80,000, ot_municipality 1,741, ot_supplier_gift 14,514 and so on). It is correct that 18 donors with no donations and 10 municipalities that received none are kept.
8. Once the SQL analytics endpoint has synchronized, read the same tables with SQL and confirm that ot_donation has 80,000 rows and that DonationAmountYen totals JPY 1,344,099,000. Also confirm that MunicipalityId keeps its leading zeros.

> Notebook 01 has a safe mechanism for replacing validated tables. Do not rerun a completed Notebook 01 without a reason.

</details>
