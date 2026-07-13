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

## Segurança e domínio (resumo)

- Conta padrão: **TEST**. REAL só com opt-in explícito no env/config.
- OPTION: envio agora → **entrada na vela seguinte** → liquidação no **fim** dela.
- **Corte M1:** a partir do segundo **55** da vela, CALL/PUT somem — o bexa bloqueia envio.
- Detalhes para agentes: ver `AGENTS.md`.

## CLI rápida

```bash
bexa status

# ordem TEST (gate de demo se o CLI exigir)
BEXA_ALLOW_DEMO_ORDER=YES_ONE_DEMO_ORDER \
  bexa demo-order --direction CALL --investment 1
```

## Robô automático

Sinal no fechamento da vela; na Ebinex a entrada é na **vela seguinte**.

```bash
# Dry-run (não envia ordens)
BEXA_ALLOW_BOT=YES_RUN_BOT bexa run --strategy candle_color --dry-run

# LIVE em TEST
BEXA_ALLOW_BOT=YES_RUN_BOT bexa run --strategy candle_color --live --max-trades 3 --investment 1

# LIVE em REAL (opt-ins fortes no env — ver config/CLI)
BEXA_ENVIRONMENT=REAL \
BEXA_ALLOW_REAL_TRADING=YES_REAL_TRADING \
BEXA_ALLOW_AUTO_REAL_TRADE=YES_AUTO_REAL_TRADE \
BEXA_ALLOW_BOT=YES_RUN_BOT \
  bexa run --strategy candle_color --live --max-trades 3
```

Estratégias: `hold`, `candle_color` (ou `register_strategy`).  
Instruções para agentes: `AGENTS.md`.

## Desenvolvimento

```bash
.venv/bin/ruff check src tests
.venv/bin/pytest
```
