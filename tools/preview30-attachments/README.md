# Ontology Copilot attachment exercise / 添付演習

The four files are **synthetic conversation context**, not ingestion, RDF import,
permissions or independent benchmark answers. `data-dictionary.txt` is generated
from the actual public CSV headers, hashes and typed ontology binding contract.
The image is an explicitly labelled domain diagram, never a fabricated UI capture.
Existing v2.7 data and the standard ten questions / 84 conditions are unchanged.
The dictionary now labels original source-contract types separately from their
new TMDL target types. It is not a generation-2 payload: no old `EntityTypes` JSON
or `KustoTable` object is implicitly valid for the new format. Native time-series
binding and DAX metric projection still require actual service/UI verification.

```powershell
python .\tools\preview30-attachments\build_attachments.py
python .\tools\preview30-attachments\test_attachments.py
```

Generation needs the packages in `requirements.txt` and an embeddable Japanese
TrueType font. Windows Meiryo is selected by default; use `--font` elsewhere.
PDF font subsets are embedded. The manifest records the font hash for exact
regeneration. PNG labels use the same font. No full font file is distributed.
Outputs are only `workshop\v3.0.0-preview\attachments`; no source data is rewritten.

## 操作 / Exercise

1. Instructor approves an isolated new-experience ontology lab copy and source IDs.
   Save its baseline definition/version. Keep all real IDs in a private worksheet.
2. In a fresh **Plan** conversation, request scoped discovery, a draft, validation
   and read-only preview without attachments. Save the transcript privately.
3. Start a separate conversation on the same unchanged baseline. Attach
   `business-requirements.pdf`, `data-dictionary.txt`, `domain-model.png`. Refer to
   each filename and repeat the same prompt. At most ten files / conversation,
   each at most 5 MB. Refresh/closing the tab ends current preview conversations.
4. Compare geography, key types, relationship direction, layer/denominator,
   unsupported delivery/wealth claims, source grounding and proposed changes.
   The optional `revision-requirements.txt` tests a metadata-only improvement.
5. Preserve stable IDs. Only after explicit approval switch to **Act** for the
   approved lab copy; read back the published definition and compare the delta.
   Plan must not have changed either the ontology or any source.
6. Record actual attachment names/upload, evidence of model use, validation,
   preview, Act and readback separately. Missing rollout = blocked, not passed.
   Local package tests do not prove the service uploaded or used the files.

添付教材は設計の文脈です。実データ取り込み、RDF import、権限付与ではありません。
アップロードと回答中の利用を別々に記録し、添付有無を新しい会話で比較します。
Plan の段階では変更せず、変更差分を承認してから lab-copy に限定して Act します。
画面・会話・評価の原本は非公開に保持します。
