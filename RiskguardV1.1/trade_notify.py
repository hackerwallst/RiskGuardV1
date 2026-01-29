from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timezone, timedelta
import html

from logger import log_event
from mt5_reader import RiskGuardMT5Reader
from notify import send_alert


def _h(v: Any) -> str:
    return html.escape(str(v), quote=False)


def _fmt_money(x: Any) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "N/D"


def _fmt_price(x: Any, digits: int) -> str:
    try:
        if x is None:
            return "—"
        v = float(x)
        if v == 0.0:
            return "—"
        return f"{v:.{int(digits)}f}"
    except Exception:
        return "—"


def _fmt_volume(x: Any) -> str:
    try:
        return f"{float(x):.2f}"
    except Exception:
        return "N/D"


def _fmt_side(side: Any) -> str:
    s = str(side or "").lower()
    if s == "buy":
        return "BUY"
    if s == "sell":
        return "SELL"
    return str(side or "").upper() or "N/D"


def _server_dt_from_epoch(ts: Any) -> Optional[datetime]:
    try:
        if ts is None:
            return None
        v = int(ts)
        if v <= 0:
            return None
        # No MT5, o "time" costuma estar no fuso do servidor; usamos tz=UTC apenas como container.
        return datetime.fromtimestamp(v, tz=timezone.utc)
    except Exception:
        return None


def _fmt_server_time(ts: Any) -> str:
    dt = _server_dt_from_epoch(ts)
    if not dt:
        return "N/D"
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _fmt_duration(seconds: Any) -> str:
    try:
        sec = int(float(seconds))
        if sec < 0:
            sec = 0
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return "N/D"


def _pre(lines: List[str]) -> str:
    return "<pre>" + "\n".join(lines) + "</pre>"


def _position_to_state(pos: Dict[str, Any]) -> Dict[str, Any]:
    symbol_info = pos.get("symbol_info") or {}
    current_price = pos.get("current_price")
    floating_pnl = pos.get("floating_pnl")
    return {
        "ticket": int(pos.get("ticket", 0) or 0),
        "symbol": str(pos.get("symbol") or ""),
        "type": str(pos.get("type") or ""),
        "volume": float(pos.get("volume") or 0.0),
        "open_price": float(pos.get("open_price") or 0.0),
        "open_time_epoch": int(pos.get("open_time_epoch") or 0),
        "sl": float(pos.get("sl") or 0.0) if pos.get("sl") not in (None, 0.0) else None,
        "tp": float(pos.get("tp") or 0.0) if pos.get("tp") not in (None, 0.0) else None,
        "risk_pct": float(pos.get("risk_pct")) if isinstance(pos.get("risk_pct"), (int, float)) else None,
        "magic": int(pos.get("magic") or 0),
        "comment": str(pos.get("comment") or ""),
        "digits": int(symbol_info.get("digits") or 5),
        "point": float(symbol_info.get("point") or 0.0),
        "current_price": float(current_price) if isinstance(current_price, (int, float)) and float(current_price) != 0.0 else None,
        "floating_pnl": float(floating_pnl) if isinstance(floating_pnl, (int, float)) else None,
    }


def _deal_time_epoch(deal: Any) -> Optional[int]:
    t = getattr(deal, "time", None)
    if isinstance(t, datetime):
        try:
            return int(t.replace(tzinfo=timezone.utc).timestamp())
        except Exception:
            return None
    try:
        if t is None:
            return None
        return int(t)
    except Exception:
        return None


def _deals_for_position(reader: RiskGuardMT5Reader, position_ticket: int,
                        since_epoch: Optional[int], symbol: Optional[str] = None) -> List[Any]:
    try:
        import MetaTrader5 as mt5
    except Exception:
        return []

    reader.ensure_connection()

    # 1) Preferência: consulta direta por position_id (mais confiável e rápida).
    try:
        deals = mt5.history_deals_get(position=int(position_ticket))
    except Exception:
        deals = None
    if deals:
        return list(deals)

    # 2) Fallback: janela temporal (útil se o broker não preenche position_id corretamente).
    now_dt = datetime.now(timezone.utc)
    if since_epoch and since_epoch > 0:
        from_dt = datetime.fromtimestamp(int(since_epoch), tz=timezone.utc) - timedelta(minutes=10)
    else:
        from_dt = now_dt - timedelta(days=7)
    to_dt = now_dt + timedelta(minutes=10)

    try:
        if symbol:
            deals = mt5.history_deals_get(from_dt, to_dt, group=str(symbol))
        else:
            deals = mt5.history_deals_get(from_dt, to_dt)
    except Exception:
        deals = None
    if deals is None:
        return []

    out: List[Any] = []
    for d in deals:
        try:
            pid = getattr(d, "position_id", None)
            if pid is None:
                pid = getattr(d, "position", None)
            if pid is None:
                continue
            if int(pid) == int(position_ticket):
                out.append(d)
        except Exception:
            continue
    return out


def _summarize_closed_position(reader: RiskGuardMT5Reader, pos_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Melhor esforço: usa history_deals_get para obter preço/tempo de saída e PnL.
    """
    ticket = int(pos_state.get("ticket", 0) or 0)
    deals = _deals_for_position(
        reader,
        ticket,
        since_epoch=pos_state.get("open_time_epoch"),
        symbol=pos_state.get("symbol"),
    )
    if not deals:
        approx_pnl = pos_state.get("floating_pnl")
        approx_price = pos_state.get("current_price")
        if isinstance(approx_pnl, (int, float)):
            return {
                "ok": True,
                "approx": True,
                "ticket": ticket,
                "deals_count": 0,
                "close_price": float(approx_price) if isinstance(approx_price, (int, float)) else None,
                "close_time_epoch": None,
                "profit": float(approx_pnl),
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
                "net": float(approx_pnl),
                "deal_comment": "",
            }
        return {"ok": False, "reason": "Sem histórico de deals.", "ticket": ticket}

    try:
        import MetaTrader5 as mt5
        out_entries = {
            getattr(mt5, "DEAL_ENTRY_OUT", 1),
            getattr(mt5, "DEAL_ENTRY_INOUT", 2),
            getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
        }
    except Exception:
        out_entries = {1, 2, 3}

    last_out = None
    last_out_ts = -1
    for d in deals:
        try:
            entry = getattr(d, "entry", None)
            if entry not in out_entries:
                continue
            ts = _deal_time_epoch(d)
            if ts is None:
                continue
            if ts > last_out_ts:
                last_out_ts = ts
                last_out = d
        except Exception:
            continue

    profit = 0.0
    commission = 0.0
    swap = 0.0
    fee = 0.0
    for d in deals:
        try:
            profit += float(getattr(d, "profit", 0.0) or 0.0)
            commission += float(getattr(d, "commission", 0.0) or 0.0)
            swap += float(getattr(d, "swap", 0.0) or 0.0)
            fee += float(getattr(d, "fee", 0.0) or 0.0)
        except Exception:
            continue

    close_price = None
    close_time_epoch = None
    deal_comment = ""
    if last_out is not None:
        try:
            close_price = float(getattr(last_out, "price", 0.0) or 0.0) or None
        except Exception:
            close_price = None
        close_time_epoch = _deal_time_epoch(last_out)
        try:
            deal_comment = str(getattr(last_out, "comment", "") or "")
        except Exception:
            deal_comment = ""

    return {
        "ok": True,
        "approx": False,
        "ticket": ticket,
        "deals_count": len(deals),
        "close_price": close_price,
        "close_time_epoch": close_time_epoch,
        "profit": float(profit),
        "commission": float(commission),
        "swap": float(swap),
        "fee": float(fee),
        "net": float(profit + commission + swap + fee),
        "deal_comment": deal_comment,
    }


def _guess_close_reason(pos_state: Dict[str, Any], close_price: Optional[float]) -> str:
    if close_price is None:
        return "N/D"

    sl = pos_state.get("sl")
    tp = pos_state.get("tp")
    point = float(pos_state.get("point") or 0.0)
    eps = max(point * 2.0, 1e-9)

    try:
        if isinstance(sl, (int, float)) and float(sl) > 0 and abs(float(close_price) - float(sl)) <= eps:
            return "SL"
        if isinstance(tp, (int, float)) and float(tp) > 0 and abs(float(close_price) - float(tp)) <= eps:
            return "TP"
    except Exception:
        pass

    return "N/D"


def _notify_open(pos_state: Dict[str, Any], pertrade_limit_pct: float) -> None:
    symbol = pos_state.get("symbol") or "?"
    ticket = pos_state.get("ticket") or "?"
    digits = int(pos_state.get("digits") or 5)

    sl = pos_state.get("sl")
    tp = pos_state.get("tp")
    risk_pct = pos_state.get("risk_pct")

    risk_line = "N/D"
    if isinstance(risk_pct, (int, float)):
        risk_line = f"{float(risk_pct):.2f}% (limite {float(pertrade_limit_pct):.2f}%)"

    pre_lines = [
        f"Ativo:     {_h(symbol)}",
        f"Ticket:    {_h(ticket)}",
        f"Lado:      {_h(_fmt_side(pos_state.get('type')))}",
        f"Volume:    {_h(_fmt_volume(pos_state.get('volume')))}",
        f"Entrada:   {_h(_fmt_price(pos_state.get('open_price'), digits))}",
        f"SL:        {_h(_fmt_price(sl, digits))}",
        f"TP:        {_h(_fmt_price(tp, digits))}",
        f"Risco:     {_h(risk_line)}",
    ]

    lines: list[str] = [
        "",
        _pre(pre_lines),
        f"🕒 <b>Horário (servidor):</b> {_h(_fmt_server_time(pos_state.get('open_time_epoch')))}",
    ]

    magic = pos_state.get("magic")
    comment = (pos_state.get("comment") or "").strip()
    if (isinstance(magic, int) and magic != 0) or comment:
        tail = []
        if isinstance(magic, int) and magic != 0:
            tail.append(f"magic {magic}")
        if comment:
            tail.append(comment[:120])
        lines.append(f"🧠 <b>EA:</b> {_h(' | '.join(tail))}")

    send_alert("🟢 Nova posição aberta", lines)


def _notify_close(reader: RiskGuardMT5Reader, pos_state: Dict[str, Any]) -> None:
    symbol = pos_state.get("symbol") or "?"
    ticket = pos_state.get("ticket") or "?"
    digits = int(pos_state.get("digits") or 5)
    point = float(pos_state.get("point") or 0.0)

    summ = _summarize_closed_position(reader, pos_state)
    close_price = summ.get("close_price") if summ.get("ok") else None
    close_time_epoch = summ.get("close_time_epoch") if summ.get("ok") else None

    entry_price = pos_state.get("open_price")
    side = str(pos_state.get("type") or "").lower()
    points = None
    try:
        if isinstance(entry_price, (int, float)) and isinstance(close_price, (int, float)) and point > 0:
            if side == "buy":
                points = (float(close_price) - float(entry_price)) / point
            elif side == "sell":
                points = (float(entry_price) - float(close_price)) / point
    except Exception:
        points = None

    pre_lines = [
        f"Ativo:     {_h(symbol)}",
        f"Ticket:    {_h(ticket)}",
        f"Lado:      {_h(_fmt_side(pos_state.get('type')))}",
        f"Volume:    {_h(_fmt_volume(pos_state.get('volume')))}",
        f"Entrada:   {_h(_fmt_price(entry_price, digits))}",
        f"Saída:     {_h(_fmt_price(close_price, digits))}",
    ]

    if points is not None:
        pre_lines.append(f"Pontos:    {_h(f'{points:+.1f}')}")

    if summ.get("ok"):
        pre_lines.append(f"PnL:       {_h(_fmt_money(summ.get('profit')))}")
        pre_lines.append(f"Líquido:   {_h(_fmt_money(summ.get('net')))}")
    else:
        pre_lines.append("PnL:       N/D")

    lines: list[str] = [
        "",
        _pre(pre_lines),
    ]

    if summ.get("ok") and not summ.get("approx"):
        lines.append(
            f"💸 <b>Custos:</b> comissão {_h(_fmt_money(summ.get('commission')))} | swap {_h(_fmt_money(summ.get('swap')))} | fee {_h(_fmt_money(summ.get('fee')))}"
        )
    elif summ.get("ok") and summ.get("approx"):
        lines.append("⚠️ <b>PnL estimado:</b> histórico indisponível no momento.")

    reason = _guess_close_reason(pos_state, close_price)
    if reason != "N/D":
        lines.append(f"📌 <b>Motivo:</b> {_h(reason)}")

    open_epoch = pos_state.get("open_time_epoch")
    if close_time_epoch:
        lines.append(f"🕒 <b>Horário (servidor):</b> {_h(_fmt_server_time(close_time_epoch))}")
        if open_epoch:
            try:
                dur = int(close_time_epoch) - int(open_epoch)
                lines.append(f"⏱ <b>Duração:</b> {_h(_fmt_duration(dur))}")
            except Exception:
                pass

    send_alert("🔴 Posição encerrada", lines)


def sync_and_notify_trades(
    reader: RiskGuardMT5Reader,
    snapshot: Dict[str, Any],
    state: Dict[str, Any],
    pertrade_limit_pct: float,
    enabled: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Sincroniza estado de tickets/posições e envia notificações:
      - 🟢 Nova posição aberta (ticket novo)
      - 🔴 Posição encerrada (ticket sumiu)

    Na primeira execução (state não inicializado), apenas cria baseline (sem alertar).
    """
    st = state if isinstance(state, dict) else {}
    st.setdefault("initialized", False)
    st.setdefault("tickets", [])
    st.setdefault("positions_by_ticket", {})

    prev_tickets = {str(int(x)) for x in (st.get("tickets") or []) if str(x).strip().isdigit()}
    prev_positions: Dict[str, Any] = st.get("positions_by_ticket") if isinstance(st.get("positions_by_ticket"), dict) else {}

    positions = list((snapshot or {}).get("positions") or [])
    curr_states: Dict[str, Any] = {}
    for p in positions:
        tk = int(p.get("ticket", 0) or 0)
        if tk <= 0:
            continue
        curr_states[str(tk)] = _position_to_state(p)

    curr_tickets = set(curr_states.keys())

    report = {
        "new_tickets": sorted([int(x) for x in (curr_tickets - prev_tickets)], key=int),
        "closed_tickets": sorted([int(x) for x in (prev_tickets - curr_tickets)], key=int),
    }

    # Baseline silenciosa (primeiro loop)
    if not st.get("initialized"):
        st["initialized"] = True
        st["tickets"] = sorted([int(x) for x in curr_tickets], key=int)
        st["positions_by_ticket"] = curr_states
        report["new_tickets"] = []
        report["closed_tickets"] = []
        return st, report

    if enabled:
        # Aberturas
        for tk in report["new_tickets"]:
            ps = curr_states.get(str(tk))
            if ps:
                _notify_open(ps, pertrade_limit_pct=pertrade_limit_pct)
                log_event("TRADE_OPEN", ps, {"module": "trade_notify"})

        # Encerramentos
        for tk in report["closed_tickets"]:
            ps = prev_positions.get(str(tk))
            if ps:
                _notify_close(reader, ps)
                log_event("TRADE_CLOSE", ps, {"module": "trade_notify"})

    # Atualizar estado (remove tickets encerrados)
    for tk in report["closed_tickets"]:
        prev_positions.pop(str(tk), None)
    # Atualiza/insere posições atuais
    prev_positions.update(curr_states)

    st["tickets"] = sorted([int(x) for x in curr_tickets], key=int)
    st["positions_by_ticket"] = prev_positions
    return st, report
