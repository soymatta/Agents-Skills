---
description: >-
  Auto-session: guarda el historial de la sesión al alcanzar el límite del
  proveedor, inyecta los archivos de sesión previos del repo al abrir una sesión
  nueva, o limpia ("desatasca") un límite pegado. El plugin
  opencode-auto-session procesa este comando sin gastar turnos del modelo (los
  resultados se muestran como toasts en el TUI).
---

# /autosession - Historial y contexto de sesión

El plugin `opencode-auto-session` intercepta este comando y lo resuelve de forma
determinista (toasts en el TUI). Subcomandos:

- `/autosession status` - estado: proyecto, dump, archivos de sesión, aviso
- `/autosession dump` - guardar el historial en `.opencode_session_dump-<sesion>.md` ahora
- `/autosession files` - listar los archivos de sesión del repo
- `/autosession inject` - forzar la inyección del contexto en el próximo request
- `/autosession simulate [texto]` - recorrer el camino del límite sin gastar cuota
- `/autosession reset` - borrar los dumps del repo (desatasca un límite pegado)

Sin subcomando muestra el estado. Nada de esto se envía al modelo.
