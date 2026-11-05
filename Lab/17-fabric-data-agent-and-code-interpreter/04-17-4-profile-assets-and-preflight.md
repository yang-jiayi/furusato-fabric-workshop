# 17.4 プロファイル資産と事前確認

[Lab 目次](../README.md) · [この章の目次](README.md)

同梱の `workshop/v3.0.0-preview/data-agent/profiles/current-experimental` にある `profile-manifest.json`、`global-instructions.txt`、`source-instructions.json`、`selection-contract.json`、定義と portable stage template を確認します。manifest の SHA-256 と実ファイルを照合し、プロファイル名が `current-experimental` であることを確認します。これらは全体を照合する必須の比較入力です。`global-instructions.txt` を含む profile は末尾も変更せず、現行共通指示は17.9の別ファイルで固定します。

**manifest の選択資産件数**

| 論理ソース | オブジェクト | 列 | メジャー |
| --- | --- | --- | --- |
| Lakehouse / SQL | 11 | 88 | — |
| KQL Database | 1 | 10 | — |
| Semantic model | 5 | 31 | 10 |
| Ontology | 10 | — | — |

definition few-shot file は 0 件、実定義の active example は 0 件です。不変な比較入力の global instructions は 9994 UTF-16 単位です。適用する現行共通指示は3,394 UTF-16 単位で、上限 10000 単位以下です。

<details>
<summary>English</summary>

## 17.4 Profile assets and preflight

Inspect `profile-manifest.json`, `global-instructions.txt`, `source-instructions.json`, `selection-contract.json`, the definition and portable stage template under `workshop/v3.0.0-preview/data-agent/profiles/current-experimental`. Compare manifest SHA-256 values with the files and confirm the profile name is `current-experimental`. These are required complete comparison inputs. Preserve the profile, including the ending of `global-instructions.txt`; bind the current common guidance from its separate file in17.9.

**Manifest selection inventory**

| Logical source | Objects | Columns | Measures |
| --- | --- | --- | --- |
| Lakehouse / SQL | 11 | 88 | — |
| KQL Database | 1 | 10 | — |
| Semantic model | 5 | 31 | 10 |
| Ontology | 10 | — | — |

The definition contains 0 definition few-shot files and 0 active examples. The immutable comparison input's global instructions measure 9994 UTF-16 units. The current common guidance to apply measures 3,394 UTF-16 units, within the 10000-unit maximum.

</details>
