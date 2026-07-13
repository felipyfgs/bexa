# AGENTS.md — bexa

Instruções curtas para agentes. Não repita o que o código/README já deixam óbvio.

## Idioma

- Responder o usuário em **pt-BR**.
- Artefatos OpenSpec (`proposal`, `design`, `tasks`, specs) em **pt-BR**.
- IDs de change em kebab-case (podem ser em inglês); código/identificadores em inglês ok.

## O que é este repo

App Python sobre **ebinexpy** para operar a sala **Ebinex** (OPTION).  
Código em `src/bexa/` (features: connection, market, execution, strategy, risk, bot).  
Não reimplementar protocolo Ebinex — estender features e usar `EbinexClient`.

## Comandos

```bash
python3 -m pip install -e '.[dev]'
pytest
ruff check src tests
bexa status
bexa run --strategy candle_color          # dry-run
bexa run --strategy candle_color --live   # envia ordens
```

## Domínio Ebinex (não óbvio)

- Conta padrão **TEST**. **REAL** só com opt-in explícito no config (`allow_real_trading`).
- Ordem OPTION: envio agora → **entrada na vela seguinte** → **liquidação no fim dessa vela**.
- **Corte de entrada M1:** a partir do **segundo 55** da vela corrente CALL/PUT somem — não enviar (`entry_window` em `execution/timing.py`). Outros TF: últimos ~5s da vela.
- Wait de settlement ≈ até 2× timeframe + buffer (não usar timeout curto tipo 35s).
- Segredos só em `.env` (`EBINEX_EMAIL`, `EBINEX_PASSWORD`). Nunca commitar.

## Como trabalhar no código

- Layout modular por feature em `src/bexa/<feature>/`.
- Diffs pequenos e no escopo do pedido; sem refactors laterais.
- Defaults de config no código (`config.py`); não inventar dezenas de env vars.
- Trabalho não trivial: preferir OpenSpec (skills Grok em `.grok/skills/`, CLI `openspec`). Detalhes de schema/CLI estão nas skills — não duplicar aqui.
  - `/openspec-explore` · `/openspec-propose` · `/openspec-apply-change` · `/openspec-sync-specs` · `/openspec-archive-change`
- Testes/lint verdes quando o change toca código.

## Segurança

- Nunca habilitar REAL ou auto-trade “por padrão”.
- Não logar senha/token.
- Ordem LIVE só com intenção clara do usuário (`--live` / gates do projeto).
