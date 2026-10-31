# 7.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

7. 件数の考え方を確認します。多対一の関係では、関係の数は Origin 側の件数と同じです（MunicipalityInPrefecture は 1,741）。SupplierProvidesGift は多対多で 14,514 です。モデル全体では Node 109,592・Edge 297,303 になります（付録A）。必要に応じて SQL で、キー列に NULL や相手側に存在しないキーがないかを確認します。

> Relationship の向きは業務上の主張です。逆向きにたどることはできますが、定義した向きは変えません。

<details>
<summary>English</summary>

## 7.2 Steps

7. Review how counts work. For a many-to-one relationship, the number of links equals the number of origin instances (1,741 for MunicipalityInPrefecture). SupplierProvidesGift is many-to-many with 14,514. The whole model has 109,592 nodes and 297,303 edges (Appendix A). If needed, use SQL to check that key columns contain no NULLs and no keys that are missing on the other side.

> A relationship's direction is a business statement. You can traverse it in reverse, but do not change the defined direction.

</details>
