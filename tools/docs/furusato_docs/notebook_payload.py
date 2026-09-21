"""Decode Notebook 04's literal payload without executing notebook code."""

from __future__ import annotations

import ast
import base64
import gzip
import json

PAYLOAD_CELL_TAG = "furusato-provisioning-payload"
CHUNKS_VARIABLE = "_PAYLOAD_CHUNKS"


def decode_notebook_payload(notebook: dict) -> dict:
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    payload_cells = [
        cell for cell in code_cells
        if PAYLOAD_CELL_TAG in cell.get("metadata", {}).get("tags", [])
    ]
    if not payload_cells:
        # The original single-cell layout had no role tag.
        payload_cells = [
            cell for cell in code_cells
            if f"{CHUNKS_VARIABLE} = [" in "".join(cell["source"])
        ]

    chunks: list[str] = []
    initialized = False
    for cell in payload_cells:
        for statement in ast.parse("".join(cell["source"])).body:
            if (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id == CHUNKS_VARIABLE
            ):
                if initialized:
                    raise ValueError("Payload has more than one chunk initializer")
                expression = statement.value
                initialized = True
            elif (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and statement.value.func.value.id == CHUNKS_VARIABLE
                and statement.value.func.attr == "extend"
            ):
                call = statement.value
                if not initialized or len(call.args) != 1 or call.keywords:
                    raise ValueError("Payload chunk extension has no initializer or invalid arguments")
                expression = call.args[0]
            else:
                continue

            values = ast.literal_eval(expression)
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError("Payload chunks must be a literal list of strings")
            chunks.extend(values)

    if not initialized or not chunks:
        raise ValueError("Notebook has no literal provisioning payload")
    compressed = base64.b64decode("".join(chunks), validate=True)
    payload = json.loads(gzip.decompress(compressed).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Provisioning payload must be a JSON object")
    return payload
