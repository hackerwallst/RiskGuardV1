# RiskGuard

Monitor de risco para MetaTrader 5 que aplica limites operacionais, janela de noticias e relatorios de performance.

## Recursos
- Limite por trade e limite agregado
- Protecao de drawdown e kill switch
- Janela de noticias (calendario economico)
- Alertas por Telegram (opcional)
- Avisos de abertura/fechamento de posicao (opcional)
- Relatorios HTML/PDF e simulacoes Monte Carlo

## Requisitos
- Windows 10+ 64-bit
- MetaTrader 5 instalado
- Python 3.10+ (o script `setup_riskguard.ps1` instala 3.10.11)

## Configuracao
1) Copie `config.example.txt` para `config.txt`
2) Preencha `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` se for usar alertas
3) Ajuste os limites conforme sua operacao

### Per-trade interativo (Telegram)
Opcionalmente, o RiskGuard pode ajustar o SL automaticamente para manter o risco por trade dentro do limite e aguardar sua decisao via Telegram.

- Ative com `PERTRADE_INTERACTIVE=true`
- O RiskGuard envia um alerta com 2 opcoes:
  - `1` = manter SL original (override ate a posicao fechar)
  - `2` = manter SL ajustado (recomendado)
- Sem resposta em `PERTRADE_INTERACTIVE_TIMEOUT_MIN` minutos, o SL ajustado permanece.

`config.txt` nao deve ser commitado (esta no `.gitignore`).

### Abertura/fechamento de posicao (Telegram)
Opcionalmente, o RiskGuard pode notificar toda abertura e todo encerramento de posicao.

- Ative com `TRADE_NOTIFICATIONS=true`
- 🟢 Abertura: mostra ativo, ticket, lado, volume, entrada, SL/TP, risco e horario do servidor.
- 🔴 Fechamento: mostra entrada/saida, pontos, PnL, custos (comissao/swap/fee), liquido, motivo (SL/TP) e duracao.

### Comandos via Telegram
Opcionalmente, o RiskGuard pode responder a comandos enviados no chat configurado.

- Ative com `TELEGRAM_COMMANDS=true`
- Comandos:
  - `/status`   = status completo da conta (saldo, equity, margem, risco, bloqueios)
  - `/positions` = posicoes abertas
  - `/history`  = historico do ultimo mes (resumo + ultimos trades)
  - `/relatorio` = gera e envia o relatorio completo em PDF
- Em grupos com privacy mode do bot ativo, use comandos com `/` ou `/status@SeuBot`.

## Instalacao rapida
```powershell
.\setup_riskguard.ps1
```

## Execucao (UI)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\run_riskguard_ui.ps1
```
ou
```powershell
.\venv\Scripts\python.exe .\riskguard_ui.py
```

## Relatorios
Arquivos gerados ficam em `reports/` (HTML, PDF, CSV, PNG). Eles estao ignorados no `.gitignore`.

## Estrutura do projeto
- `riskguard_ui.py`: interface principal
- `main.py`: loop principal (executado pela UI)
- `limits/`: limites, guardas e kill switch
- `news/`: janela de noticias
- `reports/`: relatorios e simulacoes
- `notify/`: alertas Telegram
- `logger/`: logs

## Publicar no GitHub
Se algum arquivo de cache ja estiver versionado (ex.: `news/ff_cache.json`), remova do indice:
```powershell
git rm --cached news/ff_cache.json
```

Depois, inicialize e envie:
```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

## Mais detalhes
Use `setup_riskguard.ps1` para reinstalar dependencias caso o ambiente quebre.
