---
name: openspec-sync-specs
description: >
  Sincroniza delta specs de uma change para as main specs (merge inteligente,
  sem arquivar). Use when the user wants to sync specs, merge deltas, update
  main specs, or runs /openspec-sync-specs, /opsx-sync, "sincroniza specs",
  "merge delta specs".
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  adaptedFor: grok
---

# OpenSpec Sync Specs (Grok)

Operação **dirigida pelo agente**: leia deltas e edite as main specs com merge
inteligente (ex.: adicionar um cenário sem reescrever o requisito inteiro).

**Idioma (bexa):** requisitos e cenários em **pt-BR**.

**Store:** `--store <id>` se aplicável.

---

## Input

Nome da change (opcional). Se ambíguo: `openspec list --json` + `ask_user_question`.
**Não auto-selecione** se houver mais de uma opção.

Mostre só changes que tenham delta specs (`specs/`).

---

## Passos

1. Selecionar a change.

2. Contexto:
   ```bash
   openspec status --change "<name>" --json
   ```

3. Deltas: use `artifactPaths.specs.existingOutputPaths`.

   Seções típicas:
   - `## ADDED Requirements`
   - `## MODIFIED Requirements`
   - `## REMOVED Requirements`
   - `## RENAMED Requirements` (FROM:/TO:)

   Sem deltas → informe e pare.

4. Para cada capability:
   - Leia o delta e a main em `openspec/specs/<capability>/spec.md`
   - **ADDED:** inclua; se já existir, trate como MODIFIED
   - **MODIFIED:** aplique só o que o delta descreve; preserve o resto
   - **REMOVED:** remova o bloco inteiro
   - **RENAMED:** renomeie FROM → TO
   - Se a capability não existir: crie `spec.md` com Purpose breve (TBD ok) + Requirements

5. Resumo: capabilities atualizadas e o que mudou.

---

## Princípio

O delta é **intenção**, não dump completo. Merge parcial e idempotente.

## Guardrails

- Leia delta e main antes de editar
- Preserve conteúdo não mencionado
- Em dúvida, pergunte
- Mostre o que está mudando
- A change permanece ativa (archive é outro passo)
