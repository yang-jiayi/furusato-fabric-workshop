# 9.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

7. ルールの History を下にスクロールして Activation details を開き、Subject が /Files/increment/donation_events_001.csv、Type が Microsoft.Fabric.OneLake.FileCreated になっている実際の activation 行を確認して記録します。添付図の概要 KPI やグラフを001の証拠に代用しません。001の行が見つからなければ未確認とし、再アップロードせずに停止します。

![Activator の History の概要。Running のルール、Last 24 hours の選択、欠けのない6つの KPI と UTC の Activation count グラフ。Activation details の対象行はこの図に含まれない。](../assets/p30-09-native-delivery.png)

ルールの History の概要。6つの KPI、Time の選択、UTC の Activation count グラフを示します。数値は表示時点と選択期間で変わります。下にスクロールして Activation details を開き、自分の001の対象パスと FileCreated を記録します。この概要だけでは001の処理や Pipeline・Copy の成功は確認できません。

<details>
<summary>English</summary>

## 9.2 Steps

7. Scroll down in the rule's History to Activation details, then confirm and record the actual activation row with Subject /Files/increment/donation_events_001.csv and Type Microsoft.Fabric.OneLake.FileCreated. Do not substitute the figure's overview KPIs or chart as evidence for 001. If the 001 row is missing, record it as unverified and stop without re-uploading.

![Activator History overview with the Running rule, Last 24 hours selector, six complete KPIs and the UTC Activation count chart. The target Activation details row is not included.](../assets/p30-09-native-delivery.png)

Rule History overview showing six KPIs, the Time selector and the UTC Activation count chart. Values depend on the observation time and selected period. Scroll down to Activation details and record your own 001 target path and FileCreated. This overview alone does not verify processing of 001 or Pipeline/Copy success.

</details>
