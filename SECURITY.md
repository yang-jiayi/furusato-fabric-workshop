# セキュリティ分類 / Security classification

[日本語](#日本語) | [English](#english)

---

## 日本語

### 公開用の新規履歴と非公開情報

**この公開配布用リポジトリは、確認済みの最新配布物だけを新しい独立した Git 履歴へ収録します。**
対象は最新版の Word／HTML 各 1 本と、それを利用・再生成するための合成データ、
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
以下の Office ラベル識別子は配布物の分類用メタデータで、Fabric の実行先やアクセス資格情報ではありません。
接続先・利用者・テナント・Workspace は各実習環境で設定し、ローカルの記録は Git の外で管理します。

過去の誤ったラベル・テナント識別子を拒否する検査は、原文の識別子ではなく SHA-256
フィンガープリントを保持します。OOXML と style carrier の検査は同じ大文字・小文字の
正規化を使い、エラーにも識別子の実値を出力しません。検査対象を減らす変更ではありません。

### Microsoft Purview 秘密度分類: General

この分類は、本 v2.7.0 ワークショップ配布物に含まれる**すべてのファイル**に適用されます。

#### Office ドキュメント

Office ドキュメント（`.docx`、`.xlsx`）には、Microsoft Purview の **General**
ラベルが埋め込まれています。

| 項目 | 値 |
|---|---|
| Label ID | `f42aa342-8706-4288-bd11-ebb85995028c` |
| Tenant/Site ID | `72f988bf-86f1-41af-91ab-2d7cd011db47` |

リリースされたバイト列は `RELEASE_SHA256SUMS.txt` で検証してください。

#### Git ネイティブ形式のファイル

Git ネイティブなソース、データ、Web／図版の各形式（`.md`、`.html`、`.svg`、
`.png`、`.json`、`.csv`、`.ipynb`、`.kql`、`.py`、`.ps1`、`.tmdl`、および
関連する定義ファイル）は、ここに記載したパッケージ単位の **General**
分類を継承します。

自己完結 HTML のリリースバイト列も `RELEASE_SHA256SUMS.txt` に記載しています。

#### ラベルを埋め込まない理由

Microsoft Purview は、これらの Git ネイティブ形式へ非保護ラベルを埋め込みません。
保護付きの `.pfile` として包むとファイル名が変わり、ワークショップ、Notebook、
チェックサム、GitHub の ZIP が利用できなくなります。したがって、これらの
ファイルの内容とパスは変更しません。

---

## English

### Fresh public-only history and private material

**This public-distribution repository starts a new independent Git history containing
only the reviewed current distribution.** It includes one current Word/HTML pair,
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
review or a secret scan. The Office label identifiers below are classification
metadata, not Fabric deployment targets or access credentials. Configure identities,
tenants, workspaces and connections per exercise environment; keep local evidence
outside Git.

Checks for accidentally applied historical labels and tenants store SHA-256
fingerprints instead of literal private identifiers. OOXML and style-carrier
validation use the same case normalization and do not echo the identifiers in
errors. This does not reduce the set of rejected identifiers.

### Microsoft Purview sensitivity classification: General

This classification applies to **every file** in this v2.7.0 workshop
distribution.

#### Office documents

Office documents (`.docx`, `.xlsx`) carry the embedded Microsoft Purview
**General** label.

| Item | Value |
|---|---|
| Label ID | `f42aa342-8706-4288-bd11-ebb85995028c` |
| Tenant/Site ID | `72f988bf-86f1-41af-91ab-2d7cd011db47` |

Verify their release bytes with `RELEASE_SHA256SUMS.txt`.

#### Git-native formats

Git-native source, data, and web/diagram formats (`.md`, `.html`, `.svg`,
`.png`, `.json`, `.csv`, `.ipynb`, `.kql`, `.py`, `.ps1`, `.tmdl`, and
related definition files) inherit the package-level **General**
classification stated here.

The self-contained HTML release bytes are also listed in
`RELEASE_SHA256SUMS.txt`.

#### Why no label is embedded

Microsoft Purview does not embed a non-protective label into those Git-native
formats. Wrapping them as protected `.pfile` files would change filenames and
make the workshop, notebooks, checksums, and GitHub ZIP unusable, so their
content and paths remain unchanged.
