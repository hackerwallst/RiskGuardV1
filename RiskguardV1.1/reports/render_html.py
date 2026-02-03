# reports/render_html.py
from __future__ import annotations
from pathlib import Path
import json, html, calendar, base64
from datetime import datetime

# =========================
# CSS
# =========================
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
:root{--page-w:1264px;--page-h:1788px;}
@page{size:var(--page-w) var(--page-h);margin:0;}
body{font-family:'Poppins', sans-serif;background:#f5f7fb;color:#1f2937;margin:0;padding:0;}
.wrap{max-width:1200px;margin:0 auto;padding:32px;}
.page{margin-bottom:28px;}
.page-break{page-break-after:always;}
.card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;box-shadow:0 10px 30px rgba(15,23,42,.08);padding:22px;}
.card-title{font-size:20px;font-weight:600;margin:0 0 16px;color:#1f2937;}
.muted{color:#6b7280;}
.header-card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;box-shadow:0 10px 30px rgba(15,23,42,.08);padding:26px;margin-bottom:18px;}
.header-block{padding:0;margin:0;}
.section{margin-top:16px;}
.header-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;}
.brand{display:flex;align-items:center;gap:12px;}
.logo{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,#5b8cff,#60a5fa);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px;box-shadow:0 8px 18px rgba(59,130,246,.28);}
.brand-name{font-size:22px;font-weight:600;color:#1f2937;}
.date-box{display:flex;align-items:center;gap:10px;color:#6b7280;}
.date-pill{background:#f3f4f6;border-radius:10px;padding:6px 10px;font-weight:600;color:#4b5563;}
.title{font-size:34px;font-weight:600;margin:14px 0 4px;color:#111827;}
.subtitle{color:#6b7280;margin-bottom:14px;}
.period-bar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;background:#f8fafc;border:1px solid #eef2f7;border-radius:14px;padding:14px 18px;}
.period-left{display:flex;gap:26px;flex-wrap:wrap;color:#6b7280;}
.period-left b{color:#111827;font-weight:600;}
.meta-right{display:flex;align-items:baseline;gap:10px;}
.balance{font-size:30px;font-weight:700;color:#111827;}
.variation{font-size:18px;font-weight:600;}
.variation.positive{color:#22c55e;}
.variation.negative{color:#ef4444;}
.grid{display:grid;gap:18px;}
.grid-3{grid-template-columns:repeat(3,minmax(0,1fr));}
.grid-2{grid-template-columns:repeat(2,minmax(0,1fr));}
.span-2{grid-column:span 2;}
.summary-list{display:flex;flex-direction:column;gap:10px;}
.summary-item{display:flex;align-items:center;gap:12px;padding:6px 0;}
.summary-icon{width:36px;height:36px;border-radius:10px;background:#eef2ff;color:#3b82f6;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;}
.summary-label{color:#6b7280;flex:1;}
.summary-value{font-size:20px;font-weight:600;color:#111827;}
.summary-value.negative{color:#ef4444;}
.summary-value.positive{color:#22c55e;}
.negative{color:#ef4444;}
.positive{color:#22c55e;}
.summary-sub{font-size:22px;font-weight:700;color:#111827;}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;font-size:13px;color:#6b7280;}
.legend-item{display:flex;align-items:center;gap:6px;}
.legend-line{width:30px;height:2px;background:#22c55e;display:inline-block;border-radius:2px;}
.legend-line.gray{height:0;border-top:2px dashed #9ca3af;background:transparent;}
.legend-line.red{background:#ef4444;}
.chart-img{width:100%;height:auto;border-radius:12px;border:1px solid #eef2f7;background:#ffffff;display:block;}
.chart-img--dd,.chart-img--mc{height:240px;object-fit:contain;}
.chart-placeholder{height:200px;border:1px dashed #e5e7eb;border-radius:12px;background:#f9fafb;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:13px;}
.subcard{background:#f8fafc;border:1px solid #eef2f7;border-radius:14px;padding:16px;}
.subcard-title{font-size:14px;font-weight:600;color:#6b7280;margin-bottom:10px;}
.mc-summary{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:center;}
.card-note{font-size:12px;color:#9ca3af;margin-top:8px;}
.split-table{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;}
.split-table.stack{grid-template-columns:1fr;}
.split-table-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;}
.table-title{font-size:14px;font-weight:600;color:#6b7280;margin-bottom:8px;}
.data-table{width:100%;border-collapse:collapse;font-size:14px;}
.data-table th{color:#6b7280;text-align:left;font-weight:600;padding-bottom:10px;border-bottom:1px solid #e5e7eb;}
.data-table td{padding:10px 0;border-bottom:1px solid #f1f5f9;color:#111827;}
.data-table td.right{text-align:right;}
.data-table .neg{color:#ef4444;}
.data-table .pos{color:#22c55e;}
.footer{text-align:center;color:#9ca3af;font-size:12px;margin-top:18px;}
.section-gap{margin-top:16px;}
.card{page-break-inside:avoid;break-inside:avoid;}
.wrap{max-width:1200px;margin:0 auto;padding:32px;}
.page{margin-bottom:28px;}
.page-break{page-break-after:always;}
.card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;box-shadow:0 10px 30px rgba(15,23,42,.08);padding:22px;}
.card-title{font-size:20px;font-weight:600;margin:0 0 16px;color:#1f2937;}
.muted{color:#6b7280;}
.header-card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;box-shadow:0 10px 30px rgba(15,23,42,.08);padding:26px;margin-bottom:18px;}
.header-block{padding:0;margin:0;}
.section{margin-top:16px;}
.header-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;}
.brand{display:flex;align-items:center;gap:12px;}
.logo{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,#5b8cff,#60a5fa);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px;box-shadow:0 8px 18px rgba(59,130,246,.28);}
.brand-name{font-size:22px;font-weight:600;color:#1f2937;}
.date-box{display:flex;align-items:center;gap:10px;color:#6b7280;}
.date-pill{background:#f3f4f6;border-radius:10px;padding:6px 10px;font-weight:600;color:#4b5563;}
.title{font-size:34px;font-weight:600;margin:14px 0 4px;color:#111827;}
.subtitle{color:#6b7280;margin-bottom:14px;}
.period-bar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;background:#f8fafc;border:1px solid #eef2f7;border-radius:14px;padding:14px 18px;}
.period-left{display:flex;gap:26px;flex-wrap:wrap;color:#6b7280;}
.period-left b{color:#111827;font-weight:600;}
.meta-right{display:flex;align-items:baseline;gap:10px;}
.balance{font-size:30px;font-weight:700;color:#111827;}
.variation{font-size:18px;font-weight:600;}
.variation.positive{color:#22c55e;}
.variation.negative{color:#ef4444;}
.grid{display:grid;gap:18px;}
.grid-3{grid-template-columns:repeat(3,minmax(0,1fr));}
.grid-2{grid-template-columns:repeat(2,minmax(0,1fr));}
.span-2{grid-column:span 2;}
.summary-list{display:flex;flex-direction:column;gap:10px;}
.summary-item{display:flex;align-items:center;gap:12px;padding:6px 0;}
.summary-icon{width:36px;height:36px;border-radius:10px;background:#eef2ff;color:#3b82f6;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;}
.summary-icon-img{width:22px;height:22px;object-fit:contain;display:block;}
.summary-label{color:#6b7280;flex:1;}

.summary-value{font-size:20px;font-weight:600;color:#111827;}
.summary-value.negative{color:#ef4444;}
.summary-value.positive{color:#22c55e;}
.negative{color:#ef4444;}
.positive{color:#22c55e;}
.summary-sub{font-size:22px;font-weight:700;color:#111827;}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;font-size:13px;color:#6b7280;}
.legend-item{display:flex;align-items:center;gap:6px;}
.legend-line{width:30px;height:2px;background:#3b82f6;display:inline-block;border-radius:2px;}
.legend-line.gray{height:0;border-top:2px dashed #9ca3af;background:transparent;}
.legend-line.red{background:#ef4444;}
.chart-img{width:100%;height:auto;border-radius:12px;border:1px solid #eef2f7;background:#ffffff;display:block;}
.chart-img--dd,.chart-img--mc{height:240px;object-fit:contain;}
.chart-placeholder{height:200px;border:1px dashed #e5e7eb;border-radius:12px;background:#f9fafb;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:13px;}
.subcard{background:#f8fafc;border:1px solid #eef2f7;border-radius:14px;padding:16px;}
.subcard-title{font-size:14px;font-weight:600;color:#6b7280;margin-bottom:10px;}
.mc-summary{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:center;}
.card-note{font-size:12px;color:#9ca3af;margin-top:8px;}
.split-table{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;}
.table-title{font-size:14px;font-weight:600;color:#6b7280;margin-bottom:8px;}
.data-table{width:100%;border-collapse:collapse;font-size:14px;}
.data-table th{color:#6b7280;text-align:left;font-weight:600;padding-bottom:10px;border-bottom:1px solid #e5e7eb;}
.data-table td{padding:10px 0;border-bottom:1px solid #f1f5f9;color:#111827;}
.data-table td.right{text-align:right;}
.data-table .neg{color:#ef4444;}
.data-table .pos{color:#22c55e;}
.footer{text-align:center;color:#9ca3af;font-size:12px;margin-top:18px;}
.section-gap{margin-top:16px;}
.card{page-break-inside:avoid;break-inside:avoid;}
svg{page-break-inside:avoid;break-inside:avoid;}
@media screen and (max-width: 1000px){
  .grid-3,.grid-2,.split-table,.split-table-3{grid-template-columns:1fr;}
  .span-2{grid-column:span 1;}
  .mc-summary{grid-template-columns:1fr;}
}
/* @media print removed to ensure exact screen replica in PDF */
"""
SVG_CSS = """
.svg{width:100%;height:auto;display:block}
.svg-grid{stroke:#e5e7eb;stroke-width:1;shape-rendering:crispEdges;stroke-dasharray:2 3}
.bar{fill:#3b82f6;opacity:.9}
.bar-neg{fill:#f59e0b;opacity:.9}
.dd-bar{opacity:1}
.pie-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}
.pie-legend{display:flex;flex-direction:column;gap:6px;margin-top:8px;font-size:12px;color:#6b7280;}
.pie-legend-item{display:flex;align-items:center;gap:8px;}
.pie-dot{width:10px;height:10px;border-radius:50%;}
.pie-label{flex:1;}
.pie-pct{color:#111827;font-weight:600;}
.line{stroke:#3b82f6;stroke-width:2}
.lbl{font-size:11px;fill:#6b7280}
.tick{font-size:11px;fill:#6b7280}
.eq-line{stroke:#3b82f6;stroke-width:1.6;fill:none;stroke-linecap:round;stroke-linejoin:round}
.hwm-line{stroke:#9ca3af;stroke-width:1.4;fill:none;stroke-dasharray:4 4}
.eq-dot{fill:#3b82f6}
.bad{fill:#ef4444;opacity:.12}
.annot{font-size:12px;fill:#ef4444}
.val{font-size:11px;fill:#374151}
"""
CSS = CSS + SVG_CSS

# =========================
# Helpers numéricos
# =========================
def _fmoney(x):
    try:
        val = float(x)
        if val < 0:
            return f"-${abs(val):,.2f}"
        return f"${val:,.2f}"
    except Exception:
        return str(x)

def _fpct(x):
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "N/D"

def _fpct1(x):
    try:
        return f"{float(x):.1f}%"
    except Exception:
        return "N/D"

def _parse_date(val):
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.fromisoformat(s.split("T")[0])
        except Exception:
            return None

def _fmt_date_br(val):
    dt = _parse_date(val)
    if dt:
        return dt.strftime("%d/%m/%Y")
    return str(val) if val is not None else ""

def _fmt_date_iso(val):
    dt = _parse_date(val)
    if dt:
        return dt.strftime("%Y-%m-%d")
    return str(val) if val is not None else ""

# =========================
# SVG helpers
# =========================
def _svg_bar_chart(data, width=960, height=180, pad=24, show_values=False, pct_map=None, rotate_labels=False):
    if not data:
        return "<div class='small'>Sem dados para plotar.</div>"
    labels, vals = zip(*data)
    n = len(vals)
    minv, maxv = min(0, min(vals)), max(0, max(vals))
    span = (maxv - minv) or 1.0
    inner_w = width - 2*pad
    inner_h = height - 2*pad
    bar_w = inner_w / max(n,1)
    zero_y = pad + inner_h * (maxv / span)
    lines = [f"<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    lines.append(f"<line x1='{pad}' y1='{zero_y:.1f}' x2='{width-pad}' y2='{zero_y:.1f}' class='svg-grid'/>")
    for i, v in enumerate(vals):
        x = pad + i * bar_w + 2
        h = inner_h * (abs(v) / span)
        y = zero_y - h if v >= 0 else zero_y
        cls = "bar-neg" if v < 0 else "bar"
        lines.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w-4:.1f}' height='{h:.1f}' rx='4' ry='4' class='{cls}'/>")
        if show_values:
            lab = str(labels[i])
            val_txt = _fmoney(v)
            if pct_map and lab in pct_map and pct_map[lab] is not None:
                val_txt = f"{val_txt} ({pct_map[lab]:.2f}%)"
            ty = (y - 4) if v >= 0 else (y + h + 12)
            tx = x + (bar_w-4)/2
            lines.append(f"<text x='{tx:.1f}' y='{ty:.1f}' class='val' text-anchor='middle'>{val_txt}</text>")
    step = 1 if rotate_labels else max(1, n // 12)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == n-1:
            tx = pad + i * bar_w + bar_w/2
            if rotate_labels:
                ty = height - 4
                lines.append(f"<text x='{tx:.1f}' y='{ty}' class='lbl' text-anchor='end' transform='rotate(-90 {tx:.1f} {ty})'>{lab}</text>")
            else:
                lines.append(f"<text x='{tx:.1f}' y='{height-6}' class='lbl' text-anchor='middle'>{lab}</text>")
    lines.append("</svg>")
    return "".join(lines)

def _svg_balance_drawdown_chart(points, width=960, height=220, pad=28):
    if not points:
        return "<div class='small'>Sem dados para plotar.</div>"
    labels, vals = zip(*points)
    n = len(vals)
    inner_w = width - 2*pad
    inner_h = height - 2*pad
    gap = 10
    top_h = max(60, int(inner_h * 0.62))
    bot_h = max(40, inner_h - top_h - gap)
    top_y = pad
    bot_y = pad + top_h + gap

    minv, maxv = min(vals), max(vals)
    span = (maxv - minv) or 1.0
    def sx(i): return pad + inner_w * (i/(max(n-1,1)))
    def sy(v): return top_y + top_h * (1 - (v - minv)/span)

    peak = None
    dd = []
    for v in vals:
        peak = v if (peak is None or v > peak) else peak
        dd.append(v - peak)  # negativo ou 0
    dd_min = min(dd) if dd else 0.0
    dd_span = abs(dd_min) or 1.0
    bar_w = inner_w / max(n, 1)
    rect_w = max(1.0, bar_w - 1.0)

    out = [f"<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    for val in (maxv, (minv+maxv)/2, minv):
        y = sy(val)
        out.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{width-pad}' y2='{y:.1f}' class='svg-grid'/>")
    out.append(f"<line x1='{pad}' y1='{bot_y:.1f}' x2='{width-pad}' y2='{bot_y:.1f}' class='svg-grid'/>")

    path = []
    for i, v in enumerate(vals):
        path.append(f"{'M' if i==0 else 'L'}{sx(i):.1f},{sy(v):.1f}")
    out.append(f"<path d='{' '.join(path)}' class='line' fill='none'/>")

    for i, v in enumerate(dd):
        if not v:
            continue
        x = pad + i * bar_w + 2
        h = bot_h * (abs(v) / dd_span)
        out.append(f"<rect x='{x:.1f}' y='{bot_y:.1f}' width='{bar_w-4:.1f}' height='{h:.1f}' rx='3' ry='3' class='dd-bar'/>")

    step = max(1, n // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == n-1:
            out.append(f"<text x='{sx(i):.1f}' y='{height-6}' class='lbl' text-anchor='middle'>{lab}</text>")
    out.append("</svg>")
    return "".join(out)

def _svg_drawdown_bar_chart(points, width=960, height=200, pad=28):
    if not points:
        return "<div class='small'>Sem dados para plotar.</div>"
    labels_raw, vals = zip(*points)
    n = len(vals)
    inner_w = width - 2*pad
    inner_h = height - 2*pad
    def _week_key(lab):
        s = str(lab or "").replace(".", "-")
        try:
            base = s.split("T")[0].split(" ")[0]
            d = datetime.fromisoformat(base).date()
        except Exception:
            return s
        year, week, _ = d.isocalendar()
        return f"{year}-W{week:02d}"

    peak = None
    dd_by_week = {}
    week_order = []
    for i, v in enumerate(vals):
        peak = v if (peak is None or v > peak) else peak
        dd_pct = 0.0
        if peak and peak > 0:
            dd_pct = (peak - v) / peak * 100.0
        key = _week_key(labels_raw[i])
        if key not in dd_by_week:
            dd_by_week[key] = dd_pct
            week_order.append(key)
        else:
            dd_by_week[key] = max(dd_by_week[key], dd_pct)

    labels = week_order
    dd = [dd_by_week.get(k, 0.0) for k in labels]
    m = len(dd)
    bar_w = inner_w / max(m, 1)
    rect_w = max(10.0, bar_w * 0.85)

    maxv = max([0.0] + dd)
    span = maxv or 1.0
    base_y = pad + inner_h
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    out.append(f"<defs><linearGradient id='ddGrad' x1='0' y1='{pad}' x2='0' y2='{base_y:.1f}' gradientUnits='userSpaceOnUse'><stop offset='0%' stop-color='#fecaca'/><stop offset='100%' stop-color='#dc2626'/></linearGradient></defs>")
    for val in (maxv, maxv/2, 0):
        y = pad + inner_h * (1 - (val / span))
        out.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{width-pad}' y2='{y:.1f}' class='svg-grid'/>")
        if val > 0:
            out.append(f"<text x='{pad-6}' y='{y+4:.1f}' class='tick' text-anchor='end'>{int(val)}%</text>")

    for i, v in enumerate(dd):
        if not v:
            continue
        x = pad + i * bar_w + (bar_w - rect_w) / 2
        h = inner_h * (v / span)
        y = base_y - h
        opacity = 0.35 + 0.65 * (v / span)
        out.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{rect_w:.1f}' height='{h:.1f}' rx='2' ry='2' class='dd-bar' fill='url(#ddGrad)' opacity='{opacity:.2f}'/>")

    step = max(1, m // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == m-1:
            tx = pad + i * bar_w + bar_w/2
            out.append(f"<text x='{tx:.1f}' y='{height-6}' class='lbl' text-anchor='middle'>{lab}</text>")
    out.append("</svg>")
    return "".join(out)

def _svg_pie_chart(data, width=260, height=220, colors=None, pad_angle=6, inner_ratio=0.62):
    if not data:
        return "<div class='small'>Sem dados para plotar.</div>"
    total = sum(float(v or 0) for _, v in data)
    if total <= 0:
        return "<div class='small'>Sem dados para plotar.</div>"
    if not colors:
        colors = ["#f59e0b","#f97316","#ef4444","#ec4899","#a855f7","#6366f1","#3b82f6","#14b8a6","#22c55e","#84cc16"]
    cx = width / 2
    cy = height / 2
    r = min(width, height) / 2 - 6
    r0 = max(1, r * inner_ratio)
    start = -90.0
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    for i, (label, val) in enumerate(data):
        v = float(val or 0)
        if v <= 0:
            continue
        ang = (v / total) * 360.0
        slice_pad = min(pad_angle, max(0.0, ang - 0.5))
        a_start = start + slice_pad / 2
        a_end = start + ang - slice_pad / 2
        if a_end <= a_start:
            start += ang
            continue
        a0 = math.radians(a_start)
        a1 = math.radians(a_end)
        x0 = cx + r * math.cos(a0)
        y0 = cy + r * math.sin(a0)
        x1 = cx + r * math.cos(a1)
        y1 = cy + r * math.sin(a1)
        x2 = cx + r0 * math.cos(a1)
        y2 = cy + r0 * math.sin(a1)
        x3 = cx + r0 * math.cos(a0)
        y3 = cy + r0 * math.sin(a0)
        large = 1 if (a_end - a_start) > 180 else 0
        color = colors[i % len(colors)]
        out.append(
            f"<path d='M {x0:.1f} {y0:.1f} "
            f"A {r:.1f} {r:.1f} 0 {large} 1 {x1:.1f} {y1:.1f} "
            f"L {x2:.1f} {y2:.1f} "
            f"A {r0:.1f} {r0:.1f} 0 {large} 0 {x3:.1f} {y3:.1f} Z' "
            f"fill='{color}' opacity='0.95'/>"
        )
        start += ang
    out.append("</svg>")
    return "".join(out)

def _pie_legend_html(data, colors=None):
    if not data:
        return ""
    total = sum(float(v or 0) for _, v in data) or 1.0
    if not colors:
        colors = ["#f59e0b","#f97316","#ef4444","#ec4899","#a855f7","#6366f1","#3b82f6","#14b8a6","#22c55e","#84cc16"]
    items = []
    for i, (label, val) in enumerate(data):
        v = float(val or 0)
        pct = v / total * 100.0
        color = colors[i % len(colors)]
        items.append(
            "<div class='pie-legend-item'>"
            f"<span class='pie-dot' style='background:{color}'></span>"
            f"<span class='pie-label'>{html.escape(str(label))}</span>"
            f"<span class='pie-pct'>{pct:.1f}%</span>"
            "</div>"
        )
    return "<div class='pie-legend'>" + "".join(items) + "</div>"

def _svg_line_chart(points, width=960, height=220, pad=28):
    if not points:
        return "<div class='small'>Sem dados para plotar.</div>"
    labels, vals = zip(*points)
    n = len(vals)
    minv, maxv = min(vals), max(vals)
    span = (maxv - minv) or 1.0
    inner_w = width - 2*pad
    inner_h = height - 2*pad
    def sx(i): return pad + inner_w * (i/(max(n-1,1)))
    def sy(v): return pad + inner_h * (1 - (v - minv)/span)
    d = []
    for i, v in enumerate(vals):
        d.append(f"{'M' if i==0 else 'L'}{sx(i):.1f},{sy(v):.1f}")
    lines = [f"<svg viewBox='0 0 {width} {height}' class='svg'>"]
    for val in (maxv, (minv+maxv)/2, minv):
        y = sy(val)
        lines.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{width-pad}' y2='{y:.1f}' class='svg-grid'/>")
        lines.append(f"<text x='{pad-6}' y='{y+4:.1f}' class='tick' text-anchor='end'>{_fmoney(val)}</text>")
    lines.append(f"<path d='{' '.join(d)}' class='line' fill='none'/>")
    step = max(1, n // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == n-1:
            lines.append(f"<text x='{sx(i):.1f}' y='{height-6}' class='lbl' text-anchor='middle'>{lab}</text>")
    lines.append("</svg>")
    return "".join(lines)

def _smooth_path(points: List[Tuple[float, float]]) -> str:
    if not points:
        return ""
    if len(points) == 1:
        x, y = points[0]
        return f"M{x:.1f},{y:.1f}"
    d = []
    x0, y0 = points[0]
    d.append(f"M{x0:.1f},{y0:.1f}")
    n = len(points)
    for i in range(n - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < n else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        d.append(f"C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)

def _ema(values: List[float], alpha: float = 0.25) -> List[float]:
    if not values:
        return []
    out = [values[0]]
    a = alpha
    for i in range(1, len(values)):
        out.append(a * values[i] + (1 - a) * out[i - 1])
    return out

def _svg_equity_chart(points, width=960, height=260, pad=32, annotate=None):
    if not points:
        return "<div class='small'>Sem dados de equity.</div>"
    labels, vals = zip(*points)
    n = len(vals)
    vals_raw = [float(v) for v in vals]
    vals = _ema(vals_raw, 0.25)
    minv, maxv = min(vals_raw), max(vals_raw)
    span = (maxv - minv) or 1.0
    inner_w = width - 2*pad
    inner_h = height - 2*pad
    def sx(i): return pad + inner_w * (i/(max(n-1,1)))
    def sy(v): return pad + inner_h * (1 - (v - minv)/span)
    pts = [(sx(i), sy(v)) for i, v in enumerate(vals)]
    path = _smooth_path(pts)
    hwm = []
    peak = None
    for i, v in enumerate(vals):
        peak = v if (peak is None or v > peak) else peak
        hwm.append(f"{'M' if i==0 else 'L'}{sx(i):.1f},{sy(peak):.1f}")
    dd_poly = ""
    if annotate and annotate.get("from") and annotate.get("to"):
        try:
            i0 = next(i for i,(lab,_) in enumerate(points) if lab == annotate["from"])
            i1 = next(i for i,(lab,_) in enumerate(points) if lab == annotate["to"])
            if i1 < i0: i0, i1 = i1, i0
            up, down = [], []
            peak = None
            for i in range(n):
                peak = vals[i] if (peak is None or vals[i] > peak) else peak
                if i0 <= i <= i1:
                    up.append(f"{sx(i):.1f},{sy(peak):.1f}")
                    down.append(f"{sx(i):.1f},{sy(vals[i]):.1f}")
            pts = " ".join(up + down[::-1])
            dd_poly = f"<polygon points='{pts}' class='bad'/>"
        except StopIteration:
            pass
    base_y = pad + inner_h
    area_path = path + f" L{sx(n-1):.1f},{base_y:.1f} L{sx(0):.1f},{base_y:.1f} Z"
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    out.append("<defs><linearGradient id='eqGradient' x1='0' y1='{0}' x2='0' y2='{1}' gradientUnits='userSpaceOnUse'><stop offset='0%' stop-color='#22c55e' stop-opacity='0.25'/><stop offset='100%' stop-color='#22c55e' stop-opacity='0.00'/></linearGradient></defs>".format(pad, f"{base_y:.1f}"))
    for val in (maxv, (minv+maxv)/2, minv):
        y = sy(val)
        out.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{width-pad}' y2='{y:.1f}' class='svg-grid'/>")
    out.append(f"<path d='{area_path}' fill='url(#eqGradient)'/>")
    if dd_poly: out.append(dd_poly)
    out.append(f"<path d='{path}' class='eq-line'/>")
    out.append(f"<path d='{' '.join(hwm)}' class='hwm-line'/>")
    step = max(1, n // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == n-1:
            out.append(f"<text x='{sx(i):.1f}' y='{height-6}' class='lbl' text-anchor='middle'>{lab}</text>")
    if annotate:
        txt = f"Max DD: {_fmoney(annotate.get('dd_abs',0))} ({_fpct(annotate.get('dd_pct',0))})"
        out.append(f"<text x='{width-pad}' y='{pad+14}' class='annot' text-anchor='end'>{txt}</text>")
    out.append("</svg>")
    return "".join(out)

def _svg_equity_with_flows(points, deposits, withdrawals, width=960, height=260, pad=32):
    if not points:
        return "<div class='small'>Sem dados de equity.</div>"
    def _lab(s):
        s = str(s)
        return s.split("T")[0] if "T" in s else s.split(" ")[0]
    eq_by_day = {}
    for (t, v) in points:
        eq_by_day[_lab(t)] = float(v)
    dep_by_day, wdr_by_day = {}, {}
    for (d, v) in (deposits or []):
        dep_by_day[_lab(d)] = dep_by_day.get(_lab(d), 0.0) + float(v)
    for (d, v) in (withdrawals or []):
        wdr_by_day[_lab(d)] = wdr_by_day.get(_lab(d), 0.0) + float(v)
    all_days = sorted(set(eq_by_day) | set(dep_by_day) | set(wdr_by_day))
    if not all_days:
        return "<div class='small'>Sem dados de equity.</div>"
    labels, vals, last = [], [], None
    for day in all_days:
        if day in eq_by_day:
            last = eq_by_day[day]
        elif last is None:
            try:
                first_val = next(iter(eq_by_day.values()))
            except StopIteration:
                first_val = 0.0
            last = first_val
        labels.append(day); vals.append(float(last))
    n = len(labels)
    minv, maxv = min(vals), max(vals)
    span = (maxv - minv) or 1.0
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    def sx(i): return pad + inner_w * (i / max(n - 1, 1))
    def sy(v): return pad + inner_h * (1 - (v - minv) / span)
    idx = {lab: i for i, lab in enumerate(labels)}
    max_flow = max([v for v in dep_by_day.values()] + [v for v in wdr_by_day.values()] + [1.0])
    bars_h = inner_h * 0.30
    def fh(v): return bars_h * (float(v) / max_flow)
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    for val in (maxv, (minv + maxv) / 2, minv):
        y = sy(val)
        out.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{width - pad}' y2='{y:.1f}' style='stroke:#213040;stroke-width:1'/>")
    base_y = pad + inner_h
    col_w = inner_w / max(n, 1)
    bar_w = col_w * 0.6
    for day, v in dep_by_day.items():
        i = idx.get(day)
        if i is None: 
            continue
        x = sx(i) - bar_w / 2
        h = fh(v)
        out.append(f"<rect x='{x:.1f}' y='{base_y - h:.1f}' width='{bar_w:.1f}' height='{h:.1f}' style='fill:#7ddc82;opacity:.5'/>")
    for day, v in wdr_by_day.items():
        i = idx.get(day)
        if i is None: 
            continue
        x = sx(i) - bar_w / 2
        h = fh(v)
        out.append(f"<rect x='{x:.1f}' y='{base_y - h:.1f}' width='{bar_w:.1f}' height='{h:.1f}' style='fill:#ff8a8a;opacity:.5'/>")
    path = []
    for i, v in enumerate(vals):
        path.append(f"{'M' if i == 0 else 'L'}{sx(i):.1f},{sy(v):.1f}")
    out.append(f"<path d='{' '.join(path)}' style='stroke:#87bfff;stroke-width:2;fill:none'/>")
    step = max(1, n // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == n - 1:
            out.append(f"<text x='{sx(i):.1f}' y='{height - 6}' style='font-size:11px;fill:#9db9d6' text-anchor='middle'>{lab}</text>")
    out.append("</svg>")
    return "".join(out)

# =========================
# Monte Carlo (HTML)
# =========================
def _img_to_base64(p: str | None) -> str | None:
    if not p:
        return None
    try:
        path = Path(p).resolve()
        if not path.exists():
            return None
        data = path.read_bytes()
        # Detect mime type roughly
        suffix = path.suffix.lower()
        mime = "image/png"
        if suffix in (".svg",):
            mime = "image/svg+xml"
        elif suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None

def _fmt_month(key:str) -> str:
    try:
        y, m = key.split("-")
        mname = calendar.month_abbr[int(m)].capitalize()
        return f"{mname}/{y}"
    except Exception:
        return key

def _html_monte_carlo(mc: dict | None) -> str:
    if not mc:
        return ""
    fe = mc.get("final_equity", {})
    dd = mc.get("max_drawdown", {})
    fp = mc.get("final_pnl", {})
    cfg = mc.get("config", {})
    fan_url = _img_to_base64(mc.get("plots", {}).get("fan_chart"))
    dd_url  = _img_to_base64(mc.get("plots", {}).get("dd_hist"))
    rows = mc.get("table") or []
    table_html = ""
    if rows:
        table_html = [
            '<table class="mc-table">',
            "<thead><tr><th>Métrica</th><th>Valor</th></tr></thead>",
            "<tbody>",
        ]
        for r in rows:
            table_html.append(f"<tr><td>{html.escape(str(r.get('Métrica','')))}</td>"
                              f"<td>{html.escape(str(r.get('Valor','')))}</td></tr>")
        table_html.append("</tbody></table>")
        table_html = "\n".join(table_html)
    highlights = f"""
    <div class="mc-cards">
      <div class="mc-card"><div class="mc-k">Mediana Equity Final</div><div class="mc-v">{fe.get('median',0):,.2f}</div></div>
      <div class="mc-card"><div class="mc-k">DD p95</div><div class="mc-v">{(dd.get('p95',0)*100):.1f}%</div></div>
      <div class="mc-card"><div class="mc-k">VaR@5%</div><div class="mc-v">{fp.get('var@5%',0):,.2f}</div></div>
      <div class="mc-card"><div class="mc-k">ES@5%</div><div class="mc-v">{fp.get('es@5%',0):,.2f}</div></div>
    </div>
    """
    imgs = []
    if fan_url:
        imgs.append(f'<figure class="mc-fig"><img src="{fan_url}" alt="Monte Carlo Fan Chart"><figcaption>Monte Carlo – Fan Chart</figcaption></figure>')
    if dd_url:
        imgs.append(f'<figure class="mc-fig"><img src="{dd_url}" alt="Distribuição do Máx. Drawdown"><figcaption>Distribuição do Máx. Drawdown</figcaption></figure>')
    imgs_html = "\n".join(imgs)
    method = cfg.get("method","?")
    n_trades = cfg.get("n_trades","?")
    iterations = cfg.get("iterations","?")
    risk_pct = cfg.get("risk_pct","?")
    note = f"""
    <p class="mc-note">
      Simulação baseada nos seus trades: 1R = mediana dos trades perdedores (ou risco por trade se disponível).
      Parâmetros: <b>{iterations}</b> iterações, horizonte <b>{n_trades}</b> trades, método <b>{method}</b>, risco/trade ≈ <b>{risk_pct}</b>.
    </p>
    """
    css = """
    <style>
      .mc-section { margin-top: 18px; }
      .mc-title { font-size: 22px; margin: 0 0 10px; color:#9ed0ff; }
      .mc-cards { display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 10px; margin: 12px 0 18px; }
      .mc-card { background:#0f141b; border:1px solid #1d2a38; border-radius:10px; padding:10px 12px; color:#e8eef4; }
      .mc-k { font-size:12px; color:#9db9d6; letter-spacing:.2px; }
      .mc-v { font-size:18px; font-weight:700; color:#e8eef4; }
      .mc-grid { display:grid; grid-template-columns: 1.2fr 1fr; gap: 18px; align-items:start; }
      .mc-fig { background:#0f141b; border:1px solid #1d2a38; border-radius:12px; padding:8px; margin:0 0 12px; }
      .mc-fig img { width:100%; height:auto; border:none; border-radius:8px; background:#ffffff; }
      .mc-fig figcaption { color:#9db9d6; font-size:12px; margin-top:6px; }
      .mc-table { width:100%; border-collapse: collapse; margin-top: 4px; color:#e8eef4; background:#0f141b; }
      .mc-table th, .mc-table td { border:1px solid #223041; padding:8px 10px; font-size: 13px; }
      .mc-table th { background:#111822; color:#9ed0ff; text-align:left; }
      .mc-note { font-size: 12px; color:#9db9d6; margin-top:10px; }
      @media (max-width: 900px) {
        .mc-cards { grid-template-columns: repeat(2, minmax(160px, 1fr)); }
        .mc-grid { grid-template-columns: 1fr; }
      }
      @media print {
        .mc-cards { grid-template-columns: repeat(4, 1fr); }
        .mc-grid { grid-template-columns: 1.2fr 1fr; }
      }
    </style>
    """
    return f"""
    <section class="mc-section card">
      {css}
      <h2 class="mc-title">Simulação Monte Carlo</h2>
      {highlights}
      <div class="mc-grid">
        <div>{imgs_html}</div>
        <div>{table_html}{note}</div>
      </div>
    </section>
    """

# =========================
# Renderizador principal
# =========================




def render_html(summary: dict, out_html: Path) -> Path:
    acc = summary.get("account", {}) or {}
    met = summary.get("metrics", {}) or {}
    qual = summary.get("quality", {}) or {}
    pt = summary.get("period_tables", {}) or {}
    dist = summary.get("distribution", {}) or {}
    flows = summary.get("flows_summary", {}) or {}
    val = summary.get("validation", {}) or {}
    mc = summary.get("monte_carlo") or {}

    period = summary.get("period", {}) or {}
    since_iso = period.get("since") or ""
    until_iso = period.get("until") or ""
    period_label = ""
    if since_iso or until_iso:
        period_label = f"{_fmt_date_br(since_iso)} a {_fmt_date_br(until_iso)}"
    else:
        period_label = "N/D"

    report_date = _fmt_date_iso(until_iso) or _fmt_date_iso(since_iso) or datetime.utcnow().strftime("%Y-%m-%d")
    currency = acc.get("currency") or ""
    equity_now = summary.get("equity_now", val.get("equity_now", 0))

    # Variacao do periodo
    start_balance = val.get("balance_start_est")
    delta_balance = val.get("balance_delta_period")
    if start_balance in (None, 0):
        try:
            start_balance = float(equity_now or 0) - float(met.get("net_pnl") or 0)
        except Exception:
            start_balance = 0.0
    if delta_balance is None:
        delta_balance = met.get("net_pnl")
    variation_pct = None
    try:
        if start_balance:
            variation_pct = (float(delta_balance or 0) / float(start_balance)) * 100.0
    except Exception:
        variation_pct = None
    variation_class = "positive" if (variation_pct is not None and variation_pct >= 0) else "negative"
    variation_text = _fpct1(variation_pct) if variation_pct is not None else "N/D"

    # Resumo
    trades = int(met.get("trades") or 0)
    win_rate = _fpct1(met.get("win_rate") or 0)
    dd = summary.get("drawdown", {}) or {}
    dd_pct = dd.get("max_balance_pct")
    if dd_pct is None:
        dd_pct = qual.get("max_dd_pct_curve")
    if dd_pct is None:
        dd_pct = met.get("max_dd_pct")
    dd_pct_text = _fpct1(dd_pct) if dd_pct is not None else "N/D"

    dd_abs = dd.get("max_balance")
    if dd_abs is None:
        dd_abs = qual.get("max_dd_abs_curve")
    if dd_abs is None:
        dd_abs = met.get("max_dd_abs")

    deposits = val.get("flows_period_deposits")
    withdrawals = val.get("flows_period_withdrawals")
    if deposits is None:
        deposits = flows.get("total_deposits")
    if withdrawals is None:
        withdrawals = flows.get("total_withdrawals")

    # Icons
    base_dir = Path(__file__).resolve().parent
    icons_dir = base_dir / "icons"
    if not icons_dir.exists():
        # Fallback for different execution contexts
        icons_dir = Path(r"c:\Users\Administrator\Documents\RiskGuardV1\RiskguardV1.1\reports\icons")
    
    ic_tr = _img_to_base64(str(icons_dir / "trades.svg"))
    ic_wr = _img_to_base64(str(icons_dir / "winrate.svg"))
    ic_dd = _img_to_base64(str(icons_dir / "drawdown.svg"))
    ic_in = _img_to_base64(str(icons_dir / "depositos.svg"))
    ic_out = _img_to_base64(str(icons_dir / "saques.svg"))

    def _render_icon(b64, fallback):
        if b64:
            return f"<img src='{b64}' class='summary-icon-img' alt='{fallback}'>"
        return fallback

    # Curva de equity
    eq_points = []
    ts = summary.get("timeseries", {})
    eq_list = ts.get("equity") or []
    for (t, v) in eq_list:
        lab = (t.split("T")[0] if isinstance(t, str) and "T" in t else str(t)) or "?"
        eq_points.append((lab, float(v)))

    dd_info = summary.get("quality", {})
    annot = {
        "dd_abs": dd_abs or 0,
        "dd_pct": dd_pct or 0,
        "from": (dd_info.get("max_dd_window", {}) or {}).get("from"),
        "to": (dd_info.get("max_dd_window", {}) or {}).get("to"),
    }

    # Distribuicoes
    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    wd = dist.get("by_weekday", {}) or {}
    weekday_data = [(d, float(wd.get(d, 0) or 0)) for d in order if d in wd]
    hr = dist.get("by_hour", {}) or {}
    def _hkey(k):
        try:
            return int(str(k).replace("h", ""))
        except Exception:
            return 0
    hour_data = sorted([(k, float(v or 0)) for k, v in hr.items()], key=lambda kv: _hkey(kv[0]))

    # Tabelas mensal / semanal
    monthly = pt.get("monthly", {}) or {}
    weekly = pt.get("weekly", {}) or {}
    monthly_data = list(monthly.items())
    weekly_data = list(weekly.items())

    # Top simbolos
    top_syms = list((met.get("pnl_by_symbol", {}) or {}).items())[:10]
    trades_by_symbol = (met.get("trades_by_symbol", {}) or {})

    # Dados das pizzas
    long_total = (q.get("longs_won", {}) or {}).get("total", 0) or 0
    short_total = (q.get("shorts_won", {}) or {}).get("total", 0) or 0
    pie_long_short = [("Long", long_total), ("Short", short_total)]

    pie_win_loss = [("Win", met.get("wins", 0)), ("Loss", met.get("losses", 0))]

    trade_counts = sorted(trades_by_symbol.items(), key=lambda kv: -kv[1])
    top_trade = trade_counts[:5]
    total_trades_count = sum(v for _, v in trade_counts)
    other_trades = max(0, total_trades_count - sum(v for _, v in top_trade))
    pie_symbols = top_trade + ([("Others", other_trades)] if other_trades > 0 else [])

    pnl_by_symbol = list((met.get("pnl_by_symbol", {}) or {}).items())
    pnl_sorted = sorted(pnl_by_symbol, key=lambda kv: -abs(kv[1]))
    top_pnl = pnl_sorted[:5]
    total_abs_pnl = sum(abs(v) for _, v in pnl_sorted)
    top_abs_pnl = sum(abs(v) for _, v in top_pnl)
    other_pnl = max(0.0, total_abs_pnl - top_abs_pnl)
    pie_pnl = [(k, abs(v)) for k, v in top_pnl] + ([("Others", other_pnl)] if other_pnl > 0 else [])
    exp_payoff = qual.get("expected_payoff", qual.get("expectancy", 0))
    payoff_ratio = qual.get("payoff_ratio")

    # Monte Carlo
    mc_available = bool(mc)
    fan_url = _img_to_base64((mc.get("plots", {}) or {}).get("fan_chart")) if mc_available else None
    dd_url = _img_to_base64((mc.get("plots", {}) or {}).get("dd_hist")) if mc_available else None
    mc_dd_p95 = None
    mc_prob_ruin = None
    mc_var5 = None
    mc_median_eq = None
    if mc_available:
        try:
            mc_dd_p95 = float((mc.get("max_drawdown", {}) or {}).get("p95")) * 100.0
        except Exception:
            mc_dd_p95 = None
        try:
            mc_prob_ruin = float(mc.get("prob_ruin_peak")) * 100.0
        except Exception:
            mc_prob_ruin = None
        try:
            mc_var5 = float((mc.get("final_pnl", {}) or {}).get("var@5%"))
        except Exception:
            mc_var5 = None
        try:
            mc_median_eq = float((mc.get("final_equity", {}) or {}).get("median"))
        except Exception:
            mc_median_eq = None

    # Qualidade (format helpers)
    q = qual or {}
    def _fmt_rate(x):
        return "N/D" if x is None else f"{float(x):.1f}%"
    def _fmt_pips(x):
        return "N/D" if x is None else f"{float(x):.1f} pips"
    def _fmt_winstat(obj):
        if not obj or not obj.get("total"):
            return "N/D"
        return f"{obj.get('wins',0)}/{obj.get('total',0)} ({_fmt_rate(obj.get('rate'))})"
    def _fmt_trade_val(tr):
        if not tr:
            return "N/D"
        dt = tr.get("end")
        dt_txt = _fmt_date_br(dt) if dt else ""
        val = _fmoney(tr.get("pnl"))
        return f"({dt_txt}) {val}" if dt_txt else val
    def _fmt_trade_pips(tr):
        if not tr:
            return "N/D"
        dt = tr.get("end")
        dt_txt = _fmt_date_br(dt) if dt else ""
        val = _fmt_pips(tr.get("pips"))
        return f"({dt_txt}) {val}" if dt_txt else val

    html_parts = []
    html_parts.append("<!doctype html><html><head><meta charset='utf-8'>")
    html_parts.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    html_parts.append(f"<title>RiskGuard Report - {acc.get('login','?')}</title>")
    html_parts.append(f"<style>{CSS}</style></head><body><div class='wrap'>")

    def _render_header(show_balance: bool) -> None:
        html_parts.append("<div class='header-card'>")
        html_parts.append("<div class='header-block'>")
        html_parts.append("<div class='header-top'>")
        html_parts.append("<div class='brand'>")
        html_parts.append("<div class='logo'>RG</div>")
        html_parts.append("<div class='brand-name'>RiskGuard</div>")
        html_parts.append("</div>")
        html_parts.append("<div class='date-box'>")
        html_parts.append("<div class='date-pill'>" + html.escape(str(report_date)) + "</div>")
        html_parts.append("</div>")
        html_parts.append("</div>")
        html_parts.append("<div class='title'>Relat&#243;rio de Performance</div>")
        html_parts.append(
            "<div class='subtitle'>[" +
            html.escape(str(acc.get('server','') or '')) +
            " / Login " + html.escape(str(acc.get('login','') or '')) + "]</div>"
        )
        html_parts.append("</div>")
        html_parts.append("<div class='period-bar'>")
        html_parts.append("<div class='period-left'>")
        html_parts.append("<div>Per&#237;odo: <b>" + html.escape(period_label) + "</b></div>")
        html_parts.append("<div>Moeda: <b>" + html.escape(str(currency)) + "</b></div>")
        html_parts.append("</div>")
        if show_balance:
            html_parts.append("<div class='meta-right'>")
            html_parts.append("<div class='balance'>" + _fmoney(equity_now) + "</div>")
            html_parts.append("<div class='variation " + variation_class + "'>" + html.escape(variation_text) + "</div>")
            html_parts.append("</div>")
        html_parts.append("</div>")
        html_parts.append("</div>")

    # Page 1
    html_parts.append("<div class='page'>")
    _render_header(show_balance=True)

    # Resumo + Curva
    html_parts.append("<div class='grid grid-3 section'>")
    html_parts.append("<div class='card'>")
    html_parts.append("<div class='card-title'>Resumo</div>")
    html_parts.append("<div class='summary-list'>")
    html_parts.append("<div class='summary-item'><div class='summary-icon'>" + _render_icon(ic_tr, "TR") + "</div><div class='summary-label'>Trades</div><div class='summary-value'>" + html.escape(str(trades)) + "</div></div>")
    html_parts.append("<div class='summary-item'><div class='summary-icon'>" + _render_icon(ic_wr, "WR") + "</div><div class='summary-label'>Win rate</div><div class='summary-value'>" + html.escape(win_rate) + "</div></div>")
    html_parts.append("<div class='summary-item'><div class='summary-icon'>" + _render_icon(ic_dd, "DD") + "</div><div class='summary-label'>DD m&#225;ximo</div><div class='summary-value negative'>" + html.escape(dd_pct_text) + "</div></div>")
    html_parts.append("<div class='summary-item'><div class='summary-icon'>" + _render_icon(ic_in, "IN") + "</div><div class='summary-label'>Dep&#243;sitos</div><div class='summary-value'>" + _fmoney(deposits or 0) + "</div></div>")
    html_parts.append("<div class='summary-item'><div class='summary-icon'>" + _render_icon(ic_out, "OUT") + "</div><div class='summary-label'>Saques</div><div class='summary-value'>" + _fmoney(withdrawals or 0) + "</div></div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    html_parts.append("<div class='card span-2'>")
    html_parts.append("<div class='card-title'>Curva de Equity</div>")
    if eq_points:
        html_parts.append(_svg_equity_chart(eq_points, height=300, annotate=annot))
    else:
        html_parts.append("<div class='chart-placeholder'>Sem dados de equity.</div>")
    html_parts.append("<div class='legend'>")
    html_parts.append("<div class='legend-item'><span class='legend-line'></span><span>Equity</span></div>")
    html_parts.append("<div class='legend-item'><span class='legend-line gray'></span><span>HWM</span></div>")
    dd_label = "Max. DD " + _fmoney(dd_abs or 0) + " (" + (_fpct1(dd_pct) if dd_pct is not None else "N/D") + ")"
    html_parts.append("<div class='legend-item'><span class='legend-line red'></span><span class='negative'>" + html.escape(dd_label) + "</span></div>")
    html_parts.append("</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    # Drawdown (barras)
    html_parts.append("<div class='card section'>")
    html_parts.append("<div class='card-title'>Drawdown (Percentual)</div>")
    if eq_points:
        html_parts.append(_svg_drawdown_bar_chart(eq_points, height=200))
    else:
        html_parts.append("<div class='chart-placeholder'>Sem dados.</div>")
    html_parts.append("</div>")

    # Distribuicao DD + Monte Carlo
    html_parts.append("<div class='grid grid-2 section'>")
    html_parts.append("<div class='card'>")
    html_parts.append("<div class='card-title'>Distribui&#231;&#227;o do M&#225;x. Drawdown</div>")
    if dd_url:
        html_parts.append("<img class='chart-img chart-img--dd' src='" + dd_url + "' alt='DD distribution'>")
    else:
        html_parts.append("<div class='chart-placeholder'>Distribui&#231;&#227;o indispon&#237;vel.</div>")
    html_parts.append("<div class='section-gap'>")
    html_parts.append("<div class='summary-item'><div class='summary-label'>M&#225;x. DD p95</div><div class='summary-value'>" + (_fpct1(mc_dd_p95) if mc_dd_p95 is not None else "N/D") + "</div></div>")
    html_parts.append("<div class='summary-item'><div class='summary-label'>Prob. ru&#237;na (por pico)</div><div class='summary-value'>" + (_fpct1(mc_prob_ruin) if mc_prob_ruin is not None else "N/D") + "</div></div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    html_parts.append("<div class='card'>")
    html_parts.append("<div class='card-title'>Simula&#231;&#227;o Monte Carlo</div>")
    if fan_url:
        html_parts.append("<img class='chart-img chart-img--mc' src='" + fan_url + "' alt='Monte Carlo'>")
    else:
        html_parts.append("<div class='chart-placeholder'>Monte Carlo indispon&#237;vel.</div>")
    html_parts.append("<div class='grid grid-2 section-gap'>")
    html_parts.append("<div><div class='muted'>VaR@5%</div><div class='summary-sub'>" + (_fmoney(mc_var5) if mc_var5 is not None else "N/D") + "</div></div>")
    html_parts.append("<div><div class='muted'>Median Equity Final</div><div class='summary-sub'>" + (_fmoney(mc_median_eq) if mc_median_eq is not None else "N/D") + "</div></div>")
    html_parts.append("</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    # Monte Carlo summary row (sem duplicar gr??fico)
    if mc_available:
        html_parts.append("<div class='card mc-summary section'>")
        html_parts.append("<div>")
        html_parts.append("<div class='summary-item'><div class='summary-label'>M&#225;x. DD p95</div><div class='summary-value'>" + (_fpct1(mc_dd_p95) if mc_dd_p95 is not None else "N/D") + "</div></div>")
        html_parts.append("<div class='summary-item'><div class='summary-label'>Prob. ru&#237;na (por pico)</div><div class='summary-value'>" + (_fpct1(mc_prob_ruin) if mc_prob_ruin is not None else "N/D") + "</div></div>")
        html_parts.append("</div>")
        html_parts.append("<div>")
        html_parts.append("<div class='summary-item'><div class='summary-label'>VaR@5%</div><div class='summary-value'>" + (_fmoney(mc_var5) if mc_var5 is not None else "N/D") + "</div></div>")
        html_parts.append("<div class='summary-item'><div class='summary-label'>Median Equity Final</div><div class='summary-value'>" + (_fmoney(mc_median_eq) if mc_median_eq is not None else "N/D") + "</div></div>")
        html_parts.append("</div>")
        html_parts.append("</div>")

    # Qualidade (logo abaixo do bloco de Monte Carlo)
    html_parts.append("<div class='card section'>")
    html_parts.append("<div class='card-title'>Qualidade</div>")
    html_parts.append("<div class='split-table-3'>")
    # Coluna 1
    html_parts.append("<div class='subcard'>")
    html_parts.append("<table class='data-table'><tbody>")
    html_parts.append("<tr><td>Trades</td><td class='right'>" + html.escape(str(trades)) + "</td></tr>")
    html_parts.append("<tr><td>Profitability</td><td class='right'>" + html.escape(_fmt_rate(met.get("win_rate"))) + "</td></tr>")
    html_parts.append("<tr><td>Pips</td><td class='right'>" + html.escape(_fmt_pips(q.get("pips_total"))) + "</td></tr>")
    html_parts.append("<tr><td>Average Win</td><td class='right'>" + html.escape(_fmt_pips(q.get("avg_win_pips"))) + " / " + _fmoney(qual.get("avg_win", 0)) + "</td></tr>")
    html_parts.append("<tr><td>Average Loss</td><td class='right'>" + html.escape(_fmt_pips(q.get("avg_loss_pips"))) + " / " + _fmoney(qual.get("avg_loss", 0)) + "</td></tr>")
    html_parts.append("<tr><td>Lots</td><td class='right'>" + (f"{float(q.get('lots_total') or 0):.2f}" if q.get('lots_total') is not None else "N/D") + "</td></tr>")
    html_parts.append("<tr><td>Commissions</td><td class='right'>" + _fmoney(q.get("commissions_total") or 0) + "</td></tr>")
    html_parts.append("</tbody></table></div>")
    # Coluna 2
    html_parts.append("<div class='subcard'>")
    html_parts.append("<table class='data-table'><tbody>")
    html_parts.append("<tr><td>Longs Won</td><td class='right'>" + html.escape(_fmt_winstat(q.get("longs_won"))) + "</td></tr>")
    html_parts.append("<tr><td>Shorts Won</td><td class='right'>" + html.escape(_fmt_winstat(q.get("shorts_won"))) + "</td></tr>")
    html_parts.append("<tr><td>Best Trade (£)</td><td class='right'>" + html.escape(_fmt_trade_val(q.get("best_trade"))) + "</td></tr>")
    html_parts.append("<tr><td>Worst Trade (£)</td><td class='right'>" + html.escape(_fmt_trade_val(q.get("worst_trade"))) + "</td></tr>")
    html_parts.append("<tr><td>Best Trade (Pips)</td><td class='right'>" + html.escape(_fmt_trade_pips(q.get("best_trade_pips"))) + "</td></tr>")
    html_parts.append("<tr><td>Worst Trade (Pips)</td><td class='right'>" + html.escape(_fmt_trade_pips(q.get("worst_trade_pips"))) + "</td></tr>")
    html_parts.append("<tr><td>Avg. Trade Length</td><td class='right'>" + (_seconds_to_hms(q.get("avg_trade_length_sec") or 0) if q.get("avg_trade_length_sec") is not None else "N/D") + "</td></tr>")
    html_parts.append("</tbody></table></div>")
    # Coluna 3
    html_parts.append("<div class='subcard'>")
    html_parts.append("<table class='data-table'><tbody>")
    html_parts.append("<tr><td>Profit Factor</td><td class='right'>" + (f"{float(met.get('profit_factor')):.2f}" if met.get('profit_factor') is not None else "N/D") + "</td></tr>")
    html_parts.append("<tr><td>Standard Deviation</td><td class='right'>" + (_fmoney(q.get("std_pnl")) if q.get("std_pnl") is not None else "N/D") + "</td></tr>")
    html_parts.append("<tr><td>Sharpe Ratio</td><td class='right'>" + (f"{float(q.get('sharpe')):.2f}" if q.get('sharpe') is not None else "N/D") + "</td></tr>")
    z_txt = "N/D"
    if q.get("z_score") is not None:
        z_txt = f"{float(q.get('z_score')):.2f}"
        if q.get("z_prob") is not None:
            z_txt += f" ({float(q.get('z_prob')):.2f}%)"
    html_parts.append("<tr><td>Z-Score (Probability)</td><td class='right'>" + html.escape(z_txt) + "</td></tr>")
    exp_pips = _fmt_pips(q.get("expectancy_pips"))
    html_parts.append("<tr><td>Expectancy</td><td class='right'>" + html.escape(exp_pips) + " / " + _fmoney(qual.get("expected_payoff", 0)) + "</td></tr>")
    html_parts.append("<tr><td>AHPR</td><td class='right'>" + (_fmt_rate(q.get("ahpr")) if q.get("ahpr") is not None else "N/D") + "</td></tr>")
    html_parts.append("<tr><td>GHPR</td><td class='right'>" + (_fmt_rate(q.get("ghpr")) if q.get("ghpr") is not None else "N/D") + "</td></tr>")
    html_parts.append("</tbody></table></div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    html_parts.append("</div>")  # page 1

    # Page 2
    html_parts.append("<div class='page'>")
    # Distribuicao por dia e hora
    html_parts.append("<div class='card section'>")
    html_parts.append("<div class='card-title'>Distribui&#231;&#227;o por Dia e Hora</div>")
    html_parts.append("<div class='grid grid-2'>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>PnL por Dia da Semana (USD)</div>")
    if weekday_data:
        html_parts.append(_svg_bar_chart(weekday_data, width=520, height=230, show_values=True))
    else:
        html_parts.append("<div class='chart-placeholder'>Sem dados.</div>")
    html_parts.append("</div>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>PnL por Hora do Dia (USD)</div>")
    if hour_data:
        html_parts.append(_svg_bar_chart(hour_data, width=520, height=230, show_values=True))
    else:
        html_parts.append("<div class='chart-placeholder'>Sem dados.</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    # Pizzas
    html_parts.append("<div class='card section'>")
    html_parts.append("<div class='card-title'>Distribui&#231;&#245;es (Pizza)</div>")
    html_parts.append("<div class='pie-grid'>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>Shorts vs Longs</div>")
    html_parts.append(_svg_pie_chart(pie_long_short, colors=["#22c55e","#ef4444"]))
    html_parts.append(_pie_legend_html(pie_long_short, colors=["#22c55e","#ef4444"]))
    html_parts.append("</div>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>Win vs Loss</div>")
    html_parts.append(_svg_pie_chart(pie_win_loss, colors=["#3b82f6","#f59e0b"]))
    html_parts.append(_pie_legend_html(pie_win_loss, colors=["#3b82f6","#f59e0b"]))
    html_parts.append("</div>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>S&#237;mbolos Mais Negociados</div>")
    html_parts.append(_svg_pie_chart(pie_symbols))
    html_parts.append(_pie_legend_html(pie_symbols))
    html_parts.append("</div>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>Top PnL por S&#237;mbolo (Abs)</div>")
    html_parts.append(_svg_pie_chart(pie_pnl))
    html_parts.append(_pie_legend_html(pie_pnl))
    html_parts.append("</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    # Mensal/Semanal (cards)
    html_parts.append("<div class='card section'>")
    html_parts.append("<div class='card-title'>Mensal vs Semanal (USD)</div>")
    html_parts.append("<div class='split-table'>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>Mensal (PnL $)</div>")
    if monthly_data:
        html_parts.append(_svg_bar_chart(monthly_data, width=520, height=220, show_values=True))
    else:
        html_parts.append("<div class='chart-placeholder'>Sem dados.</div>")
    html_parts.append("</div>")
    html_parts.append("<div class='subcard'>")
    html_parts.append("<div class='subcard-title'>Semanal (PnL $)</div>")
    if weekly_data:
        html_parts.append(_svg_bar_chart(weekly_data, width=520, height=220, show_values=True, rotate_labels=True))
    else:
        html_parts.append("<div class='chart-placeholder'>Sem dados.</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    # Simbolos
    html_parts.append("<div class='grid grid-2 section'>")
    html_parts.append("<div class='card span-2'>")
    html_parts.append("<div class='card-title'>Maiores PnLs por S&#237;mbolo</div>")
    html_parts.append("<table class='data-table'><thead><tr><th>S&#237;mbolo</th><th class='right'>PnL</th></tr></thead><tbody>")
    for s, v in top_syms:
        name = s or "-"
        cls = "neg" if float(v or 0) < 0 else "pos"
        html_parts.append("<tr><td>" + html.escape(str(name)) + "</td><td class='right " + cls + "'>" + _fmoney(v) + "</td></tr>")
    html_parts.append("</tbody></table>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    html_parts.append("<div class='footer'>&#169; " + datetime.utcnow().strftime("%Y") + " RiskGuard. All rights reserved.</div>")

    html_parts.append("</div>")  # page 2

    html_parts.append("</div></body></html>")
    out_html.write_text("".join(html_parts), encoding="utf-8")
    return out_html
# =========================
# CLI auxiliar
# =========================
def build_from_summary(summary_json: Path, out_html: Path) -> Path:
    data = json.loads(summary_json.read_text(encoding="utf-8"))
    return render_html(data, out_html)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--summary", required=True, help="Caminho do summary_*.json")
    p.add_argument("--out", required=False, help="Caminho do HTML de saída")
    args = p.parse_args()
    sj = Path(args.summary)
    out = Path(args.out) if args.out else sj.with_suffix(".html")
    build_from_summary(sj, out)
    print("HTML gerado em:", out)
