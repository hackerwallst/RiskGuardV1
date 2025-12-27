from __future__ import annotations

import argparse
import sys
import time

from notify import send_alert, telegram_poll_chat_messages


def parse_args():
    p = argparse.ArgumentParser(description="RiskGuard Telegram debug (send + getUpdates)")
    p.add_argument("--wait-sec", type=int, default=90, help="Tempo máximo para aguardar a resposta (segundos)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # 1) Sync offset (evita ler histórico antigo)
    _, offset = telegram_poll_chat_messages(None)

    # 2) Envia mensagem de teste
    ok = send_alert("🧪 Telegram Debug", [
        "Responda com um número:",
        "  1 = teste OK (opção 1)",
        "  2 = teste OK (opção 2)",
        "",
        f"Tempo limite: {args.wait_sec}s",
    ])
    if not ok:
        print("Falha ao enviar mensagem. Verifique TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID (config.txt).")
        return 2

    # 3) Aguarda resposta
    deadline = time.time() + float(args.wait_sec)
    while time.time() < deadline:
        msgs, offset2 = telegram_poll_chat_messages(offset, timeout=10)
        if offset2 is not None:
            offset = offset2
        for m in msgs:
            if not isinstance(m, dict) or m.get("from_is_bot"):
                continue
            text = (m.get("text") or "").strip()
            if text in ("1", "2"):
                print(f"OK: recebido '{text}' via getUpdates.")
                return 0
        time.sleep(0.3)

    print("Timeout: não recebi '1' ou '2' via getUpdates.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

