# HTML textbook renderer / HTML 教科書レンダラー

The current participant guide is generated with
[`tools/docs/current_delivery.py`](../docs/current_delivery.py). Its bilingual
HTML is a self-contained file; the matching numbered Markdown Lab is generated
from the same source. The current participant package contains no Word or PDF
manuals or exports.

Use the [HTML/Lab maintenance guide](../docs/CURRENT_HTML_LAB.md) for the
supported build, validation and package workflow. Run commands from the
repository root. The static and browser checks validate the generated document
and local interactions; they do not certify Fabric deployment or AI answer
quality.

The diagram renderer reads the current participant SVGs under
`docs/assets/current-diagrams`, sanitizes them and embeds them in the standalone
HTML. Current screenshots are separately reviewed source assets and must not be
fabricated, relabeled or treated as live deployment evidence.

## Renderer and checks

- `furusato_html/preview30.py` captures and renders the shared bilingual model.
- `furusato_html/render.py` renders text, tables, code, figures and callouts.
- `furusato_html/diagrams.py` sanitizes and translates the current diagrams.
- `assets/preview30.css` and `assets/preview30.js` provide responsive styling,
  navigation, search, language switching, copy and progress controls.
- `tests/` contains the renderer and browser regressions used by the current
  delivery pipeline.
