---
name: openspec-apply-change
description: >
  Implementa tasks de uma change OpenSpec (apply). Use when the user wants to
  implement, continue tasks, apply a change, or runs /openspec-apply-change,
  /opsx-apply, "implementa a change", "aplica tasks", "continuar implementação".
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  adaptedFor: grok
---

# OpenSpec Apply Change (Grok)

Implemente as tasks de uma change OpenSpec, uma de cada vez, com diffs mínimos.

**Idioma (bexa):** comunicação e updates em artefatos em **pt-BR**. Código pode
seguir a stack em inglês.

**Store:** se houver store, `--store <id>` nos comandos OpenSpec relevantes.

---

## Input

Nome da change (opcional). Se omitido: infira do contexto, auto-selecione se só
houver uma ativa; se ambíguo, `openspec list --json` + `ask_user_question`.

Sempre anuncie: `Usando change: <name>`.

---

## Passos

1. **Selecionar a change** (como acima).

2. **Status / schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Note `schemaName`, `planningHome`, `changeRoot`, `actionContext`.

3. **Instruções de apply**
   ```bash
   openspec instructions apply --change "<name>" --json
   ```
   Retorna `contextFiles`, progresso, lista de tasks, instrução dinâmica.

   - `state: "blocked"` → mostre o que falta; sugira completar artefatos / propose
   - `state: "all_done"` → parabéns; sugira `/openspec-archive-change`
   - senão → implemente

4. **Ler todos os `contextFiles`** antes de codar.

5. **Mostrar progresso:** schema, N/M tasks, restantes, instrução dinâmica.

6. **Loop de implementação**
   - Anuncie a task atual
   - Implemente o mínimo necessário
   - Marque `- [ ]` → `- [x]` em `tasks.md` **na hora**
   - Siga para a próxima

   **Pause se:** task ambígua, design errado, erro/bloqueio, ou usuário interromper.
   Prefira atualizar artefatos OpenSpec a divergir em silêncio.

7. **Ao terminar ou pausar:** progresso, o que ficou feito, próximo passo
   (archive se 100%).

---

## Outputs de referência

**Durante:**
```
## Implementing: <change> (schema: …)
Working on task 3/7: …
✓ Task complete
```

**Conclusão:**
```
## Implementation Complete
**Progress:** 7/7 ✓
Ready to archive → /openspec-archive-change
```

**Pausa:**
```
## Implementation Paused
**Progress:** 4/7
### Issue
…
**Options:** …
```

---

## Guardrails

- Leia `contextFiles` antes de começar
- Diffs pequenos e no escopo da task
- Não invente layout que contradiga o repo
- Em bexa: não habilitar REAL/auto-trade por padrão; não commitar `.env`
- Use paths da CLI; não assuma nomes de arquivos
- Workflow fluido: pode intercalar com updates de design/specs

## Domínio (bexa)

- OPTION: envio agora → entrada na **vela seguinte** → liquidação no fim dela
- Corte M1: a partir do segundo **55** não enviar (`entry_window`)
