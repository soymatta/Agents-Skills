# Arquitectura

Este documento explica cómo funciona el plugin por dentro: qué eventos captura,
qué forma tienen los datos reales del SDK de OpenCode, cómo se construye cada
mensaje y cómo se implementan las respuestas (botones y replies).

Este plugin es una **versión ampliada** de `opencode-telegram-notifier`: el
mismo formato de notificaciones, más interacción por Telegram. Por eso **no debe
ejecutarse a la vez que el notifier clásico** (duplicarían mensajes).

## Piezas implicadas

| Componente | Rol |
|------------|-----|
| `notification.ts` | Plugin de OpenCode (TypeScript). Escucha eventos, envía a Telegram y recoge respuestas. |
| `@opencode-ai/plugin` | SDK de plugins: provee el hook `event` y el `client`. |
| `@opencode-ai/sdk` | Tipos de OpenCode (sesiones, mensajes, eventos). |
| `~/.config/opencode/.env` | Credenciales reales (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). |
| `~/.config/opencode/.telegram-answers.json` | Estado del plugin: offset de `getUpdates`, botones vivos y mapa `message_id → sesión`. |
| `~/.config/opencode/plugins/telegram-answers.ts` | El plugin instalado (OpenCode autoload los `.ts` planos de esa carpeta; no lee subcarpetas). Instalado por `install.ps1` o `setup.py`. |

## Ciclo de vida del plugin

```
OpenCode inicia
   │
   ├─ Carga plugins de ~/.config/opencode/plugins/
   │      └─ notification.ts se ejecuta:
   │           1. loadEnvFile() → lee .env (proyecto → ~/.config/opencode/)
   │           2. Si faltan credenciales → log y no hace nada (fallo silencioso)
   │           3. Carga el estado de .telegram-answers.json (limpiando lo caducado)
   │           4. startPolling() → arranca el long-poll de getUpdates
   │           5. Devuelve { event: async ({ event }) => {...} }
   │
    └─ Espera eventos…
          ├─ "session.status" (busy)         → envía/anima "Trabajando …" (se borra solo si caduca)
          ├─ "session.idle"                 → edita el "Trabajando …" a la final (o lo borra + envía nueva)
         ├─ "permission.updated"(v1)       → notificación + 3 botones
         └─ "permission.asked"/"permission.v2.asked" (v2) → notificación + 3 botones
```

## Flujo de la notificación de fin de tarea

1. Se recibe `session.idle` con `sessionID` en las propiedades.
2. Debounce local por `sessionID` (memoria, `shouldNotify`) para no duplicar.
3. Se consulta en paralelo `client.session.get()` (título) y
   `client.session.messages()` (historial).
4. Todo el envío siguiente ocurre bajo **`withStateLock()`**: un lock de archivo
   exclusivo (`.telegram-answers.lock`). OpenCode puede cargar el plugin en dos
   instancias (TUI + server); el lock serializa y el marker `state.lastFinal`
   evita que la segunda instancia reenvíe el MISMO final (clave = el
   `message_id` del último mensaje del asistente, que es único por turno).
5. Si es un **subagente** (`isSubagentSession`: la sesión tiene `parentID`, o el
   título termina en `(@… subagent)`) y `CONFIG.skipSubagent` está activo → no
   notifica.
6. `extractInfo()` recorre el historial **de atrás hacia adelante**:
   - Último mensaje `role === "assistant"`: une **todas** sus partes de texto y
     devuelve además `lastMessageID` (id del mensaje) y `lastMessageTime`.
   - Agente: último mensaje `role === "user"` anterior (campo `agent`), con
     `CONFIG.defaultAgent` de respaldo.
7. Se construye el encabezado `Sesión: "…" - Agent: …` y se convierte con
   `markdownToHtml()`. **Sin truncado**: `splitHtmlChunks()` parte el HTML en
   trozos ≤ `CONFIG.maxBodyChars` (4096, techo absoluto: el corte reserva los
   cierres de etiquetas) sin romper etiquetas.
8. Si hay un "Trabajando …" pendiente (`takeWorking()`), `editFinalToMessage()`
   lo **edita a la primera parte** y las siguientes se envían encadenadas
   (`reply_to` el ancla); si el edit falla, se **borra** y todo sale como mensaje
   nuevo. Sin pendiente → `sendMultipart()` (o `sendTelegram()` si cabe en uno).
9. Cada `message_id` enviado (ancla y continuaciones) se guarda en
   `state.notified`: `{ [message_id]: { sessionID, time } }`. Ese mapa permite
   que un **reply** a la notificación se inyecte en la sesión.
10. `markLastFinal()` persiste `state.lastFinal[sessionID] = { messageID, time }`
    y se llama `drainPendingPrompts()` para promover **un** mensaje de la cola de
    Telegram si la hay.

## Flujo del permiso y sus botones

1. Se recibe `permission.updated` (v1), `permission.asked` (v2) o
   `permission.v2.asked` (v2 moderna).
2. `permInfoFromEvent()` extrae `{ permID, sessionID, tool, pattern, variant }`:
   - v1: `tool = props.title`, `pattern = props.pattern`.
   - v2: `tool = props.permission ?? props.action`, `pattern = props.patterns ?? props.resources`.
   - `permID = props.id` (ej.: `v1` usa el id del permiso; `v2` usa el `requestID`).
3. Debounce por `permID` + lectura del título de sesión (con fallback).
4. Se envía el mensaje con un **inline keyboard** de 3 botones:
   `buildPermKeyboard(token)` → `callback_data = "perm|once|tok3n"` (¡< 64 bytes!).
5. El token (`makeToken()`) es la única referencia que se guarda en
   `state.buttons`: `{ [token]: { sessionID, permID, variant, time } }`, con TTL
   `CONFIG.buttonTtlMs`.

## Flujo de las respuestas (getUpdates)

`startPolling()` lanza `pollTelegram()` al arrancar y repite cada
`CONFIG.pollIntervalMs`:

```
getUpdates?timeout=25&offset=<state.offset + 1>   (long-poll)
   │
   ├─ callback_query (botón pulsado)
   │     parseCallbackData("perm|once|tok3n") → { reply, token }
   │     state.buttons[token] vigente?
   │       ├─ sí → replyPermission() + answerCallbackQuery + EDITAR el cuerpo
   │       │         con el resultado (`permOutcomeText()`: "✅ Permiso concedido" /
   │       │         "🚫 Permiso rechazado") + quitar botones en la misma edición +
   │       │         borrar token
   │       └─ no → answerCallbackQuery("Error en el permiso: no vigente o ya respondido")
   │               + editar el cuerpo con ese estado si el permiso ya se consumió
   │
   └─ permission.replied (resuelto en CUALQUIER vía: botón, TUI, auto)
          → `settlePermOutcome()`: fija el resultado una sola vez y lo refleja
            en TODOS los mensajes vivos del permID (gemelos de varias
            instancias). Si ya estaba fijado, solo limpia botones sin re-editar
            (un "concedido" nunca se pisa con "expirado").
   │
    └─ message con reply_to_message
          state.notified[message_id] vigente?
            ├─ ¿sesión OCCUPADA (busySessions tiene sessionID)?
            │   ├─ sí → enqueue en state.pendingPrompts (status queued; TTL 24 h,
            │   │        máx CONFIG.queueMaxEntries=25) + acuse `queueBusyAckLabel`.
            │   │        Se reenvía en el próximo idle, UNO por idle, sin cortar
            │   │        el turno (drainPendingPrompts → client.session.prompt con
            │   │        metadata { via: "telegram-answers" }).
            │   └─ no → client.session.prompt({ parts:[{type:"text", text}] }) y se
            │          borra la entrada (sin acuse en Telegram; solo se avisa si falla).
            └─ no → ignorar (mensaje normal)
```

### replyPermission()

Orden de intentos (el runtime actual responde por la ruta v2):

| # | Ruta | Cómo |
|---|------|------|
| 1 | v1 | `client.postSessionIdPermissionsPermissionId({ path: { id: sessionID, permissionID }, body: { response } })` |
| 2 | v2 | `POST /api/session/{sessionID}/permission/{requestID}/reply` invocado con el **HTTP client interno del SDK** (`client._client.post(...)` — propiedad `_client` en SDK 1.18.x; se prueban `_client` → `client` → `api`) — la ruta que responde la opencode 1.18.x |
| 3 | self-heal | Si la v2 dice 404/`PermissionNotFoundError`: `findPendingPermission()` lista `GET /api/session/{sessionID}/permission` y luego `GET /permission`, localiza el permiso por su id y **reintenta con su sesión dueña real**. Si ya no está en pendientes → error "respondido en otro lado o caducado" |
| 3 | `permission2.reply` | cast best-effort; no existe en 1.18.x |

Si todos fallan lanza un error con el detalle de cada intento (HTTP status +
mensaje), que se loguea en OpenCode (`app.log`) y por `console.warn`.

Las respuestas válidas coinciden con las opciones reales de OpenCode:
`"once" | "always" | "reject"`. Los botones mapean 1:1 (Permitir una vez →
`once`, Permitir siempre → `always`, Rechazar → `reject`).

## Auto-test E2E (`runSelfTest()`)

Al arrancar, una vez por `CONFIG.selfTestVersion` (se reintenta en cada arranque
mientras falle): busca el directorio real del workspace (`session.list`, se
excluye el home), crea una sesión desechable **con ese directorio**
(`query.directory`) y le pide que escriba en una carpeta **hermana** del
workspace (`parent(_ws)\.telegram-selftest\probe.txt`): al estar fuera del
árbol de la sesión, el server pide permiso REAL. `permInfoFromEvent` detecta el
evento en esa sesión: el handler NO notifica a Telegram y responde con el mismo
`replyPermission()` de los botones (`reject`). Tras el prompt (o el
`selfTestTimeoutMs`) borra la sesión. Resultados:

- `✅ OK: reject por v2 en N ms` → se persiste `selfTestVersion`, no se repite.
- `⚠️ FALLÓ: motivo` → no se persiste, se reintenta cada arranque.
- `N/A: …` (sin evento de permiso: write auto-permitido o no intentado) → se
  persiste igual y NO se notifica a Telegram (no es un fallo del flujo).

La sesión del auto-test se registra en `state.selfTestSessions` desde antes del
prompt hasta que se borra: así sus eventos idle/status no envían ni "Trabajando"
ni notificación aunque el `activeSelfTest` en memoria ya haya caducado. Si un
envío de permiso tarda > 10 s se loguea `perm notify lento` (detector de flood).

El auto-test es **100% silencioso**: los resultados solo van a `opencode log`
(`report()`), jamás a Telegram.

## Estado persistido

`~/.config/opencode/.telegram-answers.json`:

```json
{
  "offset": 1234,
  "buttons": { "tok3n": { "sessionID": "s1", "permID": "p1", "variant": "v1", "time": 1720000000000 } },
  "notified": { "42": { "sessionID": "s1", "time": 1720000000000 } },
  "working": { "s1": { "messageId": 43, "time": 1720000000000 } },
  "lastFinal": { "s1": "msg_xyz" },
  "pendingPrompts": { "s1": [ { "id": "p1", "text": "...", "status": "queued", "time": 1720000000000 } ] },
  "selfTestSessions": ["s9"]
}
```

Se escribe solo cuando cambia algo; se limpia al cargar (entradas caducadas por
TTL: `lastFinal` por `dedupTtlMs`, cola por `queueTtlMs`, el resto por sus
TLTs propios). El lock de archivo vive aparte (`.telegram-answers.lock`) y se
borra solo (stale a `LOCK_STALE_MS = 15000`). El archivo de estado **es solo
de este plugin** (el notifier clásico usa `.notification-state.json`), así no
se pisan entre sí.

## Robustez al flood control y a la notificación final perdida

Telegram limita ~1 mensaje/seg del bot y la animación edita varias veces por
turno: la notificación final podía perderse (429 al agotar reintentos) o el
"Trabajando …" llegar *después* de la final (sendMessage en retry) y quedar
animando huérfano. Garantías actuales:

- base `workingEditMs = 1500`, techo `6000` con backoff adaptativo.
- `pendingWorkingSends`: si la final llega con el "Trabajando" aún en vuelo, el
  idle lo espera (tope 8 s) y lo EDITA en vez de duplicar.
- `recentFinals` + `isFinalAlreadyDelivered()`: si el "Trabajando" se
  materializa en Telegram DESPUÉS de que la final ya se entregó por otra vía,
  se BORRA en vez de editarlo a la final (editarlo duplicaba la respuesta).
  Solo si aún no hay final entregada se edita como última bala. La edición
  solo aplica si la final se generó DESPUÉS del turno busy en curso
  (`busySince` + `shouldEditLateWorking`): una final del turno anterior
  reenviaría el mensaje previo en bucle en cada `session.status busy` hasta que
  la tarea actual termina.
- Single-flight del "Trabajando" (`claimWorkingSlot()` + `pendingWorkingSends`):
  busy repetidos o dos instancias (TUI+server) no envían otro indicador: la
  primera reserva el slot en el state file (`messageId: 0`) y las demás lo
  reutilizan (`revive`) o lo omiten (`skip`). Un edit de revive bajo 429
  (`limited`) conserva el mensaje y lo anima con backoff en vez de
  borrar+recrear (eso duplicaba bajo flood).
- Si `sendMessage` de la final devuelve null (429 agotado), se intenta editar el
  "Trabajando" vivo con el texto final como última bala antes de rendirse.

## Formato de datos real del SDK (importante)

`session.messages()` NO devuelve `Message[]` sino:

```ts
Array<{ info: Message; parts: Part[] }>
```

Por eso se lee `entry.info.role` y los textos de
`parts.filter(p => p.type === "text" && !p.synthetic)`.

## Seguridad del canal

- El chat se restringe: los replies se ignoran si `chat.id` no coincide con
  `TELEGRAM_CHAT_ID`.
- Los botones solo responden si el token existe en `state.buttons` y no caducó.
- Todo viaja por HTTPS a `api.telegram.org`.

## Conversión markdown → Telegram

`markdownToHtml()` primero **escapa HTML** (`&`, `<`, `>`). Bloques de código →
`<pre>`, encabezados → `<b>`, citas `>` → `<i>▸ …</i>`, `---` → separador, listas
`-`/`*` → `• `, e inline: `` `x` `` → `<code>`, `**x**` → `<b>`, `*x*` → `<i>`,
`~~x~~` → `<s>`, `[t](url)` → `<a href>`. Se colapsan saltos de línea triples.
`sendMultipart()` / `splitHtmlChunks()`: el texto jamás se trunca. Se parte el
HTML en trozos ≤ `CONFIG.maxBodyChars` (4096) cerrando y reabriendo etiquetas
por trozo (`<b>…</b>` cerrado al final del trozo y reabierto al inicio del
siguiente); el primero edita el "Trabajando …", los siguientes van `reply_to`
el ancla. La última bala sin truncado: si aun así Telegram rechaza, se reenvía
como mensaje nuevo.