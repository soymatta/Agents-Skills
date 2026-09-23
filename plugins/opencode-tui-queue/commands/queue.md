---
description: >-
  Gestiona la cola de prompts del TUI: lista lo encolado, muestra el siguiente,
  envía un prompt al momento (/queue now <texto>), pausa o reanuda la cola, o la
  vacía. El plugin opencode-tui-queue procesa este comando sin gastar turnos del
  modelo (los resultados se muestran como toasts en el TUI).
---

# /queue - Cola de prompts del TUI

El plugin `opencode-tui-queue` intercepta este comando y lo resuelve de forma
determinista (toasts en el TUI). Subcomandos:

- `/queue list` - mensajes encolados de esta sesión
- `/queue front` - el siguiente que se enviará
- `/queue now <texto>` - enviar ya (o poner el primero de la cola si está ocupada)
- `/queue stop` - pausar la captura y el vaciado
- `/queue start` - reanudar
- `/queue flush [all]` - descartar lo encolado (esta sesión, o todas con `all`)

Sin subcomando muestra la ayuda. Nada de esto se envía al modelo.