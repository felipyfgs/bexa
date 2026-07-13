# AGENTS.md — bexa

Instructions for AI agents working in this repository.

## Idioma (obrigatório)

- **Sempre** responder o usuário em **português do Brasil (pt-BR)**.
- **Sempre** escrever changes e artefatos OpenSpec em **pt-BR**, incluindo:
  - conteúdo de `proposal.md`, `design.md`, `tasks.md`
  - specs (main e delta): requisitos, cenários, descrições
  - resumos de status, progresso e mensagens ao usuário sobre a change
- Nomes de change (diretórios/IDs) podem continuar em **kebab-case em inglês** quando forem identificadores técnicos (ex.: `add-user-auth`); o **conteúdo** dos arquivos da change deve estar em pt-BR.
- Código (identificadores, APIs públicas, commits de tooling) pode seguir convenções da stack em inglês; comentários e docs orientados ao time/usuário preferem pt-BR quando fizer sentido.

## Project status

Aplicação Python **bexa** sobre a biblioteca [`ebinexpy`](https://github.com/felipyfgs/ebinexpy) para operar a Ebinex.

Current structure:

| Path | Role |
|------|------|
| `src/bexa/` | Código da aplicação (modular por feature) |
| `tests/` | Testes (unitários e futuros de integração) |
| `openspec/` | Spec-driven source of truth (specs, changes, project config) |
| `openspec/config.yaml` | OpenSpec schema + optional project context / artifact rules |
| `openspec/specs/` | Main (canonical) capability specs |
| `openspec/changes/` | Active change proposals |
| `openspec/changes/archive/` | Completed changes |
| `.codex/skills/` | OpenSpec agent skills (propose, apply, explore, archive, sync) |

### Stack e layout

- **Python** ≥ 3.11, pacote instalável via Hatchling (`pyproject.toml`)
- **Dependência de broker**: `ebinexpy` (cliente async da sala Ebinex)
- **Layout**: `src/bexa/<feature>/` — features atuais:
  - `core/` — exceções e logging
  - `connection/` — factory e sessão do `EbinexClient`
  - `accounts/` — contas, perfil, saldo
  - `market/` — ativos, candles, preço, streams
  - `orders/` — listagem e wait de ordens
  - `execution/` — execução OPTION com gates de risco/REAL
  - `strategy/` — estratégias pluggable (`hold`, `candle_color`, registro)
  - `risk/` — limites do robô (max trades, open, cooldown, daily loss)
  - `bot/` — motor automático (vela fechada → sinal → execução)
  - `config.py`, `cli.py` — settings e CLI (`status`, `demo-order`, `real-order`, `run`)
- **Build / test / lint**:
  - install: `python3 -m pip install -e '.[dev]'`
  - tests: `pytest`
  - lint: `ruff check src tests`
- **Segredos**: `.env` mínimo com `EBINEX_EMAIL` + `EBINEX_PASSWORD`. Defaults no código (`config.py`); não inflar o env com flags do robô.
- **REAL trading**: `BEXA_ENVIRONMENT=REAL` + `BEXA_ALLOW_REAL_TRADING=1`. Nunca default.
- **Padrão de conta**: TEST; símbolo IDXUSDT; timeframe M1.
- **Ciclo OPTION na Ebinex**: envio agora → **entrada na vela seguinte** → **liquidação no fim da vela seguinte** (`execution/timing.py`).
- **Corte de entrada (UI)**: no M1, a partir do **segundo 55** da vela corrente os botões CALL/PUT somem — não enviar ordem nesse intervalo (`entry_window`, corte 55s; outros TF = últimos 5s da vela).
- **Robô (`bexa run`)**: dry-run por padrão; `--live` envia ordens. Overrides de estratégia/stake/max via CLI, não via dezenas de env vars.

## Default workflow: OpenSpec (spec-driven)

This project uses **OpenSpec** with schema `spec-driven`. Prefer planning through OpenSpec before writing product code.

### Lifecycle

1. **Explore** — clarify problem/scope without implementing (`openspec-explore` skill).
2. **Propose** — create a change with artifacts (`openspec-propose` skill).
3. **Apply** — implement tasks from the change (`openspec-apply-change` skill).
4. **Sync specs** (if needed) — merge delta specs into main specs (`openspec-sync-specs` skill).
5. **Archive** — finalize the change after implementation (`openspec-archive-change` skill).

### Naming

- Change names: **kebab-case** (e.g. `add-user-auth`, `fix-login-redirect`).
- Prefer short, verb-led names that describe the change.
- Artefatos e textos da change: **sempre pt-BR** (ver seção Idioma).

### Artifacts (typical for `spec-driven`)

| Artifact | Purpose |
|----------|---------|
| `proposal.md` | What & why (scope, non-goals) |
| `design.md` | How (approach, decisions, risks) |
| Delta specs under `specs/` | Requirements changes (ADDED / MODIFIED / REMOVED / RENAMED) |
| `tasks.md` | Implementation checklist |

Do not invent artifact layout. Use CLI paths from:

```bash
openspec status --change "<name>" --json
openspec instructions <artifact-id> --change "<name>" --json
```

### CLI conventions

- Prefer `openspec` over hand-editing scaffolding when the CLI creates structure.
- Use CLI output (`status`, `instructions`, `list`, `validate`) as the source of paths and progress — do not assume repo-local paths if the CLI returns resolved ones.
- If a **store** is named or relevant: `openspec store list --json`, then pass `--store <id>` on store-aware commands.
- Without a store, commands act on the nearest local `openspec/` root.

Useful commands:

```bash
openspec list --json
openspec list --specs
openspec status --change "<name>" --json
openspec instructions <artifact|apply> --change "<name>" --json
openspec validate [item-name]
openspec doctor
openspec context
```

### Implementation rules while applying a change

- Announce which change is in use.
- Read all `contextFiles` from `openspec instructions apply` before coding.
- Implement one task at a time; keep diffs minimal and scoped to the task.
- Mark tasks complete in `tasks.md` immediately: `- [ ]` → `- [x]`.
- Pause and ask when requirements are unclear, design is wrong, or a blocker appears.
- Prefer updating OpenSpec artifacts when implementation reveals design/scope issues — do not silently diverge from the plan.

### Spec editing rules

- Main specs live at `openspec/specs/<capability>/spec.md`.
- Delta specs express **intent**; merge intelligently (e.g. add a scenario without rewriting the whole requirement).
- Preserve content not mentioned in a delta.
- Requirement language: use clear SHALL / WHEN / THEN style already used by OpenSpec templates.
- Do not copy `<context>`, `<rules>`, or instruction metadata into artifact files.

### Explore mode

When exploring: read and reason freely; **do not implement product code**. Capturing decisions into OpenSpec artifacts is allowed if the user asks.

## Coding conventions (interim)

Until a stack is chosen and documented here:

- Prefer small, reviewable changes.
- Do not introduce frameworks, services, or infra without an OpenSpec change (or explicit user request).
- Do not invent package/module layout that contradicts existing dirs; extend only what exists.
- Prefer editing existing files over creating parallel structures.
- Avoid drive-by refactors unrelated to the active change or user request.
- Do not commit secrets, tokens, or local credentials.

### When code appears, document here

Update this section with:

- Language(s) and runtime versions
- Package manager and lockfile policy
- Build / test / lint commands
- Formatting rules (or “run formatter X”)
- Directory layout (e.g. `src/`, `apps/`, `packages/`)
- Commit / PR conventions if the team standardizes them

Also mirror durable tech-stack notes into `openspec/config.yaml` under `context:` so OpenSpec artifact generation stays aligned.

## Project context file

`openspec/config.yaml` may define:

- `context:` — tech stack, domain, style notes shown when creating artifacts
- `rules:` — per-artifact constraints (proposal, tasks, etc.)

Treat those as authoritative for artifact creation. Keep them short and actionable.

## What not to do

- Do not reply to the user in English (or any language other than pt-BR), unless they explicitly request another language for a specific turn.
- Do not write OpenSpec change artifacts (`proposal.md`, `design.md`, `tasks.md`, specs) in English by default — use pt-BR.
- Do not skip OpenSpec for non-trivial product work unless the user explicitly asks for a quick/unplanned change.
- Do not archive a change without checking incomplete tasks/artifacts and offering to sync delta specs.
- Do not auto-select a change when the user must choose among several.
- Do not dump long docs into `AGENTS.md`; keep this file instructional and link out when needed.

## Skills map

| Skill | When to use |
|-------|-------------|
| `openspec-explore` | Thinking / discovery, no implementation |
| `openspec-propose` | New change + full artifact set |
| `openspec-apply-change` | Implement tasks from a change |
| `openspec-sync-specs` | Merge delta specs into main specs |
| `openspec-archive-change` | Finalize and archive a completed change |
