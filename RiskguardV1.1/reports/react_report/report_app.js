(function(){
  const h = React.createElement;

  function fmtMoney(x){
    const n = Number(x);
    if (Number.isNaN(n)) return String(x == null ? '' : x);
    const abs = Math.abs(n);
    const s = abs.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    return (n < 0 ? '-$' : '$') + s;
  }

  function fmtPct(x){
    const n = Number(x);
    if (Number.isNaN(n)) return 'N/D';
    return n.toFixed(2) + '%';
  }

  function fmtPct1(x){
    const n = Number(x);
    if (Number.isNaN(n)) return 'N/D';
    return n.toFixed(1) + '%';
  }

  function parseDate(val){
    if (!val) return null;
    const s = String(val).trim();
    if (!s) return null;
    const iso = s.replace('Z', '+00:00');
    const d = new Date(iso);
    if (!Number.isNaN(d.getTime())) return d;
    const d2 = new Date(s.split('T')[0]);
    return Number.isNaN(d2.getTime()) ? null : d2;
  }

  function fmtDateBR(val){
    const d = parseDate(val);
    if (!d) return val ? String(val) : '';
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return dd + '/' + mm + '/' + yyyy;
  }

  function fmtDateISO(val){
    const d = parseDate(val);
    if (!d) return val ? String(val) : '';
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return yyyy + '-' + mm + '-' + dd;
  }

  function toFileUrl(path){
    if (!path) return '';
    const s = String(path);
    if (s.startsWith('http://') || s.startsWith('https://') || s.startsWith('file:')) return s;
    let p = s.replace(/\\/g, '/');
    if (/^[A-Za-z]:/.test(p)){
      p = 'file:///' + p;
    }
    return encodeURI(p);
  }

  function svgBarChart(data, width, height, pad, showValues, pctMap, rotateLabels){
    if (!data || !data.length){
      return "<div class='small'>Sem dados para plotar.</div>";
    }
    const labels = data.map(d => d[0]);
    const vals = data.map(d => Number(d[1] || 0));
    const n = vals.length;
    const minv = Math.min(0, ...vals);
    const maxv = Math.max(0, ...vals);
    const span = (maxv - minv) || 1.0;
    const innerW = width - 2 * pad;
    const innerH = height - 2 * pad;
    const barW = innerW / Math.max(n, 1);
    const zeroY = pad + innerH * (maxv / span);
    const lines = [];
    lines.push("<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='" + width + "' height='" + height + "' viewBox='0 0 " + width + " " + height + "'>");
    lines.push("<line x1='" + pad + "' y1='" + zeroY.toFixed(1) + "' x2='" + (width - pad) + "' y2='" + zeroY.toFixed(1) + "' class='svg-grid' />");
    for (let i = 0; i < n; i++){
      const v = vals[i];
      const x = pad + i * barW + 2;
      const h = innerH * (Math.abs(v) / span);
      const y = v >= 0 ? zeroY - h : zeroY;
      const barClass = v < 0 ? 'bar-neg' : 'bar';
      lines.push("<rect x='" + x.toFixed(1) + "' y='" + y.toFixed(1) + "' width='" + (barW - 4).toFixed(1) + "' height='" + h.toFixed(1) + "' rx='4' ry='4' class='" + barClass + "' />");
      if (showValues){
        const lab = String(labels[i]);
        let valTxt = fmtMoney(v);
        if (pctMap && Object.prototype.hasOwnProperty.call(pctMap, lab) && pctMap[lab] !== null && pctMap[lab] !== undefined){
          valTxt = valTxt + ' (' + Number(pctMap[lab]).toFixed(2) + '%)';
        }
        const ty = v >= 0 ? (y - 4) : (y + h + 12);
        const tx = x + (barW - 4) / 2;
        lines.push("<text x='" + tx.toFixed(1) + "' y='" + ty.toFixed(1) + "' class='val' text-anchor='middle'>" + valTxt + "</text>");
      }
    }
    const step = rotateLabels ? 1 : Math.max(1, Math.floor(n / 12));
    for (let i = 0; i < n; i++){
      if (i % step === 0 || i === n - 1){
        const tx = pad + i * barW + barW / 2;
        if (rotateLabels){
          const ty = height - 4;
          lines.push("<text x='" + tx.toFixed(1) + "' y='" + ty + "' class='lbl' text-anchor='end' transform='rotate(-90 " + tx.toFixed(1) + " " + ty + ")'>" + labels[i] + "</text>");
        } else {
          lines.push("<text x='" + tx.toFixed(1) + "' y='" + (height - 6) + "' class='lbl' text-anchor='middle'>" + labels[i] + "</text>");
        }
      }
    }
    lines.push('</svg>');
    return lines.join('');
  }

  function svgDrawdownBarChart(points, width, height, pad){
    if (!points || !points.length){
      return "<div class='small'>Sem dados para plotar.</div>";
    }
    function isoWeekKey(dateObj){
      const d = new Date(Date.UTC(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate()));
      const day = d.getUTCDay() || 7;
      d.setUTCDate(d.getUTCDate() + 4 - day);
      const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
      const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
      const yyyy = d.getUTCFullYear();
      return yyyy + '-W' + String(weekNo).padStart(2, '0');
    }
    function weekKey(label){
      const dt = parseDate(label);
      if (!dt || Number.isNaN(dt.getTime())) return String(label || '');
      return isoWeekKey(dt);
    }
    const labelsRaw = points.map(p => p[0]);
    const vals = points.map(p => Number(p[1] || 0));
    const n = vals.length;
    const innerW = width - 2 * pad;
    const innerH = height - 2 * pad;
    let peak = null;
    const ddWeekly = new Map();
    const weekOrder = [];
    for (let i = 0; i < n; i++){
      const v = vals[i];
      peak = (peak === null || v > peak) ? v : peak;
      let ddPct = 0;
      if (peak && peak > 0){
        ddPct = ((peak - v) / peak) * 100.0;
      }
      const key = weekKey(labelsRaw[i]);
      if (!ddWeekly.has(key)){
        ddWeekly.set(key, ddPct);
        weekOrder.push(key);
      } else {
        ddWeekly.set(key, Math.max(ddWeekly.get(key) || 0, ddPct));
      }
    }
    const labels = weekOrder;
    const dd = labels.map(k => ddWeekly.get(k) || 0);
    const m = dd.length;
    const barW = innerW / Math.max(m, 1);
    const rectW = Math.max(8, barW * 0.8);
    const maxv = Math.max(0, ...dd);
    const span = maxv || 1.0;
    const baseY = pad + innerH;
    const lines = [];
    lines.push("<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='" + width + "' height='" + height + "' viewBox='0 0 " + width + " " + height + "'>");
    lines.push("<defs><linearGradient id='ddGrad' x1='0' y1='" + pad + "' x2='0' y2='" + baseY.toFixed(1) + "' gradientUnits='userSpaceOnUse'><stop offset='0%' stop-color='#fecaca'/><stop offset='100%' stop-color='#dc2626'/></linearGradient></defs>");
    for (const val of [maxv, maxv / 2, 0]){
      const y = pad + innerH * (1 - (val / span));
      lines.push("<line x1='" + pad + "' y1='" + y.toFixed(1) + "' x2='" + (width - pad) + "' y2='" + y.toFixed(1) + "' class='svg-grid'/>");
      if (val > 0){
        lines.push("<text x='" + (pad - 6) + "' y='" + (y + 4).toFixed(1) + "' class='tick' text-anchor='end'>" + val.toFixed(0) + "%</text>");
      }
    }
    for (let i = 0; i < m; i++){
      const v = dd[i];
      if (!v) continue;
      const x = pad + i * barW + (barW - rectW) / 2;
      const h = innerH * (v / span);
      const y = baseY - h;
      const opacity = (0.35 + 0.65 * (v / span)).toFixed(2);
      lines.push("<rect x='" + x.toFixed(1) + "' y='" + y.toFixed(1) + "' width='" + rectW.toFixed(1) + "' height='" + h.toFixed(1) + "' rx='2' ry='2' class='dd-bar' fill='url(#ddGrad)' opacity='" + opacity + "' />");
    }
    const step = Math.max(1, Math.floor(m / 10));
    for (let i = 0; i < m; i++){
      if (i % step === 0 || i === m - 1){
        const tx = pad + i * barW + barW / 2;
        lines.push("<text x='" + tx.toFixed(1) + "' y='" + (height - 6) + "' class='lbl' text-anchor='middle'>" + labels[i] + "</text>");
      }
    }
    lines.push("</svg>");
    return lines.join('');
  }

  function _smoothPath(pts){
    if (!pts || pts.length === 0) return '';
    if (pts.length === 1) return 'M' + pts[0][0].toFixed(1) + ',' + pts[0][1].toFixed(1);
    let d = 'M' + pts[0][0].toFixed(1) + ',' + pts[0][1].toFixed(1);
    for (let i = 0; i < pts.length - 1; i++){
      const p0 = i > 0 ? pts[i - 1] : pts[i];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = (i + 2 < pts.length) ? pts[i + 2] : p2;
      const c1x = p1[0] + (p2[0] - p0[0]) / 6;
      const c1y = p1[1] + (p2[1] - p0[1]) / 6;
      const c2x = p2[0] - (p3[0] - p1[0]) / 6;
      const c2y = p2[1] - (p3[1] - p1[1]) / 6;
      d += ' C' + c1x.toFixed(1) + ',' + c1y.toFixed(1) + ' ' + c2x.toFixed(1) + ',' + c2y.toFixed(1) + ' ' + p2[0].toFixed(1) + ',' + p2[1].toFixed(1);
    }
    return d;
  }

  function _ema(values, alpha){
    if (!values || values.length === 0) return [];
    const a = (alpha === undefined || alpha === null) ? 0.25 : Number(alpha);
    const out = [values[0]];
    for (let i = 1; i < values.length; i++){
      out.push(a * values[i] + (1 - a) * out[i - 1]);
    }
    return out;
  }

  function svgEquityChart(points, width, height, pad, annotate){
    if (!points || !points.length){
      return "<div class='small'>Sem dados de equity.</div>";
    }
    const labels = points.map(p => p[0]);
    const valsRaw = points.map(p => Number(p[1] || 0));
    const vals = _ema(valsRaw, 0.25);
    const n = vals.length;
    const minv = Math.min(...valsRaw);
    const maxv = Math.max(...valsRaw);
    const span = (maxv - minv) || 1.0;
    const innerW = width - 2 * pad;
    const innerH = height - 2 * pad;
    const sx = (i) => pad + innerW * (i / Math.max(n - 1, 1));
    const sy = (v) => pad + innerH * (1 - (v - minv) / span);
    const pts = [];
    for (let i = 0; i < n; i++){
      pts.push([sx(i), sy(vals[i])]);
    }
    const path = _smoothPath(pts);
    const baseY = pad + innerH;
    const areaPath = path + ' L' + sx(n - 1).toFixed(1) + ',' + baseY.toFixed(1) + ' L' + sx(0).toFixed(1) + ',' + baseY.toFixed(1) + ' Z';
    const hwm = [];
    let peak = null;
    for (let i = 0; i < n; i++){
      peak = (peak === null || vals[i] > peak) ? vals[i] : peak;
      hwm.push((i === 0 ? 'M' : 'L') + sx(i).toFixed(1) + ',' + sy(peak).toFixed(1));
    }
    let ddPoly = '';
    if (annotate && annotate.from && annotate.to){
      const i0 = labels.indexOf(annotate.from);
      const i1 = labels.indexOf(annotate.to);
      if (i0 >= 0 && i1 >= 0){
        const a0 = Math.min(i0, i1);
        const a1 = Math.max(i0, i1);
        const up = [];
        const down = [];
        let p = null;
        for (let i = 0; i < n; i++){
          p = (p === null || vals[i] > p) ? vals[i] : p;
          if (i >= a0 && i <= a1){
            up.push(sx(i).toFixed(1) + ',' + sy(p).toFixed(1));
            down.push(sx(i).toFixed(1) + ',' + sy(vals[i]).toFixed(1));
          }
        }
        const pts = up.concat(down.reverse()).join(' ');
        ddPoly = "<polygon points='" + pts + "' class='bad' />";
      }
    }
    const out = [];
    out.push("<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='" + width + "' height='" + height + "' viewBox='0 0 " + width + " " + height + "'>");
    out.push("<defs><linearGradient id='eqGradient' x1='0' y1='" + pad + "' x2='0' y2='" + baseY.toFixed(1) + "' gradientUnits='userSpaceOnUse'><stop offset='0%' stop-color='#22c55e' stop-opacity='0.25' /><stop offset='100%' stop-color='#22c55e' stop-opacity='0.00' /></linearGradient></defs>");
    const ticks = [maxv, (minv + maxv) / 2, minv];
    for (let i = 0; i < ticks.length; i++){
      const y = sy(ticks[i]);
      out.push("<line x1='" + pad + "' y1='" + y.toFixed(1) + "' x2='" + (width - pad) + "' y2='" + y.toFixed(1) + "' class='svg-grid' />");
    }
    out.push("<path d='" + areaPath + "' fill='url(#eqGradient)' />");
    if (ddPoly) out.push(ddPoly);
    out.push("<path d='" + path + "' class='eq-line' />");
    out.push("<path d='" + hwm.join(' ') + "' class='hwm-line' />");
    const step = Math.max(1, Math.floor(n / 10));
    for (let i = 0; i < n; i++){
      if (i % step === 0 || i === n - 1){
        out.push("<text x='" + sx(i).toFixed(1) + "' y='" + (height - 6) + "' class='lbl' text-anchor='middle'>" + labels[i] + "</text>");
      }
    }
    if (annotate){
      const txt = 'Max DD: ' + fmtMoney(annotate.dd_abs || 0) + ' (' + fmtPct(annotate.dd_pct || 0) + ')';
      out.push("<text x='" + (width - pad) + "' y='" + (pad + 14) + "' class='annot' text-anchor='end'>" + txt + "</text>");
    }
    out.push('</svg>');
    return out.join('');
  }

  const pieColors = ['#f59e0b','#f97316','#ef4444','#ec4899','#a855f7','#6366f1','#3b82f6','#14b8a6','#22c55e','#84cc16'];

  function svgDonutChart(data, width, height, opts){
    opts = opts || {};
    const colors = opts.colors || pieColors;
    const padAngle = (opts.padAngle !== undefined && opts.padAngle !== null) ? Number(opts.padAngle) : 6;
    const innerRatio = (opts.innerRatio !== undefined && opts.innerRatio !== null) ? Number(opts.innerRatio) : 0.62;
    if (!data || !data.length){
      return "<div class='small'>Sem dados para plotar.</div>";
    }
    const total = data.reduce((acc, d) => acc + (Number(d.value) || 0), 0);
    if (total <= 0) return "<div class='small'>Sem dados para plotar.</div>";
    const cx = width / 2;
    const cy = height / 2;
    const r = Math.min(width, height) / 2 - 6;
    const r0 = Math.max(1, r * innerRatio);
    let start = -90;
    const lines = [];
    lines.push("<svg xmlns='http://www.w3.org/2000/svg' class='svg' width='" + width + "' height='" + height + "' viewBox='0 0 " + width + " " + height + "'>");
    for (let i = 0; i < data.length; i++){
      const v = Number(data[i].value) || 0;
      if (v <= 0) continue;
      const ang = (v / total) * 360;
      const slicePad = Math.min(padAngle, Math.max(0, ang - 0.5));
      const aStart = start + slicePad / 2;
      const aEnd = start + ang - slicePad / 2;
      if (aEnd <= aStart){
        start += ang;
        continue;
      }
      const a0 = (Math.PI / 180) * aStart;
      const a1 = (Math.PI / 180) * aEnd;
      const x0 = cx + r * Math.cos(a0);
      const y0 = cy + r * Math.sin(a0);
      const x1 = cx + r * Math.cos(a1);
      const y1 = cy + r * Math.sin(a1);
      const x2 = cx + r0 * Math.cos(a1);
      const y2 = cy + r0 * Math.sin(a1);
      const x3 = cx + r0 * Math.cos(a0);
      const y3 = cy + r0 * Math.sin(a0);
      const large = (aEnd - aStart) > 180 ? 1 : 0;
      const color = colors[i % colors.length];
      lines.push(
        "<path d='M " + x0.toFixed(1) + " " + y0.toFixed(1) +
        " A " + r.toFixed(1) + " " + r.toFixed(1) + " 0 " + large + " 1 " + x1.toFixed(1) + " " + y1.toFixed(1) +
        " L " + x2.toFixed(1) + " " + y2.toFixed(1) +
        " A " + r0.toFixed(1) + " " + r0.toFixed(1) + " 0 " + large + " 0 " + x3.toFixed(1) + " " + y3.toFixed(1) +
        " Z' fill='" + color + "' opacity='0.95'/>"
      );
      start += ang;
    }
    lines.push("</svg>");
    return lines.join('');
  }

  function pieLegend(data, colors){
    colors = colors || pieColors;
    const total = data.reduce((acc, d) => acc + (Number(d.value) || 0), 0) || 1;
    return h('div', {className: 'pie-legend'},
      data.map((d, i) => {
        const pct = ((Number(d.value) || 0) / total) * 100;
        return h('div', {className: 'pie-legend-item', key: 'pl-' + i},
          h('span', {className: 'pie-dot', style: {background: colors[i % colors.length]}}),
          h('span', {className: 'pie-label'}, String(d.label)),
          h('span', {className: 'pie-pct'}, pct.toFixed(1) + '%')
        );
      })
    );
  }

  function SvgHtml(props){
    return h('div', {dangerouslySetInnerHTML: {__html: props.html || ''}});
  }

  function App(){
    const data = window.__REPORT_DATA__ || {};
    const icons = window.__REPORT_ICONS__ || {};
    const acc = data.account || {};
    const met = data.metrics || {};
    const qual = data.quality || {};
    const dd = data.drawdown || {};
    const val = data.validation || {};
    const flows = data.flows_summary || {};
    const dist = data.distribution || {};
    const pt = data.period_tables || {};
    const mc = data.monte_carlo || null;

    function iconImg(key, fallback){
      const src = icons[key];
      if (src){
        return h('img', {src: src, className: 'summary-icon-img', alt: fallback || key});
      }
      return fallback || '';
    }

    const period = data.period || {};
    const sinceIso = period.since || '';
    const untilIso = period.until || '';
    const periodLabel = (sinceIso || untilIso) ? (fmtDateBR(sinceIso) + ' a ' + fmtDateBR(untilIso)) : 'N/D';
    const reportDate = fmtDateISO(untilIso) || fmtDateISO(sinceIso) || new Date().toISOString().slice(0, 10);
    const currency = acc.currency || '';
    const equityNow = (data.equity_now !== undefined && data.equity_now !== null) ? data.equity_now : (val.equity_now || 0);

    let startBalance = val.balance_start_est;
    let deltaBalance = val.balance_delta_period;
    if (!startBalance){
      startBalance = Number(equityNow || 0) - Number(met.net_pnl || 0);
    }
    if (deltaBalance === undefined || deltaBalance === null){
      deltaBalance = met.net_pnl;
    }
    let variationPct = null;
    if (startBalance){
      variationPct = (Number(deltaBalance || 0) / Number(startBalance)) * 100.0;
    }
    const variationClass = (variationPct !== null && variationPct >= 0) ? 'positive' : 'negative';
    const variationText = variationPct !== null ? fmtPct1(variationPct) : 'N/D';

    const trades = Number(met.trades || 0);
    const winRate = fmtPct1(met.win_rate || 0);
    let ddPct = dd.max_balance_pct;
    if (ddPct === undefined || ddPct === null) ddPct = qual.max_dd_pct_curve;
    if (ddPct === undefined || ddPct === null) ddPct = met.max_dd_pct;
    const ddPctText = ddPct !== undefined && ddPct !== null ? fmtPct1(ddPct) : 'N/D';

    let ddAbs = dd.max_balance;
    if (ddAbs === undefined || ddAbs === null) ddAbs = qual.max_dd_abs_curve;
    if (ddAbs === undefined || ddAbs === null) ddAbs = met.max_dd_abs;

    let deposits = val.flows_period_deposits;
    let withdrawals = val.flows_period_withdrawals;
    if (deposits === undefined || deposits === null) deposits = flows.total_deposits;
    if (withdrawals === undefined || withdrawals === null) withdrawals = flows.total_withdrawals;

    const eqList = (data.timeseries || {}).equity || [];
    const eqPoints = eqList.map(item => {
      const t = item[0];
      const v = item[1];
      const lab = (typeof t === 'string' && t.indexOf('T') >= 0) ? t.split('T')[0] : String(t || '?');
      return [lab, Number(v || 0)];
    });

    const ddInfo = qual || {};
    const annot = {
      dd_abs: ddAbs || 0,
      dd_pct: ddPct || 0,
      from: (ddInfo.max_dd_window || {}).from,
      to: (ddInfo.max_dd_window || {}).to
    };

    const order = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const wd = (dist.by_weekday || {});
    const weekdayData = order.filter(d => wd[d] !== undefined).map(d => [d, Number(wd[d] || 0)]);
    const hr = (dist.by_hour || {});
    const hourKeys = Object.keys(hr || {});
    const hourData = hourKeys.map(k => [k, Number(hr[k] || 0)]).sort((a, b) => {
      const ha = parseInt(String(a[0]).replace('h', ''), 10) || 0;
      const hb = parseInt(String(b[0]).replace('h', ''), 10) || 0;
      return ha - hb;
    });

    const monthly = pt.monthly || {};
    const weekly = pt.weekly || {};
    const topSyms = Object.entries(met.pnl_by_symbol || {}).slice(0, 10);
    const monthlyKeys = Object.keys(monthly).sort();
    const weeklyKeys = Object.keys(weekly).sort();
    const monthlyData = monthlyKeys.map(k => [k, Number(monthly[k] || 0)]);
    const weeklyData = weeklyKeys.map(k => [k, Number(weekly[k] || 0)]);

    const mcAvailable = !!(mc && Object.keys(mc).length);
    const fanUrl = mcAvailable ? toFileUrl((mc.plots || {}).fan_chart) : '';
    const ddUrl = mcAvailable ? toFileUrl((mc.plots || {}).dd_hist) : '';
    let mcDdP95 = null;
    let mcProbRuin = null;
    let mcVar5 = null;
    let mcMedianEq = null;
    if (mcAvailable){
      if ((mc.max_drawdown || {}).p95 !== undefined && (mc.max_drawdown || {}).p95 !== null){
        mcDdP95 = Number(mc.max_drawdown.p95) * 100.0;
      }
      if (mc.prob_ruin_peak !== undefined && mc.prob_ruin_peak !== null){
        mcProbRuin = Number(mc.prob_ruin_peak) * 100.0;
      }
      if ((mc.final_pnl || {})['var@5%'] !== undefined && (mc.final_pnl || {})['var@5%'] !== null){
        mcVar5 = Number(mc.final_pnl['var@5%']);
      }
      if ((mc.final_equity || {}).median !== undefined && (mc.final_equity || {}).median !== null){
        mcMedianEq = Number(mc.final_equity.median);
      }
    }

    function Header(props){
      const logoSrc = icons.logo;
      return h('div', {className: 'header-card'},
        h('div', {className: 'header-block'},
          h('div', {className: 'header-top'},
            h('div', {className: 'brand'},
              h('div', {className: 'logo'}, logoSrc ? h('img', {src: logoSrc, className: 'logo-img', alt: 'RiskGuard'}) : 'RG'),
              h('div', {className: 'brand-name'}, 'RiskGuard')
            ),
            h('div', {className: 'date-box'},
              h('div', {className: 'date-pill'}, reportDate)
            )
          ),
          h('div', {className: 'title'}, 'Relat\u00f3rio de Performance'),
          h('div', {className: 'subtitle'}, '[' + (acc.server || '') + ' / Login ' + (acc.login || '') + ']')
        ),
        h('div', {className: 'period-bar'},
          h('div', {className: 'period-left'},
            h('div', null, 'Per\u00edodo: ', h('b', null, periodLabel)),
            h('div', null, 'Moeda: ', h('b', null, String(currency)))
          ),
          props.showBalance ? h('div', {className: 'meta-right'},
            h('div', {className: 'balance'}, fmtMoney(equityNow)),
            h('div', {className: 'variation ' + variationClass}, variationText)
          ) : null
        )
      );
    }

    const eqChartHtml = svgEquityChart(eqPoints, 960, 300, 32, annot);
    const ddBarHtml = svgDrawdownBarChart(eqPoints, 960, 200, 28);
    const ddLabel = 'Max. DD ' + fmtMoney(ddAbs || 0) + ' (' + (ddPct !== undefined && ddPct !== null ? fmtPct1(ddPct) : 'N/D') + ')';
    function fmtRate(x){
      if (x === undefined || x === null || Number.isNaN(Number(x))) return 'N/D';
      return Number(x).toFixed(1) + '%';
    }
    function fmtPips(x){
      if (x === undefined || x === null || Number.isNaN(Number(x))) return 'N/D';
      return Number(x).toFixed(1) + ' pips';
    }
    function fmtWinStat(obj){
      if (!obj || !obj.total) return 'N/D';
      return obj.wins + '/' + obj.total + ' (' + fmtRate(obj.rate) + ')';
    }
    function fmtTradeVal(tr){
      if (!tr) return 'N/D';
      const dt = tr.end ? fmtDateBR(tr.end) : '';
      const val = fmtMoney(tr.pnl || 0);
      return dt ? '(' + dt + ') ' + val : val;
    }
    function fmtTradePips(tr){
      if (!tr) return 'N/D';
      const dt = tr.end ? fmtDateBR(tr.end) : '';
      const val = fmtPips(tr.pips);
      return dt ? '(' + dt + ') ' + val : val;
    }
    function fmtDuration(sec){
      if (sec === undefined || sec === null || Number.isNaN(Number(sec))) return 'N/D';
      const s = Math.max(0, Math.round(Number(sec)));
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      return h + 'h ' + m + 'm';
    }
    function qualityTable(rows, key){
      return h('div', {className: 'subcard', key: key},
        h('table', {className: 'data-table'},
          h('tbody', null, rows.map((r, idx) =>
            h('tr', {key: key + '-' + idx},
              h('td', null, r[0]),
              h('td', {className: 'right'}, r[1])
            )
          ))
        )
      );
    }

    const expPayoff = (qual.expected_payoff !== undefined && qual.expected_payoff !== null) ? qual.expected_payoff : qual.expectancy;
    const qualityCard = h('div', {className: 'card section'},
      h('div', {className: 'card-title'}, 'Qualidade'),
      h('div', {className: 'split-table-3'},
        qualityTable([
          ['Trades', String(trades)],
          ['Profitability', fmtRate(met.win_rate)],
          ['Pips', fmtPips(qual.pips_total)],
          ['Average Win', fmtPips(qual.avg_win_pips) + ' / ' + fmtMoney(qual.avg_win || 0)],
          ['Average Loss', fmtPips(qual.avg_loss_pips) + ' / ' + fmtMoney(qual.avg_loss || 0)],
          ['Lots', (qual.lots_total !== undefined && qual.lots_total !== null) ? Number(qual.lots_total).toFixed(2) : 'N/D'],
          ['Commissions', fmtMoney(qual.commissions_total)]
        ], 'q1'),
        qualityTable([
          ['Longs Won', fmtWinStat(qual.longs_won)],
          ['Shorts Won', fmtWinStat(qual.shorts_won)],
          ['Best Trade (£)', fmtTradeVal(qual.best_trade)],
          ['Worst Trade (£)', fmtTradeVal(qual.worst_trade)],
          ['Best Trade (Pips)', fmtTradePips(qual.best_trade_pips)],
          ['Worst Trade (Pips)', fmtTradePips(qual.worst_trade_pips)],
          ['Avg. Trade Length', fmtDuration(qual.avg_trade_length_sec)]
        ], 'q2'),
        qualityTable([
          ['Profit Factor', (met.profit_factor !== undefined && met.profit_factor !== null) ? Number(met.profit_factor).toFixed(2) : 'N/D'],
          ['Standard Deviation', fmtMoney(qual.std_pnl)],
          ['Sharpe Ratio', (qual.sharpe !== undefined && qual.sharpe !== null) ? Number(qual.sharpe).toFixed(2) : 'N/D'],
          ['Z-Score (Probability)', (qual.z_score !== undefined && qual.z_score !== null) ? (Number(qual.z_score).toFixed(2) + (qual.z_prob !== undefined && qual.z_prob !== null ? ' (' + Number(qual.z_prob).toFixed(2) + '%)' : '')) : 'N/D'],
          ['Expectancy', fmtPips(qual.expectancy_pips) + ' / ' + fmtMoney(expPayoff || 0)],
          ['AHPR', (qual.ahpr !== undefined && qual.ahpr !== null) ? fmtRate(qual.ahpr) : 'N/D'],
          ['GHPR', (qual.ghpr !== undefined && qual.ghpr !== null) ? fmtRate(qual.ghpr) : 'N/D']
        ], 'q3')
      )
    );

    const page1 = h('div', {className: 'page'},
      h(Header, {showBalance: true}),
      h('div', {className: 'grid grid-3 section'},
        h('div', {className: 'card'},
          h('div', {className: 'card-title'}, 'Resumo'),
          h('div', {className: 'summary-list'},
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-icon'}, iconImg('trades', 'TR')),
              h('div', {className: 'summary-label'}, 'Trades'),
              h('div', {className: 'summary-value'}, String(trades))
            ),
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-icon'}, iconImg('winrate', 'WR')),
              h('div', {className: 'summary-label'}, 'Win rate'),
              h('div', {className: 'summary-value'}, winRate)
            ),
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-icon'}, iconImg('drawdown', 'DD')),
              h('div', {className: 'summary-label'}, 'DD m\u00e1ximo'),
              h('div', {className: 'summary-value negative'}, ddPctText)
            ),
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-icon'}, iconImg('depositos', 'IN')),
              h('div', {className: 'summary-label'}, 'Dep\u00f3sitos'),
              h('div', {className: 'summary-value'}, fmtMoney(deposits || 0))
            ),
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-icon'}, iconImg('saques', 'OUT')),
              h('div', {className: 'summary-label'}, 'Saques'),
              h('div', {className: 'summary-value'}, fmtMoney(withdrawals || 0))
            )
          )
        ),
        h('div', {className: 'card span-2'},
          h('div', {className: 'card-title'}, 'Curva de Equity'),
          h(SvgHtml, {html: eqChartHtml}),
          h('div', {className: 'legend'},
            h('div', {className: 'legend-item'}, h('span', {className: 'legend-line'}), h('span', null, 'Equity')),
            h('div', {className: 'legend-item'}, h('span', {className: 'legend-line gray'}), h('span', null, 'HWM')),
            h('div', {className: 'legend-item'}, h('span', {className: 'legend-line red'}), h('span', {className: 'negative'}, ddLabel))
          )
        )
      ),
      h('div', {className: 'card section'},
        h('div', {className: 'card-title'}, 'Drawdown (Percentual)'),
        eqPoints.length ? h(SvgHtml, {html: ddBarHtml}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.')
      ),
      h('div', {className: 'grid grid-2 section'},
        h('div', {className: 'card'},
          h('div', {className: 'card-title'}, 'Distribui\u00e7\u00e3o do M\u00e1x. Drawdown'),
          ddUrl ? h('img', {className: 'chart-img chart-img--dd', src: ddUrl, alt: 'DD distribution'}) : h('div', {className: 'chart-placeholder'}, 'Distribui\u00e7\u00e3o indispon\u00edvel.'),
          h('div', {className: 'section-gap'},
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-label'}, 'M\u00e1x. DD p95'),
              h('div', {className: 'summary-value'}, mcDdP95 !== null ? fmtPct1(mcDdP95) : 'N/D')
            ),
            h('div', {className: 'summary-item'},
              h('div', {className: 'summary-label'}, 'Prob. ru\u00edna (por pico)'),
              h('div', {className: 'summary-value'}, mcProbRuin !== null ? fmtPct1(mcProbRuin) : 'N/D')
            )
          )
        ),
        h('div', {className: 'card'},
          h('div', {className: 'card-title'}, 'Simula\u00e7\u00e3o Monte Carlo'),
          fanUrl ? h('img', {className: 'chart-img chart-img--mc', src: fanUrl, alt: 'Monte Carlo'}) : h('div', {className: 'chart-placeholder'}, 'Monte Carlo indispon\u00edvel.'),
          h('div', {className: 'grid grid-2 section-gap'},
            h('div', null, h('div', {className: 'muted'}, 'VaR@5%'), h('div', {className: 'summary-sub'}, mcVar5 !== null ? fmtMoney(mcVar5) : 'N/D')),
            h('div', null, h('div', {className: 'muted'}, 'Median Equity Final'), h('div', {className: 'summary-sub'}, mcMedianEq !== null ? fmtMoney(mcMedianEq) : 'N/D'))
          )
        )
      ),
      mcAvailable ? h('div', {className: 'card mc-summary section'},
        h('div', null,
          h('div', {className: 'summary-item'},
            h('div', {className: 'summary-label'}, 'M\u00e1x. DD p95'),
            h('div', {className: 'summary-value'}, mcDdP95 !== null ? fmtPct1(mcDdP95) : 'N/D')
          ),
          h('div', {className: 'summary-item'},
            h('div', {className: 'summary-label'}, 'Prob. ru\u00edna (por pico)'),
            h('div', {className: 'summary-value'}, mcProbRuin !== null ? fmtPct1(mcProbRuin) : 'N/D')
          )
        ),
        h('div', null,
          h('div', {className: 'summary-item'},
            h('div', {className: 'summary-label'}, 'VaR@5%'),
            h('div', {className: 'summary-value'}, mcVar5 !== null ? fmtMoney(mcVar5) : 'N/D')
          ),
          h('div', {className: 'summary-item'},
            h('div', {className: 'summary-label'}, 'Median Equity Final'),
            h('div', {className: 'summary-value'}, mcMedianEq !== null ? fmtMoney(mcMedianEq) : 'N/D')
          )
        )
      ) : null,
      qualityCard
    );

    const distWeekHtml = svgBarChart(weekdayData, 520, 230, 24, true, null);
    const distHourHtml = svgBarChart(hourData, 520, 230, 24, true, null);
    const monthlyChartHtml = svgBarChart(monthlyData, 520, 220, 24, true, null);
    const weeklyChartHtml = svgBarChart(weeklyData, 520, 220, 24, true, null, true);

    const tradeCounts = met.trades_by_symbol || {};
    const tradeCountEntries = Object.entries(tradeCounts).sort((a, b) => (Number(b[1]) || 0) - (Number(a[1]) || 0));
    const totalTradesCount = tradeCountEntries.reduce((acc, it) => acc + (Number(it[1]) || 0), 0);
    const topTradeSyms = tradeCountEntries.slice(0, 5);
    const otherTrades = totalTradesCount - topTradeSyms.reduce((acc, it) => acc + (Number(it[1]) || 0), 0);
    const pieSymbols = topTradeSyms.map(([s, v]) => ({label: s, value: Number(v) || 0}));
    if (otherTrades > 0) pieSymbols.push({label: 'Others', value: otherTrades});

    const longTotal = (qual.longs_won || {}).total || 0;
    const shortTotal = (qual.shorts_won || {}).total || 0;
    const pieLongShort = [{label: 'Long', value: longTotal}, {label: 'Short', value: shortTotal}];

    const pieWinLoss = [{label: 'Win', value: Number(met.wins || 0)}, {label: 'Loss', value: Number(met.losses || 0)}];

    const pnlBySymbol = met.pnl_by_symbol || {};
    const pnlEntries = Object.entries(pnlBySymbol).sort((a, b) => Math.abs(Number(b[1]) || 0) - Math.abs(Number(a[1]) || 0));
    const topPnlSyms = pnlEntries.slice(0, 5);
    const totalAbsPnl = pnlEntries.reduce((acc, it) => acc + Math.abs(Number(it[1]) || 0), 0);
    const topAbsPnl = topPnlSyms.reduce((acc, it) => acc + Math.abs(Number(it[1]) || 0), 0);
    const otherPnl = Math.max(0, totalAbsPnl - topAbsPnl);
    const piePnlSyms = topPnlSyms.map(([s, v]) => ({label: s, value: Math.abs(Number(v) || 0)}));
    if (otherPnl > 0) piePnlSyms.push({label: 'Others', value: otherPnl});

    const page2 = h('div', {className: 'page'},
      h('div', {className: 'card section'},
        h('div', {className: 'card-title'}, 'Distribui\u00e7\u00e3o por Dia e Hora'),
        h('div', {className: 'grid grid-2'},
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'PnL por Dia da Semana (USD)'),
            weekdayData.length ? h(SvgHtml, {html: distWeekHtml}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.')
          ),
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'PnL por Hora do Dia (USD)'),
            hourData.length ? h(SvgHtml, {html: distHourHtml}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.')
          )
        )
      ),
      h('div', {className: 'card section'},
        h('div', {className: 'card-title'}, 'Distribui\u00e7\u00f5es (Pizza)'),
        h('div', {className: 'pie-grid'},
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'Shorts vs Longs'),
            pieLongShort.length ? h(SvgHtml, {html: svgDonutChart(pieLongShort, 260, 220, {colors: ['#22c55e', '#ef4444'], padAngle: 6})}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.'),
            pieLegend(pieLongShort, ['#22c55e', '#ef4444'])
          ),
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'Win vs Loss'),
            pieWinLoss.length ? h(SvgHtml, {html: svgDonutChart(pieWinLoss, 260, 220, {colors: ['#3b82f6', '#f59e0b'], padAngle: 6})}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.'),
            pieLegend(pieWinLoss, ['#3b82f6', '#f59e0b'])
          ),
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'S\u00edmbolos Mais Negociados'),
            pieSymbols.length ? h(SvgHtml, {html: svgDonutChart(pieSymbols, 260, 220, {padAngle: 6})}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.'),
            pieLegend(pieSymbols)
          ),
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'Top PnL por S\u00edmbolo (Abs)'),
            piePnlSyms.length ? h(SvgHtml, {html: svgDonutChart(piePnlSyms, 260, 220, {padAngle: 6})}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.'),
            pieLegend(piePnlSyms)
          )
        )
      ),
      h('div', {className: 'card section'},
        h('div', {className: 'card-title'}, 'Mensal vs Semanal (USD)'),
        h('div', {className: 'split-table'},
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'Mensal (PnL $)'),
            monthlyData.length ? h(SvgHtml, {html: monthlyChartHtml}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.')
          ),
          h('div', {className: 'subcard'},
            h('div', {className: 'subcard-title'}, 'Semanal (PnL $)'),
            weeklyData.length ? h(SvgHtml, {html: weeklyChartHtml}) : h('div', {className: 'chart-placeholder'}, 'Sem dados.')
          )
        )
      ),
      h('div', {className: 'grid grid-2 section'},
        h('div', {className: 'card span-2'},
          h('div', {className: 'card-title'}, 'Maiores PnLs por S\u00edmbolo'),
          h('table', {className: 'data-table'},
            h('thead', null, h('tr', null, h('th', null, 'S\u00edmbolo'), h('th', {className: 'right'}, 'PnL'))),
            h('tbody', null, topSyms.map((pair, idx) => {
              const s = pair[0] || '-';
              const v = Number(pair[1] || 0);
              const cls = v < 0 ? 'neg' : 'pos';
              return h('tr', {key: 's-' + idx}, h('td', null, s), h('td', {className: 'right ' + cls}, fmtMoney(v)));
            }))
          )
        )
      ),
      h('div', {className: 'footer'}, '\u00a9 ' + new Date().getFullYear() + ' RiskGuard. All rights reserved.')
    );

    return h('div', {className: 'wrap'}, page1, page2);
  }

  function render(){
    const root = document.getElementById('root');
    if (!root) return;
    if (ReactDOM.createRoot){
      ReactDOM.createRoot(root).render(h(App));
    } else {
      ReactDOM.render(h(App), root);
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
