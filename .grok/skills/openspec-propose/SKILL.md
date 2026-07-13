---
name: openspec-propose
description: >
  Propõe uma change OpenSpec completa (proposal, design, specs, tasks) em um
  passo. Use when the user wants to propose a change, start planning, create a
  proposal, or runs /openspec-propose, /opsx-propose, "propor change", "nova
  change", "cria proposal".
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  adaptedFor: grok
---

# OpenSpec Propose (Grok)

Crie a change e gere todos os artefatos necessários até ficar pronta para apply.

Artefatos típicos (schema `spec-driven`):
- `proposal.md` (o quê e por quê)
- `design.md` (como)
- delta specs sob `specs/`
- `tasks.md` (checklist de implementação)

Quando pronto para implementar: `/openspec-apply-change` ou pedir para implementar.

**Idioma (bexa):** todo o conteúdo dos artefatos em **pt-BR**. Nome da change em
kebab-case (pode ser inglês).

**Store:** se houver store nomeado, `openspec store list --json` e `--store <id>`
nos comandos de specs/changes.

---

## Input

Nome kebab-case **ou** descrição do que construir.

## Passos

1. **Sem input claro** — pergunte com `ask_user_question` (open-ended):
   > O que você quer construir ou corrigir?

   Derive o nome: “add user auth” → `add-user-auth`. **Não prossiga** sem entender o objetivo.

2. **Criar a change**
   ```bash
   openspec new change "<name>"
   ```

3. **Ordem dos artefatos**
   ```bash
   openspec status --change "<name>" --json
   ```
   Use: `applyRequires`, `artifacts`, `planningHome`, `changeRoot`, `artifactPaths`,
   `actionContext`. **Não assuma paths** — use o que a CLI retornar.

4. **Criar artefatos até apply-ready**

   Use `todo_write` para acompanhar.

   Para cada artefato `ready`:
   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```
   - `template` → estrutura do arquivo
   - `instruction` → orientação do schema
   - `resolvedOutputPath` → onde escrever
   - `context` / `rules` → **constraints para você**; **NÃO** copiar no arquivo
   - Leia dependências já prontas
   - Escreva o artefato; confirme que o arquivo existe
   - Re-rode `openspec status --change "<name>" --json`
   - Pare quando todos em `applyRequires` estiverem `done`

   Se faltar informação crítica → `ask_user_question`, depois continue.

5. **Status final**
   ```bash
   openspec status --change "<name>"
   ```

---

## Output

- Nome e localização da change
- Lista de artefatos criados (resumo)
- “Pronto para implementação”
- Sugestão: `/openspec-apply-change` ou “implementa a change”

---

## Guardrails

- Crie **todos** os artefatos exigidos por `apply.requires`
- Sempre leia dependências antes do próximo artefato
- Prefira decisões razoáveis a travar; pergunte só se for crítico
- Se o nome já existir, pergunte: continuar ou criar outro
- Nunca coloque blocos `<context>` / `<rules>` no conteúdo dos artefatos
