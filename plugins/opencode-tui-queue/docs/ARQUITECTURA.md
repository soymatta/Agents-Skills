# ARQUITECTURA — opencode-tui-queue

## Flujo

```
  TUI: cualquier texto mientras busy (captura por defecto)
    │
    ▼
  chat.message (hook)               ← se dispara con TODA entrada de usuario
    │ 1. skip subagente + skip telegram-answers (via metadata)
    │ 2. busySessions.has(sessionID)? + alwaysOn + !stopped
    │    (comandos "/queue …" leading se resuelven como gestión, no se encolan)
    │ 3. extractTrailingQueue: si TERMINA en " /queue" se limpia el sufijo
    │
    ├─ captureAllBusy=false y sin sufijo → no hace nada (sigue al modelo)
    │
    └─ encola → enqueueText() en .opencode-queue.json
           output.parts = [placeholder {synthetic,ignored}]
           toast "Encolado (N pendientes)"
           (el modelo NO ve el mensaje: turno consumido)

 busy → idle (session.idle)
   │
   ▼
 drainPromote(sessionID)
   │ 1. stopped? → nada
   │ 2. promoteOne() (FIFO por sesión) → lo quita del archivo
   │ 3. client.session.prompt(parts:[{text}])  ← reentra como turno normal
   │ 4. ok → save; error → se devuelve AL FRENTE y se reintenta en el próximo idle
```

## Estado persistido

`~/.config/opencode/.opencode-queue.json`:

```json
{
  "alwaysOn": true,
  "stopped": false,
  "entries": [
    { "id": "m3n8...", "sessionID": "s-...", "text": "resume esto", "ts": 1726000000000 }
  ]
}
```

`loadQueueFrom` tolera corrupción y archivos ausentes (vuelve a estado limpio).
`saveQueueRaw` acepta una ruta custom para poder testear sin tocar el home.

## Puntos de fallo y decisiones

- **Turno consumido**: `chat.message` solo puede MUTAR `output.parts` (no devolver).
  El placeholder `{type:"text", synthetic:true, ignored:true}` evita que el
  modelo vea el mensaje y que el TUI lo muestre. Es el mismo patrón que usa la
  cola del plugin de Telegram; `extractInfo` (telegram) ya filtra `synthetic`.
- **Reencolado propio**: al promover, `promotingNow` marca la sesión durante el
  `session.prompt`; el `chat.message` del propio prompt se ignora. Además
  `recentDrainIds` recuerda el message id resultante como red de seguridad.
- **Interleaving con Telegram**: los prompts que reinyecta
  `opencode-telegram-answers` llevan `metadata: { via: "telegram-answers" }`;
  este plugin los ignora para no encolarlos dos veces.
- **Subagentes**: se cachea parentID por sesión; los hijos de un subagente no se
  tocan (nadie escribe en ellos desde el TUI, y sus prompts internos no son del
  usuario).
- **Una promoción por idle**: `promotingNow` impide dos `session.prompt`
  concurrentes; en cada idle siguiente sale el siguiente mensaje.
- **Persistencia**: si OpenCode se reinicia con cola pendiente, `loadQueue`
  la recupera intacta.

## Por qué no usar la cola nativa de OpenCode

La API tiene `delivery: "queue"` por sesión, pero el TUI no expone la opción de
encolar un prompt a mano y el límite configurable (`anomalyco/opencode#32157`)
no está enviado. Encollar aquí es determinista, visible (toast) y no depende de
comportamiento no cubierto por el contrato actual.