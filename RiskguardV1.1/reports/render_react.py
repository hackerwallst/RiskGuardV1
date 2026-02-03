from __future__ import annotations
from pathlib import Path
import base64
import json


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff")


def _safe_script(js: str) -> str:
    # evita fechar a tag <script> dentro do conteudo
    return js.replace("</script", "<\\/script")

def _img_to_base64(path: Path) -> str | None:
    try:
        if not path or not path.exists():
            return None
        data = path.read_bytes()
        suffix = path.suffix.lower()
        mime = "image/png"
        if suffix == ".svg":
            mime = "image/svg+xml"
        elif suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None

def _load_icons() -> dict:
    base_dir = Path(__file__).resolve().parent
    icons_dir = base_dir / "icons"
    mapping = {
        "trades": "trades.svg",
        "winrate": "winrate.svg",
        "drawdown": "drawdown.svg",
        "depositos": "depositos.svg",
        "saques": "saques.svg",
        "logo": "logo riskguard.svg",
    }
    out = {}
    for key, fname in mapping.items():
        src = _img_to_base64(icons_dir / fname)
        if src:
            out[key] = src
    return out


def render_react_html(summary: dict, out_html: Path) -> Path:
    root = Path(__file__).resolve().parent / "react_report"
    css_path = root / "report.css"
    react_path = root / "react.production.min.js"
    dom_path = root / "react-dom.production.min.js"
    app_path = root / "report_app.js"

    missing = [p for p in (css_path, react_path, dom_path, app_path) if not p.exists()]
    if missing:
        miss = ", ".join(str(p) for p in missing)
        raise FileNotFoundError("React assets missing: " + miss)

    data_json = json.dumps(summary, ensure_ascii=False, default=str)
    data_json = data_json.replace("</", "<\\/")

    icons_json = json.dumps(_load_icons(), ensure_ascii=False, default=str)
    icons_json = icons_json.replace("</", "<\\/")

    css = _strip_bom(_read_text(css_path))
    react_js = _safe_script(_strip_bom(_read_text(react_path)))
    dom_js = _safe_script(_strip_bom(_read_text(dom_path)))
    app_js = _safe_script(_strip_bom(_read_text(app_path)))

    html = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>RiskGuard Report</title>
  <style>{css}</style>
</head>
<body>
  <div id="root"></div>
  <script>window.__REPORT_DATA__ = {data};</script>
  <script>window.__REPORT_ICONS__ = {icons};</script>
  <script>{react_js}</script>
  <script>{dom_js}</script>
  <script>{app_js}</script>
</body>
</html>
""".format(
        data=data_json,
        icons=icons_json,
        css=css,
        react_js=react_js,
        dom_js=dom_js,
        app_js=app_js,
    )

    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return out_html


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--summary", required=True, help="Caminho do summary_*.json")
    p.add_argument("--out", required=False, help="Caminho do HTML de saida")
    args = p.parse_args()
    sj = Path(args.summary)
    out = Path(args.out) if args.out else sj.with_suffix(".html")
    data = json.loads(sj.read_text(encoding="utf-8"))
    render_react_html(data, out)
    print("HTML gerado em:", out)
