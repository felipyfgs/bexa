---
name: openspec-archive-change
description: >
  Arquiva uma change OpenSpec concluída (após implementação). Use when the user
  wants to archive, finalize, close a change, or runs /openspec-archive-change,
  /opsx-archive, "arquivar change", "finalizar change".
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  adaptedFor: grok
---

# OpenSpec Archive Change (Grok)

Finalize e mova a change para o archive.

**Idioma (bexa):** comunicação em **pt-BR**.

**Store:** `--store <id>` se aplicável.

---

## Input

Nome da change (opcional). Se ambíguo: `openspec list --json` + `ask_user_question`
somente em changes **ativas** (não arquivadas). **Não auto-selecione.**

---

## Passos

1. Selecionar a change.

2. Status de artefatos:
   ```bash
   openspec status --change "<name>" --json
   ```
   Se algum artefato não estiver `done`: avise e confirme com `ask_user_question`
   se deve prosseguir.

3. Tasks: leia `tasks.md` e conte `- [ ]` vs `- [x]`.
   Se incompletas: avise, confirme, e só então continue (se o usuário quiser).

4. Sync de delta specs (se existirem em `artifactPaths.specs.existingOutputPaths`):
   - Compare com `openspec/specs/<capability>/spec.md`
   - Mostre resumo do que seria aplicado
   - Opções via `ask_user_question`:
     - Se há mudanças: “Sincronizar agora (recomendado)” / “Arquivar sem sync”
     - Se já sync: “Arquivar agora” / “Sync de novo” / “Cancelar”
   - Se sync: siga a skill `openspec-sync-specs` (mesmo fluxo de merge inteligente)
     para a change; depois arquive de qualquer forma se o usuário pediu archive

5. Arquivar:
   ```bash
   mkdir -p "<planningHome.changesDir>/archive"
   ```
   Nome: `YYYY-MM-DD-<change-name>` (data de hoje).
   Se o destino já existir → falhe e sugira renomear.
   ```bash
   mv "<changeRoot>" "<planningHome.changesDir>/archive/YYYY-MM-DD-<name>"
   ```
   (Preserve `.openspec.yaml` — vai junto com o diretório.)

6. Resumo final.

---

## Output de sucesso

```
## Archive Complete

**Change:** <name>
**Schema:** <schema>
**Archived to:** …/archive/YYYY-MM-DD-<name>/
**Specs:** sincronizadas | sem delta | sync pulado
```

## Guardrails

- Sempre peça seleção se o nome não estiver claro
- Use o grafo de status da CLI
- Warnings não bloqueiam sozinhos — informe e confirme
- Não apague history à toa; archive = mover
