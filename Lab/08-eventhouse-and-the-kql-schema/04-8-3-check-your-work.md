# 8.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 5つの管理オブジェクトがそろっている | コマンドがエラーになった場合は、権限、型、マッピング名を確認します。データを送り直してごまかしません。 |
| 取り込み前の DonationEvents が0行 | 行がある場合は、どのファイル（SourceFile）の行かを確認し、講師の指示を待ちます。 |
| 参加者所有の新規ターゲットでのみ、初回取り込み前に DonationEvents だけの mirroring を安全に確認した | 所有範囲・フォルダー・schema・RLS・既存 policy と、IsEnabled=true・TargetLatencyInMinutes=5 を確認できなければ停止し、Activator 用ファイルを置きません。 |

<details>
<summary>English</summary>

## 8.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| All five management objects exist | If a command fails, check permissions, types and the mapping name. Never cover the problem up by resending data. |
| DonationEvents has zero rows before ingestion | If rows exist, check which files (SourceFile) they came from and wait for the instructor's direction. |
| DonationEvents-only mirroring was safely verified before first ingestion only on a fresh participant-owned target | If ownership scope, folder, schema, RLS, the existing policy and IsEnabled=true / TargetLatencyInMinutes=5 cannot be verified, stop without uploading any Activator input. |

</details>
