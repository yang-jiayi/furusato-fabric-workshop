# Participant publication / 参加者向け公開

The supported participant delivery is the versioned bilingual standalone HTML
textbook with its numbered GitHub Lab companion. Build, validate and package
those artifacts with [`current_delivery.py`](../docs/current_delivery.py), using
the exact steps in [`CURRENT_HTML_LAB.md`](../docs/CURRENT_HTML_LAB.md).

参加者向けの現行配布物は、版管理された日英単一HTML教科書と番号付きGitHub Labです。
生成・検証・ZIP化は [`current_delivery.py`](../docs/current_delivery.py) を使い、
[`CURRENT_HTML_LAB.md`](../docs/CURRENT_HTML_LAB.md) の手順に従ってください。

The supported route creates no Word or PDF guide, and the participant ZIP rejects
either format. Both the legacy export CLI and its direct Python export API refuse
to create a Word/HTML pair; only read-only validation remains available for an
existing staged pair. The current README describes the actual GitHub download/open
path; it does not claim that a hosted website or GitHub Pages site exists.

現行経路ではWord/PDFの手順書を生成せず、配布ZIPにも含めません。
旧export CLIとPython APIはWord/HTMLペアを生成せず、既存ステージ済みペアの
読み取り専用検証だけを残します。
READMEは実際のGitHubダウンロードとローカルで開く経路を案内し、
WebサイトやGitHub Pagesが公開済みとは記載しません。

Never put credentials, raw evaluation answers, private captures or local
diagnostics in source inventories, participant files or publication artifacts.
Local validation is not evidence of live Fabric deployment or Data Agent
accuracy. Keep those claims tied to separately verified live evidence.

資格情報、生の評価回答、非公開キャプチャ、ローカル診断情報を、
ソース一覧・参加者向けファイル・公開成果物に含めないでください。
ローカル検証はFabricへの実配置やData Agentの正答率を証明しません。
その主張は別途確認した実環境の証跡に基づけてください。
