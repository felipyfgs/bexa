# bexa

Camada de aplicação em Python sobre [`ebinexpy`](https://github.com/felipyfgs/ebinexpy)
para operar a sala de trading Ebinex de forma modular (por feature).

## Requisitos

- Python 3.11+
- Conta Ebinex (TEST ou REAL)

## Instalação

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
# edite .env com EBINEX_EMAIL e EBINEX_PASSWORD
```

A CLI carrega `.env` automaticamente (não é preciso `export` no shell).

## Estrutura

```
src/bexa/
  config.py          # settings via variáveis de ambiente
  core/              # exceções e logging
  connection/        # factory e ciclo de vida do EbinexClient
  accounts/          # contas, saldo, perfil
  market/            # ativos, candles, preço
  orders/            # consulta e espera de ordens
  execution/         # execução OPTION (inclui REAL com gate)
  risk/              # limites do robô
  strategy/          # estratégias pluggable
  bot/               # motor automático
  cli.py             # entrada de linha de comando
```

## Segurança

- Conta padrão: **TEST**.
- Conta **REAL** exige o literal `BEXA_ALLOW_REAL_TRADING=YES_REAL_TRADING`
  (não aceita `1` / `TRUE` / `YES` genéricos).
- Ordem REAL via CLI exige **três** opt-ins:
  1. `BEXA_ENVIRONMENT=REAL`
  2. `BEXA_ALLOW_REAL_TRADING=YES_REAL_TRADING`
  3. `BEXA_ALLOW_REAL_ORDER=YES_ONE_REAL_ORDER` (só no comando)
- O `ebinexpy` também exige `ClientConfig(allow_real_trading=True)` para ordens REAL.
- Robô LIVE em REAL exige ainda `BEXA_ALLOW_AUTO_REAL_TRADE=YES_AUTO_REAL_TRADE`.

## CLI rápida

```bash
# saldo e ativos (somente leitura; carrega .env sozinho)
bexa status

# ordem mínima em TEST (gate explícito)
BEXA_ALLOW_DEMO_ORDER=YES_ONE_DEMO_ORDER \
  bexa demo-order --symbol IDXUSDT --direction CALL --investment 1

# ordem REAL (triplo opt-in)
BEXA_ENVIRONMENT=REAL \
BEXA_ALLOW_REAL_TRADING=YES_REAL_TRADING \
BEXA_ALLOW_REAL_ORDER=YES_ONE_REAL_ORDER \
  bexa real-order --symbol IDXUSDT --direction CALL --investment 1
```

## Robô automático

O motor escuta o fechamento de vela, consulta a estratégia e (opcionalmente) envia
a ordem. Na Ebinex a entrada efetiva é na **vela seguinte**.

```bash
# 1) Dry-run (recomendado): conecta, lê velas, loga sinais — NÃO envia ordens
BEXA_ALLOW_BOT=YES_RUN_BOT bexa run --strategy candle_color --dry-run

# 2) LIVE em TEST (envia ordens de verdade)
BEXA_ALLOW_BOT=YES_RUN_BOT bexa run --strategy candle_color --live --max-trades 3 --investment 1

# 3) LIVE em REAL (gate extra)
BEXA_ENVIRONMENT=REAL \
BEXA_ALLOW_REAL_TRADING=YES_REAL_TRADING \
BEXA_ALLOW_AUTO_REAL_TRADE=YES_AUTO_REAL_TRADE \
BEXA_ALLOW_BOT=YES_RUN_BOT \
  bexa run --strategy candle_color --live --max-trades 3
```

Estratégias embutidas: `hold` (nunca opera), `candle_color` (pipeline de teste).
Registre a sua com `register_strategy("nome", factory)`.

Gates de segurança do robô:

| Flag | Valor exigido | Efeito |
|------|---------------|--------|
| `BEXA_ALLOW_BOT` | `YES_RUN_BOT` | Permite subir o motor |
| `BEXA_BOT_ENABLED` | `YES` (ou CLI `run`) | Liga o robô |
| `BEXA_BOT_DRY_RUN` | `1` (padrão) | Não envia ordens |
| `BEXA_BOT_AUTO_TRADE` | `YES_AUTO_TRADE` | Habilita envio (com dry_run=0) |
| `BEXA_ALLOW_AUTO_REAL_TRADE` | `YES_AUTO_REAL_TRADE` | LIVE em REAL |

Limites: max trades, max open, cooldown, max daily loss. Stake acima de
`BEXA_MAX_INVESTMENT` é **rejeitado** (não clamado).

## Desenvolvimento

```bash
.venv/bin/ruff check src tests
.venv/bin/pytest
```
