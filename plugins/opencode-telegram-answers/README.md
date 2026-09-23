# OpenCode Telegram Answers

Plugin para **OpenCode** que envía una notificación a **Telegram** cuando la IA
termina de responder o necesita permiso para ejecutar una herramienta, y además
te deja **interactuar desde Telegram**:

- **Aprobar/rechazar permisos** con botones inline (Permitir una vez / Permitir siempre / Rechazar).
- **Responder a las notificaciones** de fin de tarea: lo que escribas reply se
  reinyecta en la sesión que generó esa notificación.
- **Indicador "Trabajando …"** mientras la IA responde: al empezar (evento
  `session.status` = busy) se envía `Trabajando ...` y se anima el ciclo
  `... → ..· → .·. → ·..`. Terminada la respuesta, ese mismo mensaje se
  **edita** con el resultado final (nada de enviar un segundo mensaje). La
  animación son ediciones HTTP (`editMessageText`), **no consume tokens de la IA**.

> Parte de **Agents-Skills**. Es una versión ampliada de `opencode-telegram-notifier`
> (mismo formato de notificaciones, más interacción). La skill `telegram-notify`
> del mismo repo sigue siendo la librería bajo demanda; este plugin es el *listener*
> automático. Es **opencode-only**.

```
Sesión: "Citaflex" - Agent: Build
Listo. /book ya no es demo. Todo verificado (`tsc` 0, `lint` 0 errores...)
```

Debajo de un mensaje de permiso verás:

```
⚠️ Permiso requerido

Sesión: "Citaflex"

Herramienta: <code>bash</code>
Patrón: <code>rm -rf *</code>

[ Permitir una vez ] [ Permitir siempre ] [ Rechazar ]
```

> El texto llega **convertido de markdown a HTML**, así las negritas, listas,
> código y enlaces se ven bien dentro de Telegram.

---

## Cómo funciona (resumen)

El proyecto es un **plugin de OpenCode** (`notification.ts`) instalado como
carpeta bajo `~/.config/opencode/plugins/`. Mientras OpenCode corre, el plugin:

| Evento | Comportamiento |
|--------|----------------|
| `session.status` (busy) | Envía **UN solo "Trabajando …" por turno** (single-flight: reserva en el state file, así ni TUI+server ni busy repetidos lo duplican) y anima el ciclo `... → ..· → .·. → ·..` cada 1500 ms (piso seguro ante el flood control de Telegram; ante 429 el intervalo se duplica solo hasta 6 s). Subagentes excluidos con `CONFIG.skipSubagent`. |
| `session.idle` | **Edita** el mensaje "Trabajando …" con el resultado final (título de sesión + agente + respuesta). Guardo el `message_id` para poder responderle. Si la sesión es un **subagente** (título termina en `(@… subagent)`), **no envía nada** (`CONFIG.skipSubagent`). Si el edit falla, el "Trabajando …" **se borra** y la final llega como mensaje nuevo. Un "Trabajando …" que llegue tarde (tras la final ya entregada) **se borra** en vez de duplicar la respuesta. |
| `permission.updated` / `permission.asked` / `permission.v2.asked` | Notifica **título de sesión + herramienta y patrón** y añade **3 botones** que aprueban o rechazan el permiso con las respuestas reales de OpenCode (`once` / `always` / `reject`). Al responder, el mensaje **se edita con el resultado** ("✅ Permiso concedido" / "🚫 Permiso rechazado") y los botones salen en la misma edición. |
| getUpdates (polling) | Recoge tus interacciones: pulsar un botón responde el permiso; responder a una notificación reinyecta el texto en esa sesión (sin mensaje de acuse). |

**Sin truncado**: nunca se corta la respuesta. Si el texto pasa del límite de
Telegram (4096), se parte en trozos HTML válidos y se envían encadenados
(`reply_to` al primero); el "Trabajando …" se edita a la primera parte y el
resto le sigue. `CONFIG.maxBodyChars` (4096, techo absoluto respetado al corte)
es el tamaño de cada trozo, no un tope del contenido: todo lo que quepa en
4096 llega en UN solo mensaje.

**Sin duplicados entre instancias**: OpenCode puede cargar el plugin dos veces
(TUI + server). El envío del final va bajo un **lock de archivo**
(`.telegram-answers.lock`) y el marker "final ya notificada" se persiste por
`message_id` (`state.lastFinal`): la segunda instancia ve el marker y no
reenvía. El lock también cubre la reutilización del "Trabajando …".

**Cola de Telegram**: si respondes a una notificación mientras la sesión está
ocupada, el mensaje **se encola** (persistido) y recibes un acuse; se reenvía
cuando OpenCode queda idle, uno por idle, sin cortar el turno en curso.

**Auto-test silencioso**: la verificación automática de permisos al arrancar
solo escribe en `opencode log`; jamás entra en tu canal de Telegram.

Los "Trabajando …" sin finalize (corte, reinicio, evento perdido) **no quedan
colgados**: caducan a los 30 min (`CONFIG.workingTtlMs`) y el plugin los borra.

La animación del "Trabajando …" es solo `editMessageText` por HTTP, **no
consume tokens de la IA**: el coste de tokens es únicamente el del turno del
modelo, que ocurre igual con o sin el indicador.

Nada de credenciales hardcodeadas: el token y el `chat_id` se leen de un **`.env`**
(ver [Instalación](#instalación)). El estado (offset del polling, botones vivos,
mapa de notificaciones, cola, markers de dedup) se guarda en
`~/.config/opencode/.telegram-answers.json`.

Detalle técnico completo en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

---

## Importante: usa UN solo plugin de este grupo

`opencode-telegram-answers` y `opencode-telegram-notifier` **no deben ejecutarse a
la vez**: duplicarían las notificaciones de fin de tarea y de permiso (cada una
pone su propio debounce independiente). Si tienes el notifier clásico instalado
como `~/.config/opencode/plugins/notification.ts`, bórralo cuando instales este.

---

## Estructura del proyecto

```
.
├── notification.ts        ← EL plugin (todo lo personalizable está en CONFIG)
├── install.ps1            ← Instala el plugin en la config global (archivo .ts plano)
├── package.json           ← typecheck / tests / install scripts
├── tsconfig.json
├── .env.example           ← plantilla de credenciales (copia a .env)
├── test/
│   └── smoke.mjs          ← tests de las funciones puras (npm test)
└── docs/
    └── ARQUITECTURA.md    ← cómo funciona por dentro
```

---

## Instalación

Requisitos: **Node.js >= 22.6** (solo para typecheck/tests), **OpenCode**, y un
**bot de Telegram** (creado con [@BotFather](https://t.me/BotFather)).

### 1. Dependencias de desarrollo (opcional pero recomendado)

```bash
npm install
```

### 2. Instalar en OpenCode

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
# o:  npm run install:global
```

OpenCode autoload los archivos `.ts` **planos** que viven en
`~/.config/opencode/plugins/` (no lee subcarpetas), así que el script copia
`notification.ts` como **`telegram-answers.ts`** ahí.
Si el plugin clásico `notification.ts` sigue instalado, bórralo (ver
[Importante](#importante-usa-un-solo-plugin-de-este-grupo)).

### 3. Credenciales de Telegram

El plugin lee `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (en orden de prioridad):

1. `.env` del directorio donde corriste OpenCode (solo ese proyecto).
2. `.env` en `~/.config/opencode/` (**recomendado**: aplica a todas tus sesiones).

```bash
# Para todas las sesiones:
cp .env.example ~/.config/opencode/.env
# …y rellena los valores reales (nunca los compartas).
```

Pasos para obtener las credenciales:

```text
1. Habla con @BotFather → /newbot → copia el token.
2. Añade el bot al chat/grupo donde quieres las notificaciones.
3. Envía cualquier mensaje al chat.
4. Consulta tu chat_id:
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   (los grupos/canales suelen ser negativos: -100...)
```

### 4. Reiniciar

**Cierra y vuelve a abrir OpenCode** para que cargue el plugin. En la próxima
tarea terminada te llegará la notificación a Telegram.

---

## Cómo usar las respuestas

1. Llega una notificación de **permiso** con sus botones.
   Pulsa **Permitir una vez / Permitir siempre / Rechazar**. OpenCode recibe la
   respuesta equivalente (`once` / `always` / `reject`). El mensaje se edita
   con el resultado ("✅ Permiso concedido" / "🚫 Permiso rechazado") y los
   botones se quitan en la misma edición (caducan tras `CONFIG.buttonTtlMs`).
2. Llega una notificación de **fin de tarea**. Escribe en Telegram un mensaje con
   **reply** a esa notificación. El texto se inyecta como si lo hubieras escrito
   en la sesión de OpenCode. Te acusamos el mensaje en el mismo hilo.

Nota: los botones de permiso solo funcionan mientras el permiso siga vigente en
OpenCode (normalmente unos segundos/minutos). Si caducó, el bot te avisa.

---

## Verificación rápida

```bash
npm install
npm run typecheck   # valida tipos del plugin
npm test            # smoke (puras) + integration (flujos con Bot API mockeado, sin red)
```

## Prueba en vivo

1. Abre OpenCode.
2. Pide una tarea corta (p. ej. "dime hola").
3. Al terminar recibes en Telegram: `Sesión: "…" - Agent: …` + respuesta formateada.
4. Pídele a la IA que ejecute un comando que requiera tu permiso → recibes el
   mensaje con los 3 botones.

---

## Personalización rápida

Todo lo visible se edita en un solo bloque `CONFIG` al inicio de `notification.ts`:

- Idioma de las etiquetas (`Sesión`, `Agent`, `Permiso requerido`…).
- Texto de los botones y de los acuses de respuesta.
- Emojis y separadores.
- Límite de caracteres.
- Caducidad de botones y del mapa de respuestas.
- Agente por defecto.

---

## Seguridad

- **Nunca** compartas tu `.env`: contiene el token del bot. Quien tenga el token
  controla los mensajes.
- El plugin **falla silencioso** (solo loguea) si faltan credenciales — nunca
  escribe `.env` por ti.
- El token y el chat_id solo se envían a `api.telegram.org`, vía HTTPS.
- **Solo reacciona a tu chat**: los replies se ignoran si `chat.id` no coincide
  con `TELEGRAM_CHAT_ID`, y los botones son por token aleatorio guardado en estado.
- El estado se guarda en tu propio `~/.config/opencode/.telegram-answers.json`
  (nunca se envía a terceros).

---

## Licencia

Privado / sin licencia definida. No redistribuir sin permiso.