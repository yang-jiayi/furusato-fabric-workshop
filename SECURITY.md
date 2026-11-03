# セキュリティ分類 / Security classification

[日本語](#日本語) | [English](#english)

---

## 日本語

### 公開用の新規履歴と非公開情報

**この公開配布用リポジトリは、確認済みの最新配布物だけを新しい独立した Git 履歴へ収録します。**
対象は最新版の HTML と参加者 ZIP、それを利用・再生成するための合成データ、
Notebook、ソース、設計図、テストです。ガイドにある標準10問・84条件と汎用評価エンジンは保持します。
内部の追加評価コーパス・正解・実回答・作業ログ・実環境バックアップ・認証情報は含めません。

旧リポジトリの履歴、タグ、Release、PR、Actions ログや成果物は非公開アーカイブの範囲です。
HEAD から削除するだけでは過去の情報は消えません。公開側へ旧履歴を merge、pull、mirror push、
履歴付き bundle の import で持ち込まず、過去のタグや Release も一括移送しないでください。
寄稿者は公開側を新しく clone し、必要な変更をファイル単位で確認してから提出します。
公開前の独立した内容・秘密情報・権利の確認と明示的な承認は引き続き必要です。

環境別（dev/test/prod）の設定、ID、認証、評価入力・出力は、無視設定の有無にかかわらず
**すべての Git checkout の外にある非公開保存先**で管理します。新しい GitHub repository ID は
Secrets・Environments・認証設定を継承しません。必要な連携は最小権限で個別に再承認し、
古い認証情報や Actions 成果物を移送しません。[公開版の利用手順](docs/public-onboarding/README.md)を参照してください。

General ラベルは内容の分類であり、公開承認・権利確認・秘密情報検査の代わりではありません。
接続先・利用者・テナント・Workspace は各実習環境で設定し、ローカルの記録は Git の外で管理します。

### Microsoft Purview 秘密度分類: General

この分類は、現行の Workshop 3.1.0 参加者向け HTML、GitHub Lab、ZIP と、その教材ソースに適用します。
標準10問・84条件と汎用評価エンジンは保持しますが、公開承認や既知の制約の解消を意味しません。
配布 ZIP に Word／PDF は含まれません。HTML と ZIP の SHA-256 は
[docs/SHA256SUMS.txt](docs/SHA256SUMS.txt) で検証してください。

#### Git ネイティブ形式のファイル

Git ネイティブなソース、データ、Web／図版の各形式（`.md`、`.html`、`.svg`、
`.png`、`.json`、`.csv`、`.ipynb`、`.kql`、`.py`、`.ps1`、`.tmdl`、および
関連する定義ファイル）は、ここに記載したパッケージ単位の **General**
分類を継承します。

#### ラベルを埋め込まない理由

Microsoft Purview は、これらの Git ネイティブ形式へ非保護ラベルを埋め込みません。
保護付きの `.pfile` として包むとファイル名が変わり、ワークショップ、Notebook、
チェックサム、GitHub の ZIP が利用できなくなります。したがって、これらの
ファイルの内容とパスは変更しません。

---

## English

### Fresh public-only history and private material

**This public-distribution repository starts a new independent Git history containing
only the reviewed current distribution.** It includes the current HTML guide and participant ZIP,
synthetic data, notebooks, sources, diagrams and tests needed to use and rebuild it.
The guide's standard ten questions/84 conditions and the generic evaluation engine
remain available. Internal extra problem packs, keys, actual answers, work logs,
live-environment backups and credentials are not distributed.

The former repository's history, tags, Releases, PRs and Actions logs/artifacts belong
to the private archive. Deleting a file from HEAD does not erase those surfaces.
Never merge, pull, mirror-push or import a history-bearing bundle from the private
archive into this public repository; do not bulk-transfer its tags or Releases.
Contributors must clone the public repository afresh and review proposed changes
file by file. Independent content, secret and rights review and explicit publication
approval remain required.

Keep per-environment (dev/test/prod) configuration, IDs, authentication and evaluation
inputs/outputs in **private storage outside every Git checkout**, even if a directory
would be ignored by Git. The new GitHub repository ID inherits no Secrets,
Environments or authentication settings. Reauthorize needed integrations individually
with least privilege; do not transfer old credentials or Actions artifacts.
See [public onboarding](docs/public-onboarding/README.md).

The General label is a classification, not publication authorization, a rights
review or a secret scan. Configure identities, tenants, workspaces and connections
per exercise environment; keep local evidence outside Git.

### Microsoft Purview sensitivity classification: General

This classification applies to the current Workshop 3.1.0 participant HTML,
GitHub Lab, ZIP and their source materials. The standard ten questions/84
conditions and generic evaluation engine remain available, but this does not
constitute publication authorization or resolve known limitations. The participant
ZIP contains no Word/PDF documents. Verify the HTML and ZIP SHA-256 values with
[docs/SHA256SUMS.txt](docs/SHA256SUMS.txt).

#### Git-native formats

Git-native source, data, and web/diagram formats (`.md`, `.html`, `.svg`,
`.png`, `.json`, `.csv`, `.ipynb`, `.kql`, `.py`, `.ps1`, `.tmdl`, and
related definition files) inherit the package-level **General**
classification stated here.

#### Why no label is embedded

Microsoft Purview does not embed a non-protective label into those Git-native
formats. Wrapping them as protected `.pfile` files would change filenames and
make the workshop, notebooks, checksums, and GitHub ZIP unusable, so their
content and paths remain unchanged.
