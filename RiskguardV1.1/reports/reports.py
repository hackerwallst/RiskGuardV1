# reports.py — Função 7: Relatório de Performance (MT5 + Logs RiskGuard)
from __future__ import annotations

# --- imports base ---
import sys
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import argparse
import json
import csv
import os
from collections import defaultdict
import calendar

# --- sys.path para importar módulos da pasta raiz (Notify.py, mt5_reader.py, logger.py) ---
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- imports do projeto ---
from notify import set_ident_from_snapshot, notify_report, send_document  # usa Notify.py (N maiúsculo)
from rg_config import get_float
import MetaTrader5 as mt5
from mt5_reader import RiskGuardMT5Reader
from logger import log_path_current
try:
    from .mc import (
        simulate_paths,
        summarize_paths,
        mc_fig_fanchart,
        mc_fig_dd_hist,
        mc_table,
        compute_R_from_trades,
    )
except ImportError:
    from mc import (
        simulate_paths,
        summarize_paths,
        mc_fig_fanchart,
        mc_fig_dd_hist,
        mc_table,
        compute_R_from_trades,
    )
import numpy as np
from lxml import html as lxml_html

# === RG: helpers de fluxos (depósitos/retiradas) — versão completa ===
def _rg_extract_flows_from_deals(deals):
    """
    Detecta depósitos e retiradas com heurísticas:
    - type == BALANCE (dep/saque)
    - type == CREDIT (depósito)
    - volume == 0 e symbol vazio (balance manual)
    - comentário com 'deposit', 'withdraw' etc.
    """
    from collections import defaultdict
    import MetaTrader5 as mt5

    dep = defaultdict(float)
    wdr = defaultdict(float)
    KW_DEP = ("deposit", "credit", "bonus", "add", "fund")
    KW_WDR = ("withdraw", "payout", "remove", "sub", "out")

    for d in deals:
        typ = int(d.get("type", -999))
        sym = (d.get("symbol") or "").strip().lower()
        cmt = (d.get("comment") or "").lower()
        vol = float(d.get("volume", 0.0))
        amt = float(d.get("profit", 0.0))
        day = (d.get("time") or "")[:10]
        if not day:
            continue

        # 1. Tipos diretos
        if typ in (mt5.DEAL_TYPE_BALANCE, mt5.DEAL_TYPE_CREDIT):
            if amt > 0:
                dep[day] += amt
            elif amt < 0:
                wdr[day] += abs(amt)
            continue

        # 2. Volume zero e símbolo vazio
        if vol == 0 and not sym:
            if amt > 0:
                dep[day] += amt
            elif amt < 0:
                wdr[day] += abs(amt)
            continue

        # 3. Comentário detectado
        if any(k in cmt for k in KW_DEP) and amt > 0:
            dep[day] += amt
        elif any(k in cmt for k in KW_WDR) and amt < 0:
            wdr[day] += abs(amt)

    return sorted(dep.items()), sorted(wdr.items())


# === RG: helpers para curva de equity ===
def _rg_make_equity_series(trades, equity_now, net_pnl):
    """
    trades: lista de dicts com pelo menos {"end": "...", "pnl": float}
    equity_now: equity atual
    net_pnl: pnl líquido do período (para inferir equity inicial)
    Retorna: [(label, equity), ...]
    """
    try:
        start_equity = float(equity_now or 0.0) - float(net_pnl or 0.0)
    except:
        start_equity = 0.0

    # usa a data/hora de fechamento do trade: campo 'end'
    rows = sorted(trades, key=lambda t: t.get("end",""))
    eq = []
    acc = start_equity
    last_label = None
    for t in rows:
        acc += float(t.get("pnl", 0.0))
        ct = str(t.get("end",""))
        label = ct.split("T")[0] if "T" in ct else ct.split(" ")[0]
        if not label:
            label = last_label or "?"
        eq.append((label, round(acc, 2)))
        last_label = label

    if not eq:
        eq = [("—", float(equity_now or 0.0))]
    return eq

# =========================
# MT5 HTML report parsing
# =========================
def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(ch)
    )

def _read_html_text(path: Path) -> str:
    for enc in ("utf-16", "utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(errors="ignore")

def _parse_float(value: str) -> float:
    if value is None:
        return 0.0
    s = str(value).replace("\xa0", "").replace(",", "").strip()
    if s == "" or s == "-":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def _parse_mt5_html_report(path: Path) -> Dict[str, Any]:
    text = _read_html_text(path)
    root = lxml_html.fromstring(text)
    rows = root.xpath("//table//tr")

    def _cells(r):
        cells = []
        for c in r.xpath("./th|./td"):
            cls = c.get("class") or ""
            if "hidden" in cls:
                continue
            val = c.text_content().strip()
            if val:
                cells.append(val)
        return cells

    # account info
    account: Dict[str, Any] = {}
    report_dt: Optional[datetime] = None
    for r in rows:
        cells = _cells(r)
        if len(cells) != 2:
            continue
        key = _strip_accents(cells[0]).rstrip(":").lower()
        if key == "nome":
            account["name"] = cells[1]
        elif key == "conta":
            raw = cells[1]
            m = re.match(r"(\d+)\s*\((.+)\)", raw)
            if m:
                account["login"] = int(m.group(1))
                parts = [p.strip() for p in m.group(2).split(",")]
                if parts:
                    account["currency"] = parts[0]
                if len(parts) > 1:
                    account["server"] = parts[1]
            else:
                account["login"] = raw
        elif key == "empresa":
            account["company"] = cells[1]
        elif key == "data":
            try:
                report_dt = datetime.strptime(cells[1], "%Y.%m.%d %H:%M")
            except Exception:
                report_dt = None

    # section indices
    headers: Dict[str, int] = {}
    for i, r in enumerate(rows):
        cells = _cells(r)
        if len(cells) == 1:
            headers[_strip_accents(cells[0])] = i

    pos_start = headers.get("Posicoes")
    ord_start = headers.get("Ordens")
    trans_start = headers.get("Transacoes")
    res_start = headers.get("Resultados")

    trades: List[Dict[str, Any]] = []
    if pos_start is not None and ord_start is not None:
        for r in rows[pos_start + 1 : ord_start]:
            cells = _cells(r)
            if not cells:
                continue
            if not re.match(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$", cells[0]):
                continue
            if len(cells) not in (12, 13):
                continue
            if len(cells) == 13:
                time_in, pos_id, symbol, typ, vol, price, sl, tp, time_out, price_out, comm, sw, prof = cells
            else:
                time_in, pos_id, symbol, typ, vol, price, sl, time_out, price_out, comm, sw, prof = cells
            comm_val = _parse_float(comm)
            sw_val = _parse_float(sw)
            price_in = _parse_float(price)
            price_out_f = _parse_float(price_out)
            pnl = _parse_float(prof) + comm_val + sw_val
            try:
                t0 = datetime.strptime(time_in, "%Y.%m.%d %H:%M:%S")
                t1 = datetime.strptime(time_out, "%Y.%m.%d %H:%M:%S")
            except Exception:
                t0 = None
                t1 = None
            trades.append({
                "position_id": int(pos_id) if str(pos_id).isdigit() else 0,
                "symbol": symbol,
                "volume": _parse_float(vol),
                "pnl": pnl,
                "commission": comm_val,
                "swap": sw_val,
                "price_in": price_in,
                "price_out": price_out_f,
                "start": t0.isoformat() if t0 else time_in,
                "end": t1.isoformat() if t1 else time_out,
                "holding_time_sec": (t1 - t0).total_seconds() if t0 and t1 else 0.0,
                "type": typ,
            })

    # deals / balance series
    events: List[Dict[str, Any]] = []
    balance_points: List[Tuple[str, float]] = []
    flow_deposits = 0.0
    flow_withdrawals = 0.0
    if trans_start is not None and res_start is not None:
        for r in rows[trans_start + 1 : res_start]:
            cells = _cells(r)
            if not cells:
                continue
            if not re.match(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$", cells[0]):
                continue
            if len(cells) < 13:
                continue
            # layout (after removing hidden cost column):
            # time, offer, symbol, type, direction, volume, price, order, commission, fee, swap, profit, balance, comment?
            time_str = cells[0]
            symbol = cells[2] if len(cells) > 2 else ""
            typ = (cells[3] if len(cells) > 3 else "").lower()
            volume = cells[5] if len(cells) > 5 else ""
            commission = _parse_float(cells[8]) if len(cells) > 8 else 0.0
            fee = _parse_float(cells[9]) if len(cells) > 9 else 0.0
            swap = _parse_float(cells[10]) if len(cells) > 10 else 0.0
            profit = _parse_float(cells[11]) if len(cells) > 11 else 0.0
            balance = _parse_float(cells[12]) if len(cells) > 12 else None
            comment = cells[13] if len(cells) > 13 else ""

            if balance is not None:
                balance_points.append((time_str, balance))

            if typ in ("balance", "credit") or (not symbol and not str(volume).strip()):
                if profit > 0:
                    flow_deposits += profit
                elif profit < 0:
                    flow_withdrawals += abs(profit)

            events.append({
                "time": time_str,
                "type": typ,
                "symbol": symbol,
                "volume": volume,
                "profit": profit,
                "commission": commission + fee,
                "swap": swap,
                "balance": balance,
                "comment": comment,
            })

    balance_points_sorted = sorted(balance_points, key=lambda x: x[0])
    start_balance = balance_points_sorted[0][1] if balance_points_sorted else 0.0
    end_balance = balance_points_sorted[-1][1] if balance_points_sorted else start_balance

    # absolute drawdown (balance)
    initial_ref = start_balance
    min_after = end_balance
    trade_seen = False
    for ev in sorted(events, key=lambda e: e.get("time", "")):
        bal = ev.get("balance")
        if bal is None:
            continue
        if not trade_seen:
            if ev.get("type") in ("balance", "credit"):
                initial_ref = bal
                continue
            trade_seen = True
            min_after = bal
            continue
        if bal < min_after:
            min_after = bal
    abs_dd = max(0.0, float(initial_ref) - float(min_after))
    abs_dd_pct = (abs_dd / float(initial_ref) * 100.0) if initial_ref else None

    # max drawdown using balance points (full resolution)
    dd_abs, dd_pct, dd_peak, dd_trough, dd_peak_lab, dd_trough_lab = _max_drawdown_stats(balance_points_sorted)

    since_dt = None
    until_dt = None
    if balance_points_sorted:
        try:
            since_dt = datetime.strptime(balance_points_sorted[0][0], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            since_dt = None
    if report_dt:
        until_dt = report_dt.replace(tzinfo=timezone.utc) + timedelta(days=1)
    elif balance_points_sorted:
        try:
            until_dt = datetime.strptime(balance_points_sorted[-1][0], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
            until_dt = until_dt + timedelta(days=1)
        except Exception:
            until_dt = None

    return {
        "account": account,
        "report_dt": report_dt,
        "trades": trades,
        "balance_points": balance_points_sorted,
        "start_balance": start_balance,
        "end_balance": end_balance,
        "flows": {
            "deposits": round(flow_deposits, 2),
            "withdrawals": round(flow_withdrawals, 2),
            "net": round(flow_deposits - flow_withdrawals, 2),
        },
        "drawdown": {
            "absolute_balance": round(abs_dd, 2),
            "absolute_balance_pct": round(abs_dd_pct, 2) if abs_dd_pct is not None else None,
            "max_balance": dd_abs,
            "max_balance_pct": dd_pct,
            "peak_balance": round(float(dd_peak or 0.0), 2),
            "trough_balance": round(float(dd_trough or 0.0), 2),
            "start_balance_est": round(float(start_balance or 0.0), 2),
            "initial_balance_ref": round(float(initial_ref or 0.0), 2),
            "min_balance": round(float(min_after or 0.0), 2),
        },
        "period": {
            "since": since_dt.isoformat() if since_dt else None,
            "until": until_dt.isoformat() if until_dt else None,
        },
    }

def _rg_is_flow_deal(d: Dict[str, Any]) -> bool:
    typ = int(d.get("type", -999))
    profit = float(d.get("profit", 0.0))
    vol = float(d.get("volume", 0.0))
    sym = (d.get("symbol") or "").strip()
    if typ in (mt5.DEAL_TYPE_BALANCE, mt5.DEAL_TYPE_CREDIT):
        return True
    if vol == 0 and not sym and profit != 0:
        return True
    return False

def _rg_deal_delta(d: Dict[str, Any]) -> float:
    if _rg_is_flow_deal(d):
        return float(d.get("profit", 0.0))
    return float(d.get("profit", 0.0)) + float(d.get("commission", 0.0)) + float(d.get("swap", 0.0))

def _rg_initial_and_min_balance(
    events: List[Dict[str, Any]],
    balance_start: float
) -> Tuple[float, float]:
    bal = float(balance_start or 0.0)
    initial_ref = bal
    trade_seen = False
    min_after = None
    for d in events:
        bal += _rg_deal_delta(d)
        if not trade_seen:
            if _rg_is_flow_deal(d):
                # soma depósitos iniciais antes do primeiro trade
                initial_ref = bal
                continue
            trade_seen = True
            min_after = bal
            continue
        if min_after is None or bal < min_after:
            min_after = bal
    if min_after is None:
        min_after = bal
    return initial_ref, min_after

def _rg_split_period_deltas(deals: List[Dict[str, Any]]) -> Tuple[float, float, float]:
    trade_delta = 0.0
    flow_delta = 0.0
    for d in deals:
        delta = _rg_deal_delta(d)
        if _rg_is_flow_deal(d):
            flow_delta += delta
        else:
            trade_delta += delta
    return trade_delta, flow_delta, trade_delta + flow_delta

def _rg_make_balance_series(
    deals: List[Dict[str, Any]],
    balance_now: float
) -> Tuple[List[Tuple[str, float]], float, float, float, float, float]:
    events = sorted(deals, key=lambda x: x.get("time", ""))
    trade_delta, flow_delta, total_delta = _rg_split_period_deltas(events)
    try:
        start_balance = float(balance_now or 0.0) - float(total_delta or 0.0)
    except Exception:
        start_balance = float(balance_now or 0.0)

    bal = start_balance
    daily: Dict[str, float] = {}
    last_label: Optional[str] = None
    for d in events:
        bal += _rg_deal_delta(d)
        ts = str(d.get("time", ""))
        label = ts.split("T")[0] if "T" in ts else ts.split(" ")[0]
        if not label:
            label = last_label or "-"
        daily[label] = round(bal, 2)
        last_label = label

    if not daily:
        return [("-", float(balance_now or 0.0))], round(start_balance, 2), float(balance_now or 0.0), trade_delta, flow_delta, total_delta

    points = sorted(daily.items(), key=lambda kv: kv[0])
    end_balance = float(points[-1][1])
    return points, round(start_balance, 2), end_balance, trade_delta, flow_delta, total_delta

# === RG: detectores de fluxos (depósitos/retiradas) no histórico completo ===
def _rg_fetch_all_flows(until_dt: datetime):
    """
    Lê TODO o histórico de deals desde 2000-01-01 até 'until_dt' e retorna
    duas listas [(YYYY-MM-DD, +valor)], uma para depósitos e outra para saques.
    """
    import MetaTrader5 as mt5
    from collections import defaultdict

    since_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)  # início bem amplo
    deals = mt5.history_deals_get(since_dt, until_dt)
    dep = defaultdict(float)
    wdr = defaultdict(float)
    if not deals:
        return [], []

    # palavras-chave de fallback (casos onde o broker usa comment)
    KW_DEP = ("deposit", "credit", "bonus", "add", "fund", "topup", "refill", "in")
    KW_WDR = ("withdraw", "payout", "remove", "sub", "out", "wd")

    for d in deals:
        typ = int(getattr(d, "type", -999))
        amt = float(getattr(d, "profit", 0.0))
        vol = float(getattr(d, "volume", 0.0))
        sym = (getattr(d, "symbol", "") or "").strip().lower()
        cmt = (getattr(d, "comment", "") or "").strip().lower()
        ts  = datetime.fromtimestamp(getattr(d, "time", 0), tz=timezone.utc)
        day = ts.date().isoformat()

        # 1) tipos oficiais
        # BALANCE: depósito/saque; CREDIT: tratamos como depósito
        if typ in (mt5.DEAL_TYPE_BALANCE, mt5.DEAL_TYPE_CREDIT):
            if amt >= 0:
                dep[day] += amt
            else:
                wdr[day] += abs(amt)
            continue

        # 2) heurística: volume 0 e símbolo vazio costumam ser operações de saldo
        if vol == 0 and not sym and amt != 0:
            if amt > 0:
                dep[day] += amt
            else:
                wdr[day] += abs(amt)
            continue

        # 3) fallback por comentário
        if any(k in cmt for k in KW_DEP) and amt > 0:
            dep[day] += amt
        elif any(k in cmt for k in KW_WDR) and amt < 0:
            wdr[day] += abs(amt)

    return sorted(dep.items()), sorted(wdr.items())


def _rg_filter_flows_to_period(deposits, withdrawals, since_dt: datetime, until_dt: datetime):
    """
    Filtra listas [(YYYY-MM-DD, valor+)] para o intervalo [since_dt, until_dt)
    """
    def _keep(day_str):
        try:
            d = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return since_dt <= d < until_dt
        except:
            return False
    deps = [(d, v) for (d, v) in deposits if _keep(d)]
    wdrs = [(d, v) for (d, v) in withdrawals if _keep(d)]
    return deps, wdrs


# === RG: alinhar equity com dias do período e com fluxos ===
def _rg_daily_equity(eq_points, since_dt, until_dt):
    """
    Recebe [(YYYY-MM-DD, equity)] (em dias com trade) e preenche TODOS os dias do período.
    Forward-fill do último equity conhecido.
    """
    from datetime import timedelta, datetime
    # normaliza pontos (somente datas)
    pts = [(p[0].split("T")[0] if isinstance(p[0], str) else str(p[0]), float(p[1])) for p in (eq_points or [])]
    pts.sort(key=lambda x: x[0])
    last_val = pts[0][1] if pts else 0.0
    eq_by_day = {d: v for d, v in pts}

    out = []
    d = since_dt.date()
    end = (until_dt - timedelta(days=1)).date()  # until é exclusivo
    while d <= end:
        key = d.isoformat()
        if key in eq_by_day:
            last_val = eq_by_day[key]
        out.append((key, last_val))
        d += timedelta(days=1)
    return out


def _max_drawdown_stats(eq_points):
    """
    Calcula DD máximo pela curva de equity.
    Retorna (dd_abs, dd_pct, peak_equity, trough_equity, peak_label, trough_label)
    """
    peak = None
    dd_abs = 0.0
    peak_label = trough_label = ""
    peak_equity = trough_equity = 0.0
    for lab, val in eq_points:
        if peak is None or val > peak:
            peak = val
            peak_label = lab
            trough_equity = val
            trough_label = lab
        if peak - val > dd_abs:
            dd_abs = peak - val
            trough_equity = val
            trough_label = lab
    dd_pct = (dd_abs / (peak or 1.0)) * 100.0
    return round(dd_abs, 2), round(dd_pct, 2), peak or 0.0, trough_equity, peak_label, trough_label

# === RG: fluxos (depósitos/retiradas) olhando janela ampla ===
def _rg_extract_flows_wide_window(since: datetime, until: datetime):
    """
    Varre uma janela mais ampla (since-400d .. until) para achar depósitos/saques,
    e depois filtra os eventos para [since, until).
    Retorna: (deposits[ (YYYY-MM-DD, +valor) ], withdrawals[ (YYYY-MM-DD, +valor) ])
    """
    import MetaTrader5 as mt5
    from collections import defaultdict, Counter

    wide_since = since - timedelta(days=400)
    deals = mt5.history_deals_get(wide_since, until)
    dep = defaultdict(float)
    wdr = defaultdict(float)

    if not deals:
        return [], []

    # Palavras-chave para fallback em comentários (ajustaremos se necessário)
    KW_DEP = ("deposit", "credit", "bonus", "add", "fund", "topup", "refill", "in")
    KW_WDR = ("withdraw", "payout", "remove", "sub", "out", "wd")

    # DEBUG opcional: mapear comentários mais comuns (sem volume)
    # (se quiser, descomente estas 3 linhas)
    # cmt_counter = Counter((getattr(d, "comment", "") or "").strip().lower() for d in deals if getattr(d, "volume", 0.0) == 0)
    # top_cmts = cmt_counter.most_common(8)
    # print("[DEBUG] top balance comments:", top_cmts)

    for d in deals:
        typ = int(getattr(d, "type", -999))
        amt = float(getattr(d, "profit", 0.0))
        vol = float(getattr(d, "volume", 0.0))
        sym = (getattr(d, "symbol", "") or "").strip().lower()
        cmt = (getattr(d, "comment", "") or "").strip().lower()
        ts  = datetime.fromtimestamp(getattr(d, "time", 0), tz=timezone.utc)
        day = ts.date().isoformat()

        # Detectores:
        if typ in (mt5.DEAL_TYPE_BALANCE, mt5.DEAL_TYPE_CREDIT):
            # CREDIT tratamos como "depósito"
            if since <= ts < until:
                if amt >= 0:
                    dep[day] += amt
                else:
                    wdr[day] += abs(amt)
            continue

        # volume zero e símbolo vazio costumam ser operações de saldo
        if vol == 0 and not sym:
            if since <= ts < until:
                if amt > 0:
                    dep[day] += amt
                elif amt < 0:
                    wdr[day] += abs(amt)
            continue

        # fallback por comentário
        if since <= ts < until:
            if any(k in cmt for k in KW_DEP) and amt > 0:
                dep[day] += amt
            elif any(k in cmt for k in KW_WDR) and amt < 0:
                wdr[day] += abs(amt)

    return sorted(dep.items()), sorted(wdr.items())


# --- HTML/PDF (funciona rodando como módulo ou script)
try:
    # se "reports" for um pacote (tem __init__.py)
    from .render_html import render_html
    from .render_react import render_react_html
    from .render_pdf import html_to_pdf
except ImportError:
    # se rodar direto: python reports/reports.py ...
    from render_html import render_html
    from render_react import render_react_html
    from render_pdf import html_to_pdf

# --- pastas de saída ---
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Utilidades de data / fmt
# =========================
def _utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _dt(date_str: str) -> datetime:
    # "YYYY-MM-DD" -> datetime UTC 00:00
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.replace(tzinfo=timezone.utc)

def _fmt_usd(x: Optional[float]) -> str:
    if x is None:
        return "N/D"
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return str(x)

def _seconds_to_hms(sec: float) -> str:
    sec = int(abs(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# =====================================
# 1) Histórico de trades (deals) do MT5
# =====================================
def fetch_deals_raw(reader: RiskGuardMT5Reader, since: datetime, until: datetime) -> List[Dict[str, Any]]:
    """Busca deals de histórico no período [since, until) (inclui BALANCE/CREDIT)."""
    deals = mt5.history_deals_get(since, until)
    out: List[Dict[str, Any]] = []
    if deals is None:
        return out
    for d in deals:
        entry = getattr(d, "entry", None)
        out.append({
            "time": datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
            "ticket": int(d.ticket),
            "position_id": int(getattr(d, "position_id", 0)),
            "symbol": d.symbol,
            "type": int(d.type),
            "entry": int(entry) if entry is not None else None,
            "price": float(getattr(d, "price", 0.0)),
            "volume": float(getattr(d, "volume", 0.0)),
            "profit": float(getattr(d, "profit", 0.0)),
            "commission": float(getattr(d, "commission", 0.0)),
            "swap": float(getattr(d, "swap", 0.0)),
            "magic": int(getattr(d, "magic", 0)),
            "comment": getattr(d, "comment", ""),
        })
    out.sort(key=lambda x: x["time"])
    return out

def fetch_deals(reader: RiskGuardMT5Reader, since: datetime, until: datetime) -> List[Dict[str, Any]]:
    """Busca deals de histórico no período [since, until)."""
    out = fetch_deals_raw(reader, since, until)
    return [d for d in out if int(d.get("type", -999)) not in (mt5.DEAL_TYPE_BALANCE, mt5.DEAL_TYPE_CREDIT)]

def group_trades(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa deals por position_id (trade) e calcula PnL e duração.
    """
    by_pos: Dict[int, List[Dict[str, Any]]] = {}
    for d in deals:
        pid = d.get("position_id", 0) or 0
        by_pos.setdefault(pid, []).append(d)

    trades: List[Dict[str, Any]] = []
    for pid, lst in by_pos.items():
        lst = sorted(lst, key=lambda x: x["time"])
        symbol = lst[0]["symbol"]
        price_in = lst[0].get("price")
        price_out = lst[-1].get("price")
        vol = sum(x["volume"] for x in lst if x["entry"] == 1 or x["entry"] is None)  # aproximado
        commission = sum(x.get("commission", 0.0) for x in lst)
        swap = sum(x.get("swap", 0.0) for x in lst)
        profit = sum(x["profit"] for x in lst) + commission + swap
        t0 = _utc(lst[0]["time"])
        t1 = _utc(lst[-1]["time"])
        holding_sec = (t1 - t0).total_seconds()
        trade_type = "buy" if any(x["type"] == mt5.DEAL_TYPE_BUY for x in lst) else ("sell" if any(x["type"] == mt5.DEAL_TYPE_SELL for x in lst) else "n/a")
        trades.append({
            "position_id": pid,
            "symbol": symbol,
            "volume": vol,
            "pnl": profit,
            "commission": commission,
            "swap": swap,
            "price_in": price_in,
            "price_out": price_out,
            "start": t0.isoformat(),
            "end": t1.isoformat(),
            "holding_time_sec": holding_sec,
            "type": trade_type,
        })
    return [t for t in trades if t["position_id"] != 0 and (t.get("symbol") or "").strip() != ""]

# ==========================================
# 1.1) Filtros por origem (magic/manual-only)
# ==========================================
def _parse_magic_list(s: Optional[str]) -> Optional[List[int]]:
    if not s:
        return None
    out: List[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except:
            pass
    return out or None

def filter_deals(deals: List[Dict[str, Any]], magic_list: Optional[List[int]], manual_only: bool) -> List[Dict[str, Any]]:
    if manual_only:
        return [d for d in deals if d.get("magic", 0) == 0]
    if magic_list:
        return [d for d in deals if d.get("magic", 0) in magic_list]
    return deals

# =============================
# 2) Métricas e qualidade (fase A)
# =============================
def compute_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "net_pnl": 0.0,
            "profit_factor": None,
            "avg_holding": None,
            "best_trade": None, "worst_trade": None,
            "pnl_by_symbol": {},
            "max_dd_abs": 0.0, "max_dd_pct": None
        }
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net = sum(pnls)
    wr = (len(wins) / len(pnls)) * 100.0 if pnls else 0.0
    pf = (gross_profit / gross_loss) if gross_loss > 1e-12 else None
    avg_hold = sum(t["holding_time_sec"] for t in trades) / len(trades)
    best = max(trades, key=lambda x: x["pnl"])
    worst = min(trades, key=lambda x: x["pnl"])

    # PnL por símbolo + contagem por símbolo
    by_sym: Dict[str, float] = {}
    by_sym_count: Dict[str, int] = {}
    for t in trades:
        sym = t.get("symbol") or "-"
        by_sym[sym] = by_sym.get(sym, 0.0) + t["pnl"]
        by_sym_count[sym] = by_sym_count.get(sym, 0) + 1

    # Curva cumulativa -> MaxDD (pelo resultado realizado, ordenado por fechamento)
    ordered = sorted(trades, key=lambda t: t.get("end", ""))
    cum = 0.0
    cum_curve: List[float] = []
    for t in ordered:
        cum += t["pnl"]
        cum_curve.append(cum)
    max_dd_abs = 0.0
    peak = -1e30
    for v in cum_curve:
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd_abs:
            max_dd_abs = dd
    max_dd_pct = (max_dd_abs / peak * 100.0) if peak > 1e-9 else None

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": wr,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": net,
        "profit_factor": pf,
        "avg_holding": avg_hold,
        "best_trade": best,
        "worst_trade": worst,
        "pnl_by_symbol": {k: v for k, v in sorted(by_sym.items(), key=lambda kv: -abs(kv[1]))},
        "trades_by_symbol": {k: v for k, v in sorted(by_sym_count.items(), key=lambda kv: -kv[1])},
        "max_dd_abs": max_dd_abs,
        "max_dd_pct": max_dd_pct
    }

def compute_streaks(pnls: List[float]) -> Dict[str, Any]:
    best_win, best_loss = 0, 0
    cur_win, cur_loss = 0, 0
    for p in pnls:
        if p > 0:
            cur_win += 1
            cur_loss = 0
        elif p < 0:
            cur_loss += 1
            cur_win = 0
        else:
            cur_win = 0
            cur_loss = 0
        best_win = max(best_win, cur_win)
        best_loss = max(best_loss, cur_loss)
    return {"win_streak": best_win, "loss_streak": best_loss}

def compute_expectancy_payoff(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {
            "expectancy": 0.0,
            "expected_payoff": 0.0,
            "payoff_ratio": None,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "avg_loss_abs": 0.0,
        }
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total = len(pnls) or 1
    net_total = sum(pnls)
    expected_payoff = net_total / total  # MT5: Net Profit / Total Trades

    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss_abs = (abs(sum(losses)) / len(losses)) if losses else 0.0
    avg_loss = -avg_loss_abs if losses else 0.0
    payoff_ratio = (avg_win / avg_loss_abs) if avg_loss_abs > 1e-12 else None

    return {
        "expectancy": expected_payoff,
        "expected_payoff": expected_payoff,
        "payoff_ratio": payoff_ratio,
        "payoff": payoff_ratio,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_loss_abs": avg_loss_abs,
    }

def _pip_factor_from_price(price: Optional[float]) -> float:
    try:
        if price is None:
            return 1.0
        s = f"{float(price)}"
        if "." not in s:
            return 1.0
        dec = len(s.split(".")[1].rstrip("0"))
        if dec >= 4:
            return 10000.0
        if dec == 3:
            return 100.0
        if dec == 2:
            return 100.0
        if dec == 1:
            return 10.0
        return 1.0
    except Exception:
        return 1.0

def _trade_pips(trade: Dict[str, Any]) -> Optional[float]:
    pin = trade.get("price_in")
    pout = trade.get("price_out")
    if pin is None or pout is None:
        return None
    try:
        pin_f = float(pin)
        pout_f = float(pout)
    except Exception:
        return None
    factor = _pip_factor_from_price(pin_f)
    side = str(trade.get("type", "")).lower()
    if side == "sell":
        return (pin_f - pout_f) * factor
    return (pout_f - pin_f) * factor

def _z_score_runs(pnls: List[float]) -> Tuple[Optional[float], Optional[float]]:
    import math
    seq = [1 if p > 0 else 0 for p in pnls if p != 0]
    if len(seq) < 2:
        return None, None
    n1 = sum(seq)
    n2 = len(seq) - n1
    if n1 == 0 or n2 == 0:
        return None, None
    runs = 1
    for i in range(1, len(seq)):
        if seq[i] != seq[i-1]:
            runs += 1
    expected = (2 * n1 * n2) / (n1 + n2) + 1
    denom = ((n1 + n2) ** 2) * (n1 + n2 - 1)
    num = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)
    if denom <= 0 or num <= 0:
        return None, None
    std = math.sqrt(num / denom)
    if std <= 1e-12:
        return None, None
    z = (runs - expected) / std
    # two-tailed probability
    phi = 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))
    prob = (1 - phi) * 2 * 100.0
    return z, prob

def compute_quality_stats(
    trades: List[Dict[str, Any]],
    met: Dict[str, Any],
    balance_start: Optional[float] = None
) -> Dict[str, Any]:
    import math
    total = len(trades)
    pnls = [float(t.get("pnl", 0.0)) for t in trades]
    avg_pnl = (sum(pnls) / total) if total else 0.0
    std_pnl = None
    if total > 1:
        std_pnl = math.sqrt(sum((p - avg_pnl) ** 2 for p in pnls) / total)

    sharpe = None
    if std_pnl and std_pnl > 1e-12 and total > 1:
        sharpe = (avg_pnl / std_pnl) * math.sqrt(total)

    # Pips
    pips_records: List[Tuple[Dict[str, Any], float]] = []
    for t in trades:
        p = _trade_pips(t)
        if p is not None:
            pips_records.append((t, float(p)))
    total_pips = sum(p for _, p in pips_records) if pips_records else None
    pips_wins = [p for t, p in pips_records if float(t.get("pnl", 0.0)) > 0]
    pips_losses = [p for t, p in pips_records if float(t.get("pnl", 0.0)) < 0]
    avg_win_pips = (sum(pips_wins) / len(pips_wins)) if pips_wins else None
    avg_loss_pips = (sum(pips_losses) / len(pips_losses)) if pips_losses else None

    best_pips = None
    worst_pips = None
    if pips_records:
        best_pips = max(pips_records, key=lambda x: x[1])
        worst_pips = min(pips_records, key=lambda x: x[1])

    # Longs/Shorts won
    def _is_buy(t): return str(t.get("type","")).lower() == "buy"
    def _is_sell(t): return str(t.get("type","")).lower() == "sell"
    long_total = sum(1 for t in trades if _is_buy(t))
    long_wins = sum(1 for t in trades if _is_buy(t) and float(t.get("pnl", 0.0)) > 0)
    short_total = sum(1 for t in trades if _is_sell(t))
    short_wins = sum(1 for t in trades if _is_sell(t) and float(t.get("pnl", 0.0)) > 0)

    # Commissions / Lots
    total_lots = sum(float(t.get("volume", 0.0)) for t in trades)
    total_comm = sum(float(t.get("commission", 0.0)) for t in trades)

    # Expectancy in pips
    expectancy_pips = (total_pips / total) if (total and total_pips is not None) else None

    # AHPR / GHPR (per-trade returns)
    ahpr = ghpr = None
    if balance_start and balance_start > 0 and total:
        bal = float(balance_start)
        returns = []
        for t in sorted(trades, key=lambda x: x.get("end", "")):
            if bal <= 0:
                break
            r = float(t.get("pnl", 0.0)) / bal
            returns.append(r)
            bal += float(t.get("pnl", 0.0))
        if returns:
            ahpr = sum(returns) / len(returns) * 100.0
            prod = 1.0
            for r in returns:
                prod *= (1 + r)
            if prod > 0:
                ghpr = (prod ** (1 / len(returns)) - 1) * 100.0

    z_score, z_prob = _z_score_runs(pnls)

    best_trade = met.get("best_trade")
    worst_trade = met.get("worst_trade")

    out = {
        "pips_total": total_pips,
        "avg_win_pips": avg_win_pips,
        "avg_loss_pips": avg_loss_pips,
        "best_trade_pips": {"pips": best_pips[1], "end": best_pips[0].get("end")} if best_pips else None,
        "worst_trade_pips": {"pips": worst_pips[1], "end": worst_pips[0].get("end")} if worst_pips else None,
        "longs_won": {
            "wins": long_wins, "total": long_total,
            "rate": (long_wins / long_total * 100.0) if long_total else None
        },
        "shorts_won": {
            "wins": short_wins, "total": short_total,
            "rate": (short_wins / short_total * 100.0) if short_total else None
        },
        "lots_total": total_lots,
        "commissions_total": total_comm,
        "std_pnl": std_pnl,
        "sharpe": sharpe,
        "z_score": z_score,
        "z_prob": z_prob,
        "expectancy_pips": expectancy_pips,
        "ahpr": ahpr,
        "ghpr": ghpr,
        "avg_trade_length_sec": met.get("avg_holding"),
        "best_trade": best_trade,
        "worst_trade": worst_trade,
    }
    return out

# =========================================
# 3) Mensal / Semanal / Distribuições (Fase A)
# =========================================
def group_by_month(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    out = defaultdict(float)
    for t in trades:
        d = datetime.fromisoformat(t["end"]).date()
        key = f"{d.year}-{d.month:02d}"
        out[key] += t["pnl"]
    return dict(sorted(out.items()))

def group_by_week(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    out = defaultdict(float)
    for t in trades:
        d = datetime.fromisoformat(t["end"]).date()
        year, week, _ = d.isocalendar()
        key = f"{year}-W{week:02d}"
        out[key] += t["pnl"]
    return dict(sorted(out.items()))

def distro_weekday_hour(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    wd = defaultdict(float)   # 0=Mon ... 6=Sun
    hr = defaultdict(float)   # 0..23
    for t in trades:
        d1 = datetime.fromisoformat(t["end"])
        wd[d1.weekday()] += t["pnl"]
        hr[d1.hour] += t["pnl"]
    wd_named = {calendar.day_abbr[k]: v for k, v in sorted(wd.items())}
    hr_named = {f"{k:02d}h": v for k, v in sorted(hr.items())}
    return {"by_weekday": wd_named, "by_hour": hr_named}

# =======================================
# 4) Leitura de logs RiskGuard (Função 6)
# =======================================
def load_logs_in_range(since: datetime, until: datetime) -> List[Dict[str, Any]]:
    # Por simplicidade, lê apenas o log do mês atual (extensível para múltiplos meses)
    logf = Path(log_path_current())
    if not logf.exists():
        return []
    out: List[Dict[str, Any]] = []
    with logf.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
                ts = _utc(j.get("ts"))
                if since <= ts < until:
                    out.append(j)
            except Exception:
                continue
    return out

def summarize_riskguard_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_type = {"PER_TRADE": 0, "NEWS": 0, "LIMITS": 0, "DD_KILL": 0}
    closed_total = 0
    for e in events:
        et = (e.get("type") or "").upper()
        by_type[et] = by_type.get(et, 0) + 1
        payload = e.get("payload", {})
        if isinstance(payload.get("closed"), list):
            closed_total += len(payload["closed"])
    return {"events_total": len(events), "by_type": by_type, "closed_total": closed_total}

# ====================================
# 5) Consolidação do relatório (núcleo)
# ====================================
def build_report(
    reader: RiskGuardMT5Reader,
    since: datetime,
    until: datetime,
    notify: bool = False,
    magic_list: Optional[List[int]] = None,
    manual_only: bool = False
) -> Dict[str, Any]:
    snap = reader.snapshot()
    try:
        set_ident_from_snapshot(snap, label="RiskGuard")
    except Exception:
        pass

    account = snap.get("account") or {}
    balance_now = float(account.get("balance") or 0.0)
    equity_now = float(account.get("equity") or 0.0)

    deals_all = fetch_deals_raw(reader, since, until)
    trade_deals = [d for d in deals_all if not _rg_is_flow_deal(d)]
    trade_deals = filter_deals(trade_deals, magic_list, manual_only)
    flow_deals = [d for d in deals_all if _rg_is_flow_deal(d)]
    curve_deals = sorted(flow_deals + trade_deals, key=lambda d: d.get("time", ""))

    trades = group_trades(trade_deals)
    trades.sort(key=lambda t: t.get("end", ""))
    met = compute_metrics(trades)

    streaks = compute_streaks([t["pnl"] for t in trades])
    qual = compute_expectancy_payoff(trades)

    monthly = group_by_month(trades)
    weekly = group_by_week(trades)
    distro = distro_weekday_hour(trades)

    evs = load_logs_in_range(since, until)
    ev_summary = summarize_riskguard_events(evs)

    eq_points, balance_start, balance_end, trade_delta, flow_delta, total_delta = _rg_make_balance_series(
        curve_deals, balance_now
    )
    qual.update(compute_quality_stats(trades, met, balance_start))
    dd_abs, dd_pct, dd_peak, dd_trough, dd_peak_lab, dd_trough_lab = _max_drawdown_stats(eq_points)
    met["max_dd_abs"] = dd_abs
    met["max_dd_pct"] = dd_pct
    init_ref, min_after = _rg_initial_and_min_balance(curve_deals, balance_start)
    min_balance = min(v for _, v in eq_points) if eq_points else balance_end
    abs_dd = max(0.0, float(init_ref) - float(min_after)) if min_after is not None else 0.0
    abs_dd_pct = (abs_dd / float(init_ref) * 100.0) if init_ref else None
    drawdown = {
        "absolute_balance": round(abs_dd, 2),
        "absolute_balance_pct": round(abs_dd_pct, 2) if abs_dd_pct is not None else None,
        "max_balance": dd_abs,
        "max_balance_pct": dd_pct,
        "peak_balance": round(float(dd_peak or 0.0), 2),
        "trough_balance": round(float(dd_trough or 0.0), 2),
        "start_balance_est": round(float(balance_start or 0.0), 2),
        "initial_balance_ref": round(float(init_ref or 0.0), 2),
        "min_balance": round(float(min_balance or 0.0), 2),
        "since": since.isoformat(),
        "until": until.isoformat(),
    }

    # === Drawdown histórico (desde primeira operação) ===
    history_since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    deals_full = fetch_deals_raw(reader, history_since, until)
    trade_deals_full = [d for d in deals_full if not _rg_is_flow_deal(d)]
    trade_deals_full = filter_deals(trade_deals_full, magic_list, manual_only)
    flow_deals_full = [d for d in deals_full if _rg_is_flow_deal(d)]
    curve_deals_full = sorted(flow_deals_full + trade_deals_full, key=lambda d: d.get("time", ""))
    full_points, full_start, full_end, full_trade_delta, full_flow_delta, full_total_delta = _rg_make_balance_series(
        curve_deals_full, balance_now
    )
    full_dd_abs, full_dd_pct, full_peak, full_trough, full_peak_lab, full_trough_lab = _max_drawdown_stats(full_points)
    full_init_ref, full_min_after = _rg_initial_and_min_balance(curve_deals_full, full_start)
    full_min_balance = min(v for _, v in full_points) if full_points else full_end
    full_abs_dd = max(0.0, float(full_init_ref) - float(full_min_after)) if full_min_after is not None else 0.0
    full_abs_dd_pct = (full_abs_dd / float(full_init_ref) * 100.0) if full_init_ref else None
    full_since_label = curve_deals_full[0].get("time") if curve_deals_full else history_since.isoformat()
    drawdown_history = {
        "absolute_balance": round(full_abs_dd, 2),
        "absolute_balance_pct": round(full_abs_dd_pct, 2) if full_abs_dd_pct is not None else None,
        "max_balance": full_dd_abs,
        "max_balance_pct": full_dd_pct,
        "peak_balance": round(float(full_peak or 0.0), 2),
        "trough_balance": round(float(full_trough or 0.0), 2),
        "start_balance_est": round(float(full_start or 0.0), 2),
        "initial_balance_ref": round(float(full_init_ref or 0.0), 2),
        "min_balance": round(float(full_min_balance or 0.0), 2),
        "since": full_since_label,
        "until": until.isoformat(),
    }

    eq_daily = _rg_daily_equity(eq_points, since, until)
    monthly_gain_pct: Dict[str, float] = {}
    if eq_daily:
        first_by_month, last_by_month = {}, {}
        for day, eq in eq_daily:
            key = day[:7]
            first_by_month.setdefault(key, float(eq))
            last_by_month[key] = float(eq)
        for key in sorted(last_by_month):
            first = first_by_month.get(key, 0.0)
            last = last_by_month.get(key, 0.0)
            if first > 0:
                monthly_gain_pct[key] = round((last / first - 1.0) * 100.0, 2)

    deps_period, wdr_period = _rg_extract_flows_from_deals(deals_all)
    dep_period_sum = sum(v for _, v in deps_period)
    wdr_period_sum = sum(v for _, v in wdr_period)
    net_flows_period = dep_period_sum - wdr_period_sum

    deps_all, wdr_all = _rg_fetch_all_flows(until)
    total_dep = sum(v for _, v in deps_all)
    total_wdr = sum(v for _, v in wdr_all)
    saldo_fluxos = total_dep - total_wdr

    scope = "filtered" if (magic_list or manual_only) else "account"
    validation = {
        "scope": scope,
        "balance_now": round(balance_now, 2),
        "equity_now": round(equity_now, 2),
        "floating_pnl": round(equity_now - balance_now, 2),
        "balance_start_est": round(balance_start, 2),
        "balance_end_est": round(balance_end, 2),
        "trade_pnl_period": round(trade_delta, 2),
        "trade_pnl_reported": round(float(met.get("net_pnl") or 0.0), 2),
        "trade_pnl_diff": round(float(met.get("net_pnl") or 0.0) - trade_delta, 2),
        "flows_period_deposits": round(dep_period_sum, 2),
        "flows_period_withdrawals": round(wdr_period_sum, 2),
        "net_flows_period": round(net_flows_period, 2),
        "balance_delta_period": round(total_delta, 2),
    }

    summary = {
        "period": {"since": since.isoformat(), "until": until.isoformat()},
        "account": {
            "login": account.get("login"),
            "server": account.get("server"),
            "currency": account.get("currency"),
        },
        "equity_now": equity_now,
        "metrics": met,
        "quality": {
            **qual,
            "win_streak": streaks["win_streak"],
            "loss_streak": streaks["loss_streak"],
            "max_dd_abs_curve": dd_abs,
            "max_dd_pct_curve": dd_pct,
            "max_dd_window": {"from": dd_peak_lab, "to": dd_trough_lab},
        },
        "drawdown": drawdown,
        "period_tables": {
            "monthly": monthly,
            "weekly": weekly,
            "monthly_gain_pct": monthly_gain_pct,
        },
        "distribution": distro,
        "riskguard": ev_summary,
        "flows_summary": {
            "total_deposits": round(total_dep, 2),
            "total_withdrawals": round(total_wdr, 2),
            "net_flows": round(saldo_fluxos, 2),
        },
        "timeseries": {
            "equity": eq_points,
            "equity_daily": eq_daily,
            "flows": {"deposit": deps_period, "withdrawal": wdr_period},
        },
        "validation": validation,
        "drawdown_history": drawdown_history,
    }

    # Outputs
    ts_tag = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{account.get('login')}_{ts_tag}"

    csv_path = OUT_DIR / f"trades_{base}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["position_id","symbol","volume","pnl","start","end","holding_sec","type"])
        for t in trades:
            w.writerow([
                t["position_id"], t["symbol"], t["volume"], f"{t['pnl']:.2f}",
                t["start"], t["end"], int(t["holding_time_sec"]), t["type"]
            ])

    # Console
    print("\n=== RiskGuard Performance Report ===")
    print(f"Conta: {account.get('login')} | Servidor: {account.get('server')} | Moeda: {account.get('currency')}")
    print(f"Período: {since.date()} até {until.date()}")
    print(f"Balance agora: {_fmt_usd(balance_now)} | Equity agora: {_fmt_usd(equity_now)} | Floating: {_fmt_usd(equity_now - balance_now)}")
    pf_console = met["profit_factor"] if met["profit_factor"] is not None else "N/D"
    print(f"Trades: {met['trades']} | Win%: {met['win_rate']:.2f}% | PF: {pf_console}")
    print(f"PnL Bruto: {_fmt_usd(met['gross_profit'])} / {_fmt_usd(-met['gross_loss'])} | Net: {_fmt_usd(met['net_pnl'])}")
    dd_abs_pct_str = f"{drawdown.get('absolute_balance_pct'):.2f}%" if drawdown.get("absolute_balance_pct") is not None else "N/D"
    print(f"DD absoluto (saldo): {_fmt_usd(drawdown.get('absolute_balance'))} ({dd_abs_pct_str} do saldo inicial)")
    if met["max_dd_pct"] is not None:
        print(f"DD maximo (saldo): {_fmt_usd(met['max_dd_abs'])} ({met['max_dd_pct']:.2f}%)")
    else:
        print(f"DD maximo (saldo): {_fmt_usd(met['max_dd_abs'])}")
    if drawdown_history:
        dh_abs_pct_str = f"{drawdown_history.get('absolute_balance_pct'):.2f}%" if drawdown_history.get("absolute_balance_pct") is not None else "N/D"
        print(f"DD absoluto (hist.): {_fmt_usd(drawdown_history.get('absolute_balance'))} ({dh_abs_pct_str} do saldo inicial)")
        if drawdown_history.get("max_balance_pct") is not None:
            print(f"DD maximo (hist.): {_fmt_usd(drawdown_history.get('max_balance'))} ({drawdown_history.get('max_balance_pct'):.2f}%)")
        else:
            print(f"DD maximo (hist.): {_fmt_usd(drawdown_history.get('max_balance'))}")
    if met["best_trade"]:
        print(f"Melhor: {_fmt_usd(met['best_trade']['pnl'])} | Pior: {_fmt_usd(met['worst_trade']['pnl'])}")
    print(f"Tempo médio por trade: {_seconds_to_hms(met['avg_holding'] or 0)}")
    print(f"Symbols com maior impacto: {list(met['pnl_by_symbol'].items())[:5]}")
    exp_payoff = qual.get("expected_payoff", qual.get("expectancy", 0.0))
    payoff_ratio = qual.get("payoff_ratio")
    payoff_ratio_str = f"{payoff_ratio:.2f}" if payoff_ratio is not None else "N/D"
    print(f"Payoff (MT5): {_fmt_usd(exp_payoff)} | Payoff ratio: {payoff_ratio_str}")
    print(f"Streaks -> Win: {streaks['win_streak']} | Loss: {streaks['loss_streak']}")
    print(f"Mensal ($): {monthly}")
    print(f"Semanal ($): {weekly}")
    print(f"Distro por dia: {distro['by_weekday']}")
    print(f"Distro por hora: {distro['by_hour']}")
    print(f"Eventos RiskGuard: {ev_summary}")
    print(f"Fluxos no período: Depósitos {_fmt_usd(dep_period_sum)} | Retiradas {_fmt_usd(wdr_period_sum)} | Líquido {_fmt_usd(net_flows_period)}")
    print(f"Balance início estimado: {_fmt_usd(balance_start)} | Variação período: {_fmt_usd(total_delta)}")

    # === MONTE CARLO ======================================
    print("\n=== Monte Carlo Simulation ===")

    MC_ITER = 5000
    MC_TRADES = max(100, len(trades))
    MC_METHOD = "block"
    MC_BLOCK = 5
    MC_RISK_PCT = get_float("MC_RISK_PCT", 0.01)
    MC_DD_LIMIT = get_float("MC_DD_LIMIT", 0.30)

    try:
        mc_start_equity = float(summary.get("equity_now") or 0.0) - float(met.get("net_pnl") or 0.0)
        if mc_start_equity <= 1e-6:
            mc_start_equity = float(summary.get("equity_now") or 1000.0)
    except Exception:
        mc_start_equity = float(summary.get("equity_now") or 0.0)

    trades_for_mc = [
        t for t in trades
        if int(t.get("position_id", 0)) != 0
        and str(t.get("symbol") or "").strip() != ""
        and abs(float(t.get("pnl", 0.0))) >= 0.05
    ]

    try:
        R_hist, est_risk_pct = compute_R_from_trades(
            trades_for_mc if len(trades_for_mc) >= 5 else trades,
            equity_start=mc_start_equity,
            fallback_risk_pct=MC_RISK_PCT,
        )
        print(f"[DEBUG] MonteCarlo: trades_for_mc={len(trades_for_mc)} | R_hist={len(R_hist)} | risk_pct~{est_risk_pct:.3%}")
    except Exception as e:
        print("[WARN] Falha ao calcular R_hist:", e)
        R_hist = np.array([-1.0, -0.5, -0.25, 0.25, 0.5, 1.0, 2.0])
        est_risk_pct = MC_RISK_PCT

    paths = simulate_paths(
        returns_R=R_hist,
        start_equity=mc_start_equity if mc_start_equity > 0 else (summary.get("equity_now") or 1000.0),
        risk_pct=est_risk_pct,
        n_trades=MC_TRADES,
        iterations=MC_ITER,
        method=MC_METHOD,
        block_size=MC_BLOCK,
        fee_per_trade=0.0,
        seed=42
    )

    mc_summary = summarize_paths(
        paths,
        start_equity=mc_start_equity if mc_start_equity > 0 else (summary.get("equity_now") or 1000.0),
        dd_limit_pct=MC_DD_LIMIT
    )

    fan_path = dd_path = None
    try:
        fig_fan = mc_fig_fanchart(paths, title="")
        fan_path = OUT_DIR / f"mc_fanchart_{base}.svg"
        fig_fan.savefig(fan_path, format="svg", bbox_inches="tight")

        fig_dd = mc_fig_dd_hist(paths, bins=30, title="")
        dd_path = OUT_DIR / f"mc_dd_hist_{base}.svg"
        fig_dd.savefig(dd_path, format="svg", bbox_inches="tight")
    except Exception as e:
        print("[MC] Aviso: não foi possível gerar figuras (ok):", repr(e))
        fan_path = dd_path = None

    tabela_mc = mc_table(mc_summary)

    summary["monte_carlo"] = {
        "config": {
            "iterations": MC_ITER,
            "n_trades": MC_TRADES,
            "method": MC_METHOD,
            "block_size": MC_BLOCK,
            "risk_pct": float(est_risk_pct),
            "dd_limit_pct": MC_DD_LIMIT,
            "start_equity": mc_start_equity,
        },
        "final_equity": mc_summary["final_equity"],
        "final_pnl": mc_summary["final_pnl"],
        "final_return_pct": mc_summary["final_return_pct"],
        "max_drawdown": mc_summary["max_drawdown"],
        "prob_ruin_peak": mc_summary.get("prob_ruin_peak"),
        "prob_ruin_floor": mc_summary.get("prob_ruin_floor"),
        "table": tabela_mc,
        "plots": {
            "fan_chart": str(fan_path) if fan_path else None,
            "dd_hist":   str(dd_path)  if dd_path  else None,
        }
    }

    print("Monte Carlo concluído.")

    # === HTML e PDF ===
    html_path = OUT_DIR / f"report_{account.get('login')}_{ts_tag}.html"
    try:
        render_react_html(summary, html_path)
    except Exception as e:
        print(f"[reports] react render failed: {e}")
        render_html(summary, html_path)

    pdf_path = OUT_DIR / f"report_{account.get('login')}_{ts_tag}.pdf"
    ok_pdf = html_to_pdf(html_path, pdf_path)  # Playwright

    json_path = OUT_DIR / f"summary_{base}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    print("\nArquivos salvos:")
    print(f" - Trades CSV: {csv_path}")
    print(f" - Summary JSON: {json_path}")

    if notify:
        notify_report(
            period_from=str(since.date()),
            period_to=str(until.date()),
            account={
                "login": account.get("login"),
                "server": account.get("server"),
                "currency": account.get("currency"),
                "equity": account.get("equity"),
            },
            met=met,
            ev_summary=ev_summary
        )
        if ok_pdf and pdf_path.exists():
            send_document(str(pdf_path), caption="📊 Relatório de Performance")
        else:
            print(f"Aviso: PDF não gerado. HTML disponível em '{html_path}'.")

    return summary

# =========================
# HTML (MT5) offline report
# =========================
def build_report_from_html(path: Path) -> Dict[str, Any]:
    parsed = _parse_mt5_html_report(path)
    trades = parsed.get("trades", [])
    trades.sort(key=lambda t: t.get("end", ""))

    met = compute_metrics(trades)
    streaks = compute_streaks([t["pnl"] for t in trades])
    qual = compute_expectancy_payoff(trades)
    qual.update(compute_quality_stats(trades, met, parsed.get("start_balance")))

    monthly = group_by_month(trades)
    weekly = group_by_week(trades)
    distro = distro_weekday_hour(trades)

    account = parsed.get("account", {})
    balance_now = float(parsed.get("end_balance") or 0.0)
    equity_now = balance_now

    drawdown = parsed.get("drawdown", {}) or {}
    balance_points = parsed.get("balance_points") or []
    if balance_points:
        eq_points = [(t.split("T")[0] if "T" in t else t.split(" ")[0], float(v)) for t, v in balance_points]
    else:
        eq_points = _rg_make_equity_series(trades, equity_now, met.get("net_pnl", 0.0))

    since_str = (parsed.get("period") or {}).get("since")
    until_str = (parsed.get("period") or {}).get("until")
    since_dt = datetime.fromisoformat(since_str) if since_str else None
    until_dt = datetime.fromisoformat(until_str) if until_str else None

    eq_daily = _rg_daily_equity(eq_points, since_dt, until_dt) if since_dt and until_dt else []
    monthly_gain_pct: Dict[str, float] = {}
    if eq_daily:
        first_by_month, last_by_month = {}, {}
        for day, eq in eq_daily:
            key = day[:7]
            first_by_month.setdefault(key, float(eq))
            last_by_month[key] = float(eq)
        for key in sorted(last_by_month):
            first = first_by_month.get(key, 0.0)
            last = last_by_month.get(key, 0.0)
            if first > 0:
                monthly_gain_pct[key] = round((last / first - 1.0) * 100.0, 2)

    flows = parsed.get("flows", {})
    validation = {
        "scope": "mt5_html",
        "balance_now": round(balance_now, 2),
        "equity_now": round(equity_now, 2),
        "floating_pnl": 0.0,
        "balance_start_est": round(float(parsed.get("start_balance") or 0.0), 2),
        "balance_end_est": round(balance_now, 2),
        "trade_pnl_period": round(float(met.get("net_pnl") or 0.0), 2),
        "trade_pnl_reported": round(float(met.get("net_pnl") or 0.0), 2),
        "trade_pnl_diff": 0.0,
        "flows_period_deposits": round(float(flows.get("deposits") or 0.0), 2),
        "flows_period_withdrawals": round(float(flows.get("withdrawals") or 0.0), 2),
        "net_flows_period": round(float(flows.get("net") or 0.0), 2),
        "balance_delta_period": round(balance_now - float(parsed.get("start_balance") or 0.0), 2),
    }

    summary = {
        "period": {
            "since": since_str or "",
            "until": until_str or "",
        },
        "account": {
            "login": account.get("login"),
            "server": account.get("server"),
            "currency": account.get("currency"),
        },
        "equity_now": equity_now,
        "metrics": met,
        "quality": {
            **qual,
            "win_streak": streaks["win_streak"],
            "loss_streak": streaks["loss_streak"],
            "max_dd_abs_curve": drawdown.get("max_balance", 0.0),
            "max_dd_pct_curve": drawdown.get("max_balance_pct", 0.0),
            "max_dd_window": {
                "from": None,
                "to": None,
            },
        },
        "drawdown": drawdown,
        "period_tables": {
            "monthly": monthly,
            "weekly": weekly,
            "monthly_gain_pct": monthly_gain_pct,
        },
        "distribution": distro,
        "riskguard": {"events_total": 0, "by_type": {}, "closed_total": 0},
        "flows_summary": {
            "total_deposits": round(float(flows.get("deposits") or 0.0), 2),
            "total_withdrawals": round(float(flows.get("withdrawals") or 0.0), 2),
            "net_flows": round(float(flows.get("net") or 0.0), 2),
        },
        "timeseries": {
            "equity": eq_points,
            "equity_daily": eq_daily,
            "flows": {"deposit": [], "withdrawal": []},
        },
        "validation": validation,
        "drawdown_history": {},
    }

    # Base (para arquivos de saida)
    ts_tag = datetime.now().strftime("%Y%m%d-%H%M%S")
    login_tag = account.get("login") or "mt5_html"
    base = f"{login_tag}_{ts_tag}"

    # === MONTE CARLO (offline) ===
    try:
        MC_ITER = 5000
        MC_TRADES = max(100, len(trades))
        MC_METHOD = "block"
        MC_BLOCK = 5
        MC_RISK_PCT = get_float("MC_RISK_PCT", 0.01)
        MC_DD_LIMIT = get_float("MC_DD_LIMIT", 0.30)

        try:
            mc_start_equity = float(summary.get("equity_now") or 0.0) - float(met.get("net_pnl") or 0.0)
            if mc_start_equity <= 1e-6:
                mc_start_equity = float(summary.get("equity_now") or 1000.0)
        except Exception:
            mc_start_equity = float(summary.get("equity_now") or 0.0)

        trades_for_mc = [
            t for t in trades
            if int(t.get("position_id", 0)) != 0
            and str(t.get("symbol") or "").strip() != ""
            and abs(float(t.get("pnl", 0.0))) >= 0.05
        ]

        try:
            R_hist, est_risk_pct = compute_R_from_trades(
                trades_for_mc if len(trades_for_mc) >= 5 else trades,
                equity_start=mc_start_equity,
                fallback_risk_pct=MC_RISK_PCT,
            )
        except Exception:
            R_hist = np.array([-1.0, -0.5, -0.25, 0.25, 0.5, 1.0, 2.0])
            est_risk_pct = MC_RISK_PCT

        paths = simulate_paths(
            returns_R=R_hist,
            start_equity=mc_start_equity if mc_start_equity > 0 else (summary.get("equity_now") or 1000.0),
            risk_pct=est_risk_pct,
            n_trades=MC_TRADES,
            iterations=MC_ITER,
            method=MC_METHOD,
            block_size=MC_BLOCK,
            fee_per_trade=0.0,
            seed=42
        )

        mc_summary = summarize_paths(
            paths,
            start_equity=mc_start_equity if mc_start_equity > 0 else (summary.get("equity_now") or 1000.0),
            dd_limit_pct=MC_DD_LIMIT
        )

        fan_path = dd_path = None
        try:
            fig_fan = mc_fig_fanchart(paths, title="")
            fan_path = OUT_DIR / f"mc_fanchart_{base}.svg"
            fig_fan.savefig(fan_path, format="svg", bbox_inches="tight")

            fig_dd = mc_fig_dd_hist(paths, bins=30, title="")
            dd_path = OUT_DIR / f"mc_dd_hist_{base}.svg"
            fig_dd.savefig(dd_path, format="svg", bbox_inches="tight")
        except Exception as e:
            print(f"[reports] MC plotting failed: {e}")
            fan_path = dd_path = None

        tabela_mc = mc_table(mc_summary)

        summary["monte_carlo"] = {
            "config": {
                "iterations": MC_ITER,
                "n_trades": MC_TRADES,
                "method": MC_METHOD,
                "block_size": MC_BLOCK,
                "risk_pct": float(est_risk_pct),
                "dd_limit_pct": MC_DD_LIMIT,
                "start_equity": mc_start_equity,
            },
            "final_equity": mc_summary["final_equity"],
            "final_pnl": mc_summary["final_pnl"],
            "final_return_pct": mc_summary["final_return_pct"],
            "max_drawdown": mc_summary["max_drawdown"],
            "prob_ruin_peak": mc_summary.get("prob_ruin_peak"),
            "prob_ruin_floor": mc_summary.get("prob_ruin_floor"),
            "table": tabela_mc,
            "plots": {
                "fan_chart": str(fan_path) if fan_path else None,
                "dd_hist":   str(dd_path)  if dd_path  else None,
            }
        }
    except Exception:
        pass

    # Outputs

    csv_path = OUT_DIR / f"trades_{base}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["position_id","symbol","volume","pnl","start","end","holding_sec","type"])
        for t in trades:
            w.writerow([
                t["position_id"], t["symbol"], t["volume"], f"{t['pnl']:.2f}",
                t["start"], t["end"], int(t["holding_time_sec"]), t["type"]
            ])

    html_path = OUT_DIR / f"report_{login_tag}_{ts_tag}.html"
    try:
        render_react_html(summary, html_path)
    except Exception as e:
        print(f"[reports] react render failed: {e}")
        render_html(summary, html_path)

    pdf_path = OUT_DIR / f"report_{login_tag}_{ts_tag}.pdf"
    ok_pdf = html_to_pdf(html_path, pdf_path, mode="raster_pdf")

    json_path = OUT_DIR / f"summary_{base}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    print("\n=== RiskGuard Performance Report (MT5 HTML) ===")
    print(f"Conta: {account.get('login')} | Servidor: {account.get('server')} | Moeda: {account.get('currency')}")
    print(f"Período: {since_str or '-'} até {until_str or '-'}")
    print(f"Balance agora: {_fmt_usd(balance_now)} | Equity agora: {_fmt_usd(equity_now)}")
    print(f"Trades: {met['trades']} | Win%: {met['win_rate']:.2f}%")
    print(f"Net PnL: {_fmt_usd(met['net_pnl'])}")
    print(f"Payoff (MT5): {_fmt_usd(qual['expected_payoff'])} | Payoff ratio: {qual['payoff_ratio'] if qual['payoff_ratio'] is not None else 'N/D'}")
    print("\nArquivos salvos:")
    print(f" - Trades CSV: {csv_path}")
    print(f" - Summary JSON: {json_path}")
    if ok_pdf and pdf_path.exists():
        print(f" - PDF: {pdf_path}")
    else:
        print(f" - HTML: {html_path}")

    return summary

# =========
# 6) CLI
# =========
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", type=str, help="YYYY-MM-DD (inclusivo)")
    parser.add_argument("--to", dest="date_to", type=str, help="YYYY-MM-DD (exclusivo; default=amanhã)")
    parser.add_argument("--mt5-html", dest="mt5_html", type=str, help="Caminho para relatório HTML do MT5 (offline)")
    parser.add_argument("--notify", action="store_true", help="Enviar resumo para o Telegram")
    parser.add_argument("--terminal", type=str, help="Caminho do terminal MT5 (opcional)")
    parser.add_argument("--magic", type=str, help="Lista de magic numbers separados por vírgula (ex: 123,9999)")
    parser.add_argument("--manual-only", action="store_true", help="Somente operações manuais (magic=0)")
    args = parser.parse_args()

    if args.mt5_html:
        build_report_from_html(Path(args.mt5_html))
        return

    date_to = _dt(args.date_to) if args.date_to else (_now_utc().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
    if args.date_from:
        date_from = _dt(args.date_from)
    else:
        date_from = date_to - timedelta(days=30)  # padrão: últimos 30 dias

    reader = RiskGuardMT5Reader(path=args.terminal)
    assert reader.connect(), "Falha ao conectar no MT5"
    try:
        summary = build_report(
            reader,
            since=date_from,
            until=date_to,
            notify=args.notify,
            magic_list=_parse_magic_list(args.magic),
            manual_only=args.manual_only
        )
    finally:
        reader.shutdown()

if __name__ == "__main__":
    main()
