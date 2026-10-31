# 4.2 操作手順

[Lab 目次](../README.md) · [この章の目次](README.md)

1. 割り当てられた、または自分に操作が許可されたワークスペースと作業フォルダーを開きます。手動でアイテムを作成・インポートするときは、先にこのフォルダーを開き、作成後も置き場所を確認します。コマンドの配置先は24.4の実際のフォルダー対応で固定します。
2. 参加者IDを確認します。&lt;PID&gt; は 001〜999 の3桁の文字列です（000、空欄、4桁以上では Notebook 01 が停止します）。アイテム名の末尾には &lt;PID&gt; を付けます。例：LH_Furusato_&lt;PID&gt;、EH_Furusato_&lt;PID&gt;、PL_Furusato_&lt;PID&gt;、ONT_Furusato_&lt;PID&gt;、SM_Furusato_Analytics_&lt;PID&gt;、DA_Furusato_&lt;PID&gt;、My activator_&lt;PID&gt;。
3. 使える機能と権限を、見るだけで確認します。容量（capacity）が割り当てられていること、Ontology、Ontology agent、Data Agent が作成メニューやツールバーに表示されること、各アイテムに必要な読み取り・ビルド・書き込みの権限があることを確かめます。
4. テナント設定、容量、ワークスペースのロールを変更する必要がある場合は管理者へ依頼します。必須のLakehouse、KQL Database、Semantic model、主Ontology、Data Agentや必要権限が欠ける場合は依存する作業を止めます。任意の追加機能だけが未対応の場合はその項目を記録し、独立して実施できる演習を続けます。
5. 配布ファイルを編集しません。CSV を Excel で開いて保存すると MunicipalityID の先頭のゼロが失われるため、そのままアップロードします。必要に応じて、PowerShell の Get-FileHash で計算した SHA-256 を、data フォルダーの SHA256SUMS.txt と比べます。
6. ワークスペースID、アイテムID、URL、資格情報、トークンを、共有するドキュメントやチャットに貼りません。サインインは通常の画面で行い、Windows Hello などの本人確認は自分で完了します。トークンや Cookie を取り出して使うことはしません。
7. 既存のアイテムやデータを、空きを作るためや試しに削除・上書きしません。作成やアップロードがタイムアウトした場合は、同じ操作を繰り返す前に、アイテムの一覧や件数で現在の状態を確認します。

> 同じワークスペースを複数の参加者で使う場合があります。自分の &lt;PID&gt; が付いたアイテムだけを操作します。

> 標準の初回経路は24.4〜24.6の配置です。その後の5〜8章では作成済みの設定とデータを確認します。手動作成とコマンド作成を同じ参加者IDで重ねません。既に手動作成した範囲は、自動配置に引き継げないため、削除で合わせず別の許可済み空フォルダーと参加者IDから始めます。

<details>
<summary>English</summary>

## 4.2 Steps

1. Open the assigned workspace and folder, or the scope you are authorized to use. Before manually creating or importing an item, open this folder and verify the item’s location afterwards. The command deployment target is fixed by the actual folder mapping in 24.4.
2. Confirm your participant ID. &lt;PID&gt; is a three-digit string from 001 to 999 (Notebook 01 stops on 000, an empty value or four or more digits). Item names end with &lt;PID&gt;, for example LH_Furusato_&lt;PID&gt;, EH_Furusato_&lt;PID&gt;, PL_Furusato_&lt;PID&gt;, ONT_Furusato_&lt;PID&gt;, SM_Furusato_Analytics_&lt;PID&gt;, DA_Furusato_&lt;PID&gt; and My activator_&lt;PID&gt;.
3. Check available features and permissions by looking only. Confirm that a capacity is assigned, that Ontology, Ontology agent and Data Agent appear in the create menus or toolbars, and that you have the read, build and write permissions each item needs.
4. Ask the administrator for required changes to tenant settings, capacity or workspace roles. Stop dependent work if a required Lakehouse, KQL database, semantic model, main ontology, Data Agent or permission is missing. If only an optional extension is unsupported, record it and continue independent exercises.
5. Do not edit the distributed files. Opening and saving a CSV file in Excel drops the leading zeros of MunicipalityID, so upload the files as they are. If needed, compare SHA-256 values calculated with PowerShell Get-FileHash against SHA256SUMS.txt in the data folder.
6. Never paste workspace IDs, item IDs, URLs, credentials or tokens into shared documents or chats. Sign in through the normal screens and complete identity checks such as Windows Hello yourself. Never extract or reuse tokens or cookies.
7. Never delete or overwrite existing items or data to make room or to experiment. If a create or upload operation times out, check the current state in the item list or with counts before repeating it.

> Several participants may share the same workspace. Work only on items that carry your own &lt;PID&gt;.

> The standard first-run route is deployment in 24.4–24.6; Chapters 5–8 then inspect the created settings and data. Do not combine manual and command creation under the same participant ID. Manually created resources cannot be adopted by this deployment; start in another authorized empty folder with a distinct participant ID instead of deleting them to force a match.

</details>
