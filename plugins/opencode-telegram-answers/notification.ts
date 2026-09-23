import type { Plugin } from "@opencode-ai/plugin"
import type { Message, Part } from "@opencode-ai/sdk"
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const TELEGRAM_API = "https://api.telegram.org/bot"
const STATE_FILE = join(homedir(), ".config", "opencode", ".telegram-answers.json")

/**
 * ── CONFIGURACIÓN EDITABLE ─────────────────────────────────────────────
 * Todo lo que una persona deba personalizar vive aquí: etiquetas, idioma,
 * emojis, separadores y límites. No hace falta tocar la lógica del plugin.
 * ───────────────────────────────────────────────────────────────────────
 */
const CONFIG = {
  /** Encabezado de la notificación de fin de tarea */
  sessionLabel: "Sesión",
  agentLabel: "Agent",
  titleSeparator: " - ",
  /** Título mostrado cuando la sesión aún no tiene uno asignado */
  emptySessionTitle: "Sin título",
  /** Agente por defecto si no se detecta ninguno en el historial */
  defaultAgent: "build",
  /** No notificar cuando la sesión que quedó idle es un subagente (parentID o título `(@x subagent)`) */
  skipSubagent: true,

  /** Notificación de permiso requerido */
  permissionPrefix: "\u26a0\ufe0f ",
  permissionTitle: "Permiso requerido",
  permissionToolLabel: "Herramienta",
  permissionPatternLabel: "Patrón",

  /** Botones del permiso (mapeo a las respuestas reales de OpenCode) */
  permOnceLabel: "Permitir una vez",
  permAlwaysLabel: "Permitir siempre",
  permRejectLabel: "Rechazar",

  /** Respuestas de acuse por Telegram: el título muestra el ESTADO del permiso */
  replySuccessLabel: "Permiso concedido",
  replyRejectedLabel: "Permiso rechazado",
  replyFailureLabel: "Error en el permiso: no se pudo responder",
  replyExpiredLabel: "Error en el permiso: no vigente o ya respondido",
  replyPromptErrorLabel: "No pude reenviar el mensaje a OpenCode",
  /** Prefijos del acuse PERSISTENTE: al responder un permiso se EDITA el
   *  cuerpo del mensaje con el resultado (el toast solo es efímero y el
   *  "Permiso requerido" quedaba colgado para siempre). */
  permGrantedPrefix: "\u2705 ",
  permRejectedPrefix: "\ud83d\udeab ",

  /** Responder en Telegram mientras la sesión está ocupada: se ENCOLA y se
   *  reenvía cuando OpenCode quede idle. Máximo de entradas por cola */
  queueBusyAckLabel: "\u26a0\ufe0f Ocupado: tu mensaje se reenviar\u00e1 a OpenCode en cuanto quede libre esta sesi\u00f3n.",
  queueMaxEntries: 25,
  /** Entradas de cola caducadas: se descartan (ms) */
  queueTtlMs: 24 * 60 * 60 * 1000,
  /** Extensión del marcador de final ya enviada: si otra instancia ya notificó
   *  el MISMO message id del asistente, esta instancia no reenvía (ms) */
  dedupTtlMs: 24 * 60 * 60 * 1000,

  /** No enviar la respuesta si es menor a este tiempo entre eventos iguales (ms) */
  debounceMs: 3000,
  /** Tamaño de cada trozo del mensaje final. NO truncamos: el límite duro de
   *  Telegram es 4096 por mensaje y splitHtmlChunks lo respeta al corte
   *  (reserva los cierres de etiquetas). Si el texto pasa de 4096, se parte
   *  completo y se manda como varios mensajes encadenados. */
  maxBodyChars: 4096,

  /** Prefijo del callback_data de los botones (perm|respuesta|token) */
  permPrefix: "perm",
  /** Intervalo entre pollings de getUpdates (ms) */
  pollIntervalMs: 2000,
  /** Timeout de long-polling de Telegram (s) */
  updateTimeoutSec: 25,
  /** Caducidad de los botones de permiso (ms) */
  buttonTtlMs: 36 * 60 * 60 * 1000,
  /** Caducidad del mapeo "mensaje notificado → sesión" para respuestas (ms) */
  notifiedTtlMs: 24 * 60 * 60 * 1000,

  /** Mensaje "Trabajando" mientras la IA responde (se edita a la respuesta final) */
  workingEnabled: true,
  workingLabel: "Trabajando",
  /** Frames del indicador animado: el ciclo de puntos no consume tokens, son edits HTTP */
  workingFrames: ["...", "..\u00b7", ".\u00b7.", "\u00b7.."],
  /** Intervalo base entre frames (ms). 700 ms saturaba el flood control de
   * Telegram y retrasaba las notificaciones de permiso 30+ s: 1500 ms es el
   * piso seguro (1200 aún provocaba drops de la notificación final). Ante 429
   * el intervalo se duplica solo hasta workingMaxEditMs. */
  workingEditMs: 1500,
  /** Techo del backoff de la animación ante 429 (ms) */
  workingMaxEditMs: 6000,
  /** Los "Trabajando …" sin finalize se borran al caducar (ms) */
  workingTtlMs: 30 * 60 * 1000,
  /** Reserva de envío del "Trabajando" entre instancias (ms): la primera que
   *  procesa un busy marca el slot (messageId 0) y las demás lo ven y NO
   *  envían otro. Sin esto, TUI+server o busy repetidos duplicaban el
   *  indicador en vez de animar uno solo. */
  workingClaimTtlMs: 120000,

  /** Auto-test E2E al arrancar (una vez por versión). Provoca un permiso
   * REAL en una sesión desechable (título selfTestSessionTitle) y lo responde
   * con el mismo replyPermission() de los botones. Sin notificaciones
   * visibles de esa sesión; NUNCA escribe en Telegram: solo client.app.log
   * (el canal del usuario no debe tener ruido de pruebas). En FALLO NO marca
   * versión: se reintenta en cada arranque. */
  selfTest: true,
  selfTestVersion: 6,
  selfTestSessionTitle: "telegram-answers self-test (auto)",
  selfTestTimeoutMs: 120000,
  selfTestPrompt:
    "NO ejecutes bash, read, glob ni grep. \u00danicamente crea el archivo " +
    'C:\\Users\\yasse\\Desktop\\.telegram-selftest\\probe.txt con el contenido "self-test". ' +
    "Si te piden permiso para escribir fuera del workspace, detente en ese punto y no hagas nada m\u00e1s. " +
    "No modifiques ni borres ning\u00fan otro archivo.",
}

// ── Estado persistido entre reinicios de OpenCode ─────────────────────
interface StoredButton {
  sessionID: string
  permID: string
  variant: "v1" | "v2"
  time: number
  /** Mensaje de Telegram que lleva los botones (ancla): para conciliar
   *  gemelos al resolverse el permiso. Ausente en registros pre-upgrade. */
  messageId?: number | null
  /** Cuerpo PLANO del mensaje de permiso (misma info que el HTML enviado):
   *  base del acuse persistente en gemelos (sin su texto no se puede editar). */
  body?: string
}
/** Resultado fijado de un permiso (evita re-editar con "expirado" un mensaje
 *  que ya muestra concedido/rechazado: doble tap o carrera callback/replied). */
interface StoredOutcome {
  kind: PermOutcome
  time: number
}
interface StoredNotified {
  sessionID: string
  time: number
}
interface StoredWorking {
  messageId: number
  time: number
}
/** Marcador de "final ya notificada" por sesión (dedup entre instancias) */
interface StoredLastFinal {
  messageID: string
  time: number
}
/** Entrada de la cola de Telegram (reply mientras la sesión estaba ocupada) */
interface PendingPrompt {
  id: string
  sessionID: string
  text: string
  ts: number
  status: "queued" | "promoting"
}
interface AnswerState {
  offset: number
  buttons: Record<string, StoredButton>
  notified: Record<string, StoredNotified>
  /** "Trabajando …" pendientes de finalizar (sobreviven a reinicios) */
  working: Record<string, StoredWorking>
  /** Última versión de código auto-verificada (ver runSelfTest) */
  selfTestVersion?: number
  /** Sesiones del auto-test en curso (una vez borradas se quitan de aquí) */
  selfTestSessions?: string[]
  /** Final ya notificada por sesión: evita duplicados entre instancias */
  lastFinal?: Record<string, StoredLastFinal>
  /** Replies de Telegram encolados por sesión ocupada */
  pendingPrompts?: PendingPrompt[]
  /** Resultado ya fijado por permID (conciliación entre botón y evento) */
  permOutcome?: Record<string, StoredOutcome>
}

function loadState(): AnswerState {
  try {
    if (existsSync(STATE_FILE)) {
      const raw = JSON.parse(readFileSync(STATE_FILE, "utf-8")) as Partial<AnswerState>
      const now = Date.now()
      const cleanup = <T extends { time: number }>(map: Record<string, T> | undefined, ttl: number): Record<string, T> => {
        const out: Record<string, T> = {}
        for (const [k, v] of Object.entries(map ?? {})) {
          if (v && now - v.time < ttl) out[k] = v
        }
        return out
      }
      return {
        offset: typeof raw.offset === "number" && raw.offset >= 0 ? raw.offset : 0,
        buttons: cleanup(raw.buttons, CONFIG.buttonTtlMs),
        notified: cleanup(raw.notified, CONFIG.notifiedTtlMs),
        working: (() => {
          const w = cleanup(raw.working, CONFIG.workingTtlMs)
          // Reservas de envío (messageId 0) de un proceso muerto: no bloquear
          for (const [k, v] of Object.entries(w)) {
            if (v.messageId === 0 && now - v.time >= CONFIG.workingClaimTtlMs) delete w[k]
          }
          return w
        })(),
        selfTestSessions: Array.isArray(raw.selfTestSessions) ? raw.selfTestSessions : [],
        lastFinal: cleanup(raw.lastFinal, CONFIG.dedupTtlMs),
        pendingPrompts: (raw.pendingPrompts ?? [])
          .filter((p) => p && typeof p.id === "string" && typeof p.sessionID === "string" && now - p.ts < CONFIG.queueTtlMs)
          .map((p) => (p.status === "promoting" ? { ...p, status: "queued" as const } : p)),
        permOutcome: cleanup(raw.permOutcome, CONFIG.buttonTtlMs),
      }
    }
  } catch {
    // archivo de estado corrupto → empezar de cero
  }
  return { offset: 0, buttons: {}, notified: {}, working: {}, selfTestSessions: [], lastFinal: {}, pendingPrompts: [], permOutcome: {} }
}

let state: AnswerState = loadState()

function saveState(): void {
  try {
    mkdirSync(join(homedir(), ".config", "opencode"), { recursive: true })
    writeFileSync(STATE_FILE, JSON.stringify(state))
  } catch {
    // ignore state write errors
  }
}

// ── Exclusión mutua entre instancias del plugin ────────────────────────
// OpenCode carga el plugin más de una vez (dos instancias en el mismo
// proceso, o TUI + server): el lock de archivo serializa el envío del final
// para que solo una instancia notifique aunque compartan el state file.

const LOCK_FILE = join(homedir(), ".config", "opencode", ".telegram-answers.lock")
/** Un lock que lleva más de esto colgado se considera de un proceso muerto */
const LOCK_STALE_MS = 15000

/**
 * Ejecuta `fn` bajo un lock de archivo exclusivo. Devuelve el resultado y,
 * al acabar, suelta el lock. Si tras `timeoutMs` no se obtiene (otra
 * instancia activa), ejecuta igual con `locked=false`: el marcador de final
 * re-leído desde el archivo sigue protegiendo contra duplicados.
 */
async function withStateLock<T>(fn: (locked: boolean) => Promise<T>, timeoutMs = 2000): Promise<T> {
  let fd: number | null = null
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline && fd === null) {
    try {
      fd = openSync(LOCK_FILE, "wx")
    } catch {
      // Existe: si es un lock muerto (crash), reclamarlo y seguir
      try {
        const st = statSync(LOCK_FILE)
        if (Date.now() - st.mtimeMs > LOCK_STALE_MS) {
          try {
            unlinkSync(LOCK_FILE)
          } catch {
            // otra instancia lo ganó en la carrera: reintentar el open
          }
        }
      } catch {
        // desapareció entre el open y el stat: reintentar el open
      }
      await new Promise((r) => setTimeout(r, 50))
    }
  }
  if (fd === null) {
    try {
      fd = openSync(LOCK_FILE, "wx")
    } catch {
      fd = null
    }
  }
  if (fd !== null) {
    try {
      return await fn(true)
    } finally {
      try {
        closeSync(fd)
      } catch {
        // ya cerrado
      }
      try {
        unlinkSync(LOCK_FILE)
      } catch {
        // otra instancia ya lo limpió
      }
    }
  }
  return fn(false)
}

/** Relee el estado fresco desde el archivo y lo adopta como base de trabajo.
 *  Mitiga que dos instancias del plugin operen sobre un `state` desfasado. */
function adoptState(): AnswerState {
  state = loadState()
  return state
}

// ── Debounce en memoria (sin archivo cruzado: este plugin es el único) ─
const recentNotifications = new Map<string, number>()

function shouldNotify(key: string): boolean {
  const now = Date.now()
  const last = recentNotifications.get(key)
  if (last && now - last < CONFIG.debounceMs) return false
  recentNotifications.set(key, now)
  for (const [k, t] of recentNotifications) {
    if (now - t > CONFIG.debounceMs * 2) recentNotifications.delete(k)
  }
  return true
}

/**
 * Carga TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID desde un `.env`.
 * Orden de búsqueda: directorio del proyecto, `.opencode/.env` del proyecto,
 * y el `.env` global de OpenCode.
 */
function loadEnvFile(dir: string): void {
  const candidates = [
    join(dir, ".env"),
    join(dir, ".opencode", ".env"),
    join(homedir(), ".config", "opencode", ".env"),
  ]
  for (const path of candidates) {
    if (!existsSync(path)) continue
    const content = readFileSync(path, "utf-8")
    for (const line of content.split(/\r?\n/)) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith("#")) continue
      const eq = trimmed.indexOf("=")
      if (eq === -1) continue
      const key = trimmed.slice(0, eq).trim()
      let value = trimmed.slice(eq + 1).trim()
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1)
      }
      // No sobrescribir variables ya definidas en el entorno
      if (!process.env[key]) process.env[key] = value
    }
  }
}

// ── Telegram: envío y acuse ────────────────────────────────────────────

/**
 * Parte HTML en trozos de ≤`max` caracteres SIN truncar: el texto completo se
 * conserva y se reparte en mensajes encadenados (Telegram limita a 4096 por
 * mensaje). Nunca corta una etiqueta a medias; las etiquetas abiertas en un
 * trozo se cierran al final y se reabren al inicio del siguiente. El `max`
 * es TECHO ABSOLUTO: al cortar se reserva el largo de los cierres, así que
 * ningún trozo emitido supera `max` (con max=4096 todo lo que quepa llega en
 * UN solo mensaje).
 */
function splitHtmlChunks(text: string, max = CONFIG.maxBodyChars): string[] {
  if (text.length <= max) return [text]
  const chunks: string[] = []
  const stack: Array<{ open: string; close: string }> = []
  const closers = (): string => stack.slice().reverse().map((t) => t.close).join("")
  const reopeners = (): string => stack.map((t) => t.open).join("")
  const tagNameOf = (tag: string): string => {
    const m = /^<\/?([a-zA-Z][a-zA-Z0-9]*)/.exec(tag)
    return m ? m[1].toLowerCase() : ""
  }
  const pushChunk = (content: string): void => {
    if (content.length > 0) chunks.push(content + closers())
  }
  let buf = ""
  let i = 0
  const n = text.length
  while (i < n) {
    const ch = text[i]
    if (ch === "<") {
      const end = text.indexOf(">", i)
      const isAtom = end !== -1
      const tag = isAtom ? text.slice(i, end + 1) : text.slice(i)
      const closing = /^<\//.test(tag)
      const name = tagNameOf(tag)
      // Si la etiqueta no cabe en el trozo actual (reservando los cierres),
      // cerrar y empezar uno nuevo
      if (buf.length + tag.length + closers().length > max && buf.length > 0) {
        pushChunk(buf)
        buf = reopeners()
      }
      if (closing) {
        const last = stack[stack.length - 1]
        if (last && tagNameOf(last.open) === name && name) stack.pop()
      } else if (name && /^[a-zA-Z][a-zA-Z0-9]*$/.test(name)) {
        // Evitar contabilizar etiquetas auto-contenidas (`<br>` y similares)
        if (!["br", "hr", "img", "meta"].includes(name)) {
          stack.push({ open: tag, close: `</${name}>` })
        }
      }
      buf += tag
      i = isAtom ? end + 1 : n
      continue
    }
    buf += ch
    i++
    // Hueco real del trozo: los cierres de etiquetas abiertas viajan con él,
    // así que el corte deja sitio para ellos (techo absoluto `max`).
    const room = Math.max(1, max - closers().length)
    if (buf.length + closers().length >= max) {
      // Cortar en el último espacio razonable DENTRO del hueco (si lo hay)
      // para no partir palabras; si no cabe ni eso, corte duro en el hueco.
      let cut = -1
      const from = Math.min(buf.length - 1, room)
      for (let s = from; s > Math.max(0, from - 300); s--) {
        if (buf[s] === " " || buf[s] === "\n") {
          cut = s + 1
          break
        }
      }
      if (cut <= 0) cut = Math.max(1, Math.min(room, buf.length - 1))
      const head = buf.slice(0, cut)
      const tail = buf.slice(cut)
      pushChunk(head)
      buf = reopeners() + tail
    }
  }
  if (buf.length > 0) pushChunk(buf)
  return chunks.length > 0 ? chunks : [text]
}

async function sendTelegram(
  token: string,
  chatId: string,
  text: string,
  opts?: { replyMarkup?: unknown; replyTo?: number; tag?: string },
): Promise<number | null> {
  const msg = text
  const tag = opts?.tag ?? "send"
  // Telegram rechaza con 400 el texto vacío: no gastar un request
  if (!msg.trim()) {
    console.warn(`[telegram-answers] Telegram API skip empty text (${tag})`)
    return null
  }

  const body: Record<string, unknown> = {
    chat_id: chatId,
    text: msg,
    parse_mode: "HTML",
    disable_web_page_preview: true,
  }
  if (opts?.replyMarkup) body.reply_markup = opts.replyMarkup
  if (typeof opts?.replyTo === "number") body.reply_to_message_id = opts.replyTo

  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const res = await fetch(`${TELEGRAM_API}${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const payload = (await res.json().catch(() => null)) as { result?: { message_id?: number } } | null
        return typeof payload?.result?.message_id === "number" ? payload.result.message_id : null
      }
      if (res.status === 429) {
        const retryAfter = (await res.json().catch(() => ({}))) as { parameters?: { retry_after?: number } }
        const wait = (retryAfter.parameters?.retry_after ?? 5) * 1000
        await new Promise((r) => setTimeout(r, wait))
        continue
      }
      const errBody = (await res.json().catch(() => null)) as { description?: string } | null
      const description = typeof errBody?.description === "string" ? errBody.description : "?"
      // 400 por reply_to inválido (mensaje borrado): reintentar sin el reply
      if (res.status === 400 && typeof body.reply_to_message_id === "number" && /reply|not found/i.test(description)) {
        delete body.reply_to_message_id
        continue
      }
      console.warn(
        `[telegram-answers] Telegram API error ${res.status} (${tag}): ${description} | len=${msg.length} head=${JSON.stringify(msg.slice(0, 120))}`,
      )
      return null
    } catch (err) {
      if (attempt === 2) {
        console.warn(`[telegram-answers] Telegram send failed after 3 attempts (${tag}):`, err)
        return null
      }
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)))
    }
  }
  return null
}

/** Resultado de editar: "ok", "limited" (429 de Telegram) o "failed". */
type EditResult = "ok" | "limited" | "failed"

/** Edita un mensaje ya enviado (lo usa la animación y el final de la respuesta).
 * Reintenta una vez ante 429 de Telegram e informa "limited" para backoff.
 * Con `clearMarkup` quita además el teclado inline en la misma llamada
 * (acuse de permiso: texto + botones fuera en un solo request). */
async function editMessageText(
  token: string,
  chatId: string,
  messageId: number,
  text: string,
  opts?: { clearMarkup?: boolean },
): Promise<EditResult> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const body: Record<string, unknown> = {
        chat_id: chatId,
        message_id: messageId,
        text,
        parse_mode: "HTML",
      }
      if (opts?.clearMarkup) body.reply_markup = { inline_keyboard: [] }
      const res = await fetch(`${TELEGRAM_API}${token}/editMessageText`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (res.ok) return "ok"
      if (res.status === 429) {
        const retryAfter = (await res.json().catch(() => ({}))) as { parameters?: { retry_after?: number } }
        await new Promise((r) => setTimeout(r, (retryAfter.parameters?.retry_after ?? 2) * 1000))
        if (attempt === 1) return "limited"
        continue
      }
      return "failed"
    } catch {
      return "failed"
    }
  }
  return "failed"
}

async function tgApi(token: string, method: string, payload: Record<string, unknown>): Promise<boolean> {
  try {
    const res = await fetch(`${TELEGRAM_API}${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    return res.ok
  } catch {
    return false
  }
}

/**
 * Envía un texto COMPLETO en uno o varios mensajes: si pasa de 4000 se parte
 * en trozos HTML válidos encadenados al primero (reply_to el ancla). Devuelve
 * el message_id del ancla, o null si el primer envío falló. Los ids de todas
 * las partes quedan mapeados a `state.notified[sessionID]` para que responder
 * a cualquiera de ellas llegue a la sesión.
 */
async function sendMultipart(
  token: string,
  chatId: string,
  sessionID: string,
  text: string,
  opts?: { replyMarkup?: unknown; tag?: string; replyTo?: number },
): Promise<number | null> {
  const chunks = splitHtmlChunks(text)
  let anchor: number | null = null
  for (const [k, chunk] of chunks.entries()) {
    const replyTo = k === 0 ? opts?.replyTo : anchor
    const id = await sendTelegram(token, chatId, chunk, {
      replyMarkup: k === 0 ? opts?.replyMarkup : undefined,
      replyTo: typeof replyTo === "number" ? replyTo : undefined,
      tag: k === 0 ? opts?.tag : `${opts?.tag ?? "send"}-part`,
    })
    if (id === null) {
      if (k === 0) return null
      await new Promise((resolve) => setTimeout(resolve, 250))
      continue
    }
    state.notified[String(id)] = { sessionID, time: Date.now() }
    if (anchor === null) anchor = id
  }
  return anchor
}

/**
 * Convierte un "Trabajando …" en el final: si el texto pasa de 4000 se edita
 * la primera parte y las siguientes se envían como mensajes de continuación.
 * Devuelve false si el edit del ancla falló (para borrar el working y caer al
 * envío nuevo).
 */
async function editFinalToMessage(
  token: string,
  chatId: string,
  workingId: number,
  sessionID: string,
  body: string,
): Promise<boolean> {
  const chunks = splitHtmlChunks(body)
  const first = chunks[0]
  const r = await editMessageText(token, chatId, workingId, first)
  if (r !== "ok") return false
  state.notified[String(workingId)] = { sessionID, time: Date.now() }
  for (const [k, chunk] of chunks.entries()) {
    if (k === 0) continue
    const id = await sendTelegram(token, chatId, chunk, { tag: "idle-final-part", replyTo: workingId })
    if (id !== null) state.notified[String(id)] = { sessionID, time: Date.now() }
  }
  return true
}

// ── Extracción de datos del evento ─────────────────────────────────────

interface NotificationInfo {
  agent: string
  lastMessage: string | null
  /** id del último mensaje del asistente (único por turno: sirve de clave de
   *  dedup entre instancias: si idem, ya fue notificada por otra instancia) */
  lastMessageID: string | null
  /** tiempo del último mensaje del asistente (ms) */
  lastMessageTime: number | null
}

interface MessageEntry {
  info: Message
  parts: Part[]
}

/**
 * Detecta si una sesión es un subagente.
 * - Primario: la sesión tiene `parentID` (la sesión hija la rellena).
 * - Fallback heurístico: el título termina en `(@<agente> subagent)`.
 */
function isSubagentSession(parentID: string | null | undefined, title?: string): boolean {
  if (parentID) return true
  if (typeof title === "string" && /\(@[^)]+\s+subagent\)$/i.test(title)) return true
  return false
}

/**
 * Extrae de una sesión el agent y el texto completo de la última respuesta
 * del asistente. `session.messages()` devuelve `[{ info, parts }]`; la parte
 * `info` es el mensaje y `parts` son sus fragmentos.
 */
function extractInfo(entries: MessageEntry[]): NotificationInfo {
  let agent = CONFIG.defaultAgent
  let lastMessage: string | null = null
  let lastMessageID: string | null = null
  let lastMessageTime: number | null = null

  for (let i = entries.length - 1; i >= 0; i--) {
    const entry = entries[i]
    if (entry.info.role === "assistant") {
      const textParts = (entry.parts ?? [])
        .filter((p): p is Extract<Part, { type: "text" }> => p.type === "text" && !!p.text && !p.synthetic)
        .map((p) => p.text)
      if (textParts.length > 0) {
        lastMessage = textParts.join("\n").trim()
        lastMessageID = typeof entry.info.id === "string" ? entry.info.id : null
        lastMessageTime = entry.info.time?.completed ?? entry.info.time?.created ?? null
        // El agente real es el de la última petición de usuario anterior
        for (let j = i - 1; j >= 0; j--) {
          const prev = entries[j]
          if (prev.info.role === "user" && prev.info.agent) {
            agent = prev.info.agent
            break
          }
        }
        break
      }
    }
  }

  return { agent, lastMessage, lastMessageID, lastMessageTime }
}

type PermReply = "once" | "always" | "reject"

interface PermContext {
  permID: string
  sessionID: string
  tool: string
  pattern: string
  variant: "v1" | "v2"
}

/**
 * Normaliza las propiedades de un evento de permiso, añadiendo el `permID`
 * y la `sessionID` necesarios para poder responder. La variante decide cómo
 * responder:
 * - SDK v1 (`permission.updated`): respuesta por `postSessionIdPermissionsPermissionId`.
 * - SDK v2 (`permission.asked` / `permission.v2.asked`): respuesta por `permission2.reply`.
 */
function permInfoFromEvent(eventType: string, props: Record<string, unknown>): PermContext | null {
  const permID = typeof props.id === "string" ? props.id : ""
  const sessionID = typeof props.sessionID === "string" ? props.sessionID : ""
  if (!permID) return null

  const strList = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [])

  if (eventType === "permission.updated") {
    const tool = typeof props.title === "string" ? props.title : ""
    if (!tool) return null
    const pattern = Array.isArray(props.pattern)
      ? strList(props.pattern).join(", ")
      : typeof props.pattern === "string"
        ? props.pattern
        : ""
    return { permID, sessionID, tool, pattern, variant: "v1" }
  }

  if (eventType === "permission.asked" || eventType === "permission.v2.asked") {
    const tool =
      typeof props.permission === "string" && props.permission
        ? props.permission
        : typeof props.action === "string"
          ? props.action
          : ""
    if (!tool) return null
    const patterns = strList(props.patterns)
    const resources = strList(props.resources)
    return {
      permID,
      sessionID,
      tool,
      pattern: patterns.length > 0 ? patterns.join(", ") : resources.join(", "),
      variant: "v2",
    }
  }

  return null
}

// ── Botones y respuestas de permiso ────────────────────────────────────

type PluginClient = Parameters<Plugin>[0]["client"]

/** callback_data = `perm|respuesta|token` (mantener < 64 bytes) */
function buildPermKeyboard(token: string): { inline_keyboard: Array<Array<Record<string, string>>> } {
  const labels: Array<[PermReply, string]> = [
    ["once", CONFIG.permOnceLabel],
    ["always", CONFIG.permAlwaysLabel],
    ["reject", CONFIG.permRejectLabel],
  ]
  return {
    inline_keyboard: [labels.map(([reply, label]) => ({ text: label, callback_data: `${CONFIG.permPrefix}|${reply}|${token}` }))],
  }
}

function parseCallbackData(data: string): { reply: PermReply; token: string } | null {
  const parts = data.split("|")
  if (parts.length !== 3 || parts[0] !== CONFIG.permPrefix) return null
  const reply = parts[1]
  if (reply !== "once" && reply !== "always" && reply !== "reject") return null
  return { reply, token: parts[2] }
}

function makeToken(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4)
}

export type PermOutcome = "granted" | "rejected" | "expired"

/**
 * Texto persistente del acuse de permiso: reemplaza el título "⚠️ Permiso
 * requerido" del mensaje original por el resultado. Si el título no se
 * encuentra (labels personalizados), antepone el resultado al texto.
 * Recibe el texto PLANO del mensaje (message.text del callback); el
 * llamador lo escapa a HTML antes de enviarlo.
 */
export function permOutcomeText(original: string, kind: PermOutcome): string {
  const outcome =
    kind === "granted"
      ? `${CONFIG.permGrantedPrefix}${CONFIG.replySuccessLabel}`
      : kind === "rejected"
        ? `${CONFIG.permRejectedPrefix}${CONFIG.replyRejectedLabel}`
        : `${CONFIG.permissionPrefix}${CONFIG.replyExpiredLabel}`
  const marker = `${CONFIG.permissionPrefix}${CONFIG.permissionTitle}`
  if (original.includes(marker)) return original.replace(marker, outcome)
  return `${outcome}\n\n${original}`
}

/**
 * Normaliza un evento `permission.replied` (v1 plano o v2 plano/anidado) a
 * `{ permID, kind }`. Devuelve null si no trae id o respuesta conocida.
 * "once"/"always" → granted; "reject" → rejected.
 */
export function repliedInfoFromEvent(props: Record<string, unknown>): { permID: string; kind: PermOutcome } | null {
  const data = props.data && typeof props.data === "object" ? (props.data as Record<string, unknown>) : props
  const permID =
    typeof data.requestID === "string" && data.requestID
      ? data.requestID
      : typeof data.permissionID === "string" && data.permissionID
        ? data.permissionID
        : typeof data.id === "string" && data.id
          ? data.id
          : ""
  const reply = typeof data.reply === "string" ? data.reply : typeof data.response === "string" ? data.response : ""
  if (!permID) return null
  if (reply === "reject") return { permID, kind: "rejected" }
  if (reply === "once" || reply === "always") return { permID, kind: "granted" }
  return null
}

/**
 * Fija el resultado de un permiso y lo refleja en TODOS sus mensajes vivos
 * (gemelos de varias instancias): edita cada cuerpo con el acuse persistente
 * y quita los botones en la misma llamada, y borra los tokens. Si el
 * resultado ya estaba fijado (doble tap, o el evento `replied` ganó la
 * carrera al callback), solo limpia botones sin re-editar textos: nunca se
 * pisa un "concedido" con un "expirado".
 * `self` cubre el mensaje pulsado aunque su registro sea pre-upgrade.
 * Devuelve true si esta llamada fijó el resultado.
 */
async function settlePermOutcome(
  token: string,
  chatId: string,
  permID: string,
  kind: PermOutcome,
  self?: { messageId: number; text: string },
): Promise<boolean> {
  return withStateLock(async () => {
    adoptState()
    state.permOutcome = state.permOutcome ?? {}
    if (state.permOutcome[permID]) {
      let changed = false
      for (const [t, b] of Object.entries(state.buttons)) {
        if (b.permID === permID) {
          delete state.buttons[t]
          changed = true
        }
      }
      if (changed) saveState()
      return false
    }
    state.permOutcome[permID] = { kind, time: Date.now() }
    const targets = new Map<number, string>()
    for (const [t, b] of Object.entries(state.buttons)) {
      if (b.permID !== permID) continue
      if (typeof b.messageId === "number") targets.set(b.messageId, b.body ?? "")
      delete state.buttons[t]
    }
    saveState()
    if (self && !targets.has(self.messageId)) targets.set(self.messageId, self.text)
    for (const [messageId, body] of targets) {
      const html = escapeHtml(permOutcomeText(body, kind))
      const edited = await editMessageText(token, chatId, messageId, html, { clearMarkup: true })
      if (edited !== "ok") {
        await tgApi(token, "editMessageReplyMarkup", { chat_id: chatId, message_id: messageId, reply_markup: { inline_keyboard: [] } })
      }
    }
    return true
  })
}

/** Responde al permiso con la API correcta según la variante detectada.
 *
 * Orden probado en runtime:
 * 1. Ruta v1 `POST /session/{id}/permissions/{permissionID}` (método del client).
 * 2. Ruta v2 `POST /api/session/{sessionID}/permission/{requestID}/reply`
 *    invocada con el cliente HTTP interno del SDK (hereda baseUrl + auth
 *    del client que inyecta OpenCode). La opencode actual responde por esta.
 * 3. Si la v2 dice "no encontrado": el `sessionID` del evento puede no ser el
 *    dueño real, así que se listan los pendientes, se localiza el permiso por
 *    su id y se reintenta con su dirección real.
 * 4. `permission2.reply` si el client lo expone (no ocurre en 1.18.x).
 *
 * Si todas fallan, lanza con el detalle de cada intento para diagnosticar.
 */
interface InnerHttp {
  post(opts: Record<string, unknown>): Promise<{ data?: unknown; error?: unknown; response?: { status?: number } }>
  get(opts: Record<string, unknown>): Promise<{ data?: unknown; error?: unknown; response?: { status?: number } }>
}

function innerHttpClient(client: PluginClient): InnerHttp | null {
  const raw = client as unknown as { _client?: InnerHttp; client?: InnerHttp; api?: InnerHttp }
  return raw._client ?? raw.client ?? raw.api ?? null
}

function httpError(prefix: string, r: { error?: unknown; response?: { status?: number } }): string {
  const status = r.response?.status ?? "?"
  const detail = r.error instanceof Error ? r.error.message : JSON.stringify(r.error)
  return `${prefix} HTTP ${status}: ${detail}`
}

/**
 * Localiza un permiso pendiente por su id: primero en la sesión del evento,
 * luego entre todos los pendientes. Devuelve su dirección real o null si ya
 * no existe (respondido en otro lado o caducado).
 */
async function findPendingPermission(
  http: InnerHttp,
  sessionID: string,
  permID: string,
): Promise<{ sessionID: string; requestID: string } | null> {
  const pick = (data: unknown): Array<{ id?: unknown; sessionID?: unknown }> => {
    if (Array.isArray(data)) return data as Array<{ id?: unknown; sessionID?: unknown }>
    if (data && typeof data === "object" && Array.isArray((data as { data?: unknown }).data)) {
      return (data as { data: Array<{ id?: unknown; sessionID?: unknown }> }).data
    }
    return []
  }
  const match = (items: Array<{ id?: unknown; sessionID?: unknown }>) =>
    items.find((it) => typeof it?.id === "string" && it.id === permID)
  try {
    const a = await http.get({ url: "/api/session/{sessionID}/permission", path: { sessionID } })
    if (!a.error) {
      const hit = match(pick(a.data))
      if (hit) {
        return {
          sessionID: typeof hit.sessionID === "string" && hit.sessionID ? hit.sessionID : sessionID,
          requestID: hit.id as string,
        }
      }
    }
  } catch {
    // ignorar y probar el listado global
  }
  try {
    const b = await http.get({ url: "/permission" })
    if (!b.error) {
      const hit = match(pick(b.data))
      if (hit && typeof hit.sessionID === "string" && hit.sessionID) {
        return { sessionID: hit.sessionID, requestID: hit.id as string }
      }
    }
  } catch {
    // ignorar: el llamador informa el fallo
  }
  return null
}

async function replyPermission(client: PluginClient, btn: StoredButton, reply: PermReply): Promise<void> {
  const failures: string[] = []
  const http = innerHttpClient(client)

  const postReply = async (sessionID: string, requestID: string): Promise<string | null> => {
    if (!http) return "no inner http client"
    try {
      const r = await http.post({
        url: "/api/session/{sessionID}/permission/{requestID}/reply",
        path: { sessionID, requestID },
        body: { reply },
        headers: { "Content-Type": "application/json" },
      })
      if (!r.error) return null
      return httpError("v2", r)
    } catch (e) {
      return `v2 threw: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  // 1) v1 (método del client del plugin)
  if (typeof (client as { postSessionIdPermissionsPermissionId?: unknown }).postSessionIdPermissionsPermissionId === "function") {
    try {
      const res = await client.postSessionIdPermissionsPermissionId({
        path: { id: btn.sessionID, permissionID: btn.permID },
        body: { response: reply },
      })
      if (!res.error) return
      const status = (res.response as { status?: number } | undefined)?.status ?? "?"
      failures.push(`v1 HTTP ${status}`)
    } catch (e) {
      failures.push(`v1 threw: ${e instanceof Error ? e.message : String(e)}`)
    }
  } else {
    failures.push("v1 method not on client")
  }

  // 2) v2 directa con la dirección del evento
  const directErr = await postReply(btn.sessionID, btn.permID)
  if (!directErr) return
  failures.push(directErr)

  // 3) self-heal: si no lo encuentra, localizar el pendiente real y reintentar
  if (http && /404|not found/i.test(directErr)) {
    const found = await findPendingPermission(http, btn.sessionID, btn.permID)
    if (found && (found.sessionID !== btn.sessionID || found.requestID !== btn.permID)) {
      const retryErr = await postReply(found.sessionID, found.requestID)
      if (!retryErr) return
      failures.push(`retry@${found.sessionID}: ${retryErr}`)
    } else if (found) {
      failures.push("lookup: el pendiente coincide con lo intentado (el servidor lo rechaza igual)")
    } else {
      failures.push("lookup: ya no está entre los pendientes (respondido en otro lado o caducado)")
    }
  }

  // 4) permission2.reply como último intento
  const v2 = client as unknown as {
    permission2?: { reply(args: { sessionID: string; requestID: string; reply: PermReply }): Promise<unknown> }
  }
  if (v2.permission2) {
    try {
      await v2.permission2.reply({ sessionID: btn.sessionID, requestID: btn.permID, reply })
      return
    } catch (e) {
      failures.push(`permission2 threw: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  throw new Error(`no se pudo responder el permiso ${btn.permID} (${btn.sessionID}): ${failures.join(" | ")}`)
}

// ── Auto-test E2E (verificación automática, sin intervención) ──────────

/**
 * Prueba automática del flujo REAL del botón: el agente pide permiso y el
 * código que usarían los botones (replyPermission) lo responde. Activa
 * selfTestSession (a la que el handler de eventos no notifica, pero sí
 * responde "reject"), envía un prompt que fuerza un permiso externo, espera
 * el resultado del handler y borra la sesión. Informa SOLO por app.log
 * (nunca por Telegram: el canal del usuario no recibe ruido de pruebas).
 * Nunca lanza fuera.
 */
interface SelfTestState {
  sessionID: string
  phase: "waiting" | "ok" | "failed"
  detail: string
}

let activeSelfTest: SelfTestState | null = null

/** Solo un auto-test a la vez (dos instancias del plugin se pisarían el estado). */
let selfTestRunning = false

/** Directorio actual del workspace (para que la sesión de prueba pida
 * permiso REAL). Sesiones creadas sin directory nacen en el home: escribir
 * en Desktop queda dentro del árbol y no pide nada. */
async function findWorkspaceDir(client: PluginClient): Promise<string | null> {
  try {
    const sessions = await client.session.list()
    const home = homedir().toLowerCase().replace(/\\+$/, "")
    let best: string | null = null
    let bestUpdated = -1
    for (const s of (sessions.data ?? []) as Array<{ directory?: string; title?: string; time?: { updated?: number } }>) {
      if (!s.directory || s.title === CONFIG.selfTestSessionTitle) continue
      const dir = s.directory.toLowerCase().replace(/\\+$/, "")
      if (dir === home || /^[a-z]:$/.test(dir)) continue
      const updated = s.time?.updated ?? 0
      if (updated > bestUpdated) {
        best = s.directory
        bestUpdated = updated
      }
    }
    return best
  } catch {
    return null
  }
}

/** Directorio padre + separador, o null si es raíz de unidad. */
function parentDirOf(dir: string): string | null {
  const norm = dir.replace(/[\\/]+$/, "")
  const idx = Math.max(norm.lastIndexOf("\\"), norm.lastIndexOf("/"))
  if (idx <= 0) return null
  return norm.slice(0, idx)
}

async function runSelfTest(
  client: PluginClient,
  log: (message: string, extra?: Record<string, unknown>) => Promise<void>,
  token: string,
  chatId: string,
): Promise<void> {
  if (!CONFIG.selfTest || selfTestRunning || state.selfTestVersion === CONFIG.selfTestVersion) return
  // OpenCode puede cargar el plugin dos veces en el mismo proceso (o TUI +
  // server): releer el archivo fresco evita que otro proceso ya completara la
  // versión y nos haga correr una copia redundante que pisa activeSelfTest.
  try {
    const live = loadState()
    if (live.selfTestVersion === CONFIG.selfTestVersion) {
      state.selfTestVersion = CONFIG.selfTestVersion
      saveState()
      return
    }
  } catch {
    // archivo ilegible: seguir con el estado en memoria
  }
  selfTestRunning = true
  const t0 = Date.now()
  const report = async (ok: boolean, why: string): Promise<void> => {
    // SILENCIOSO para el usuario: el auto-test solo se ve en el log de la app.
    await log(`self-test reply: ${ok ? "OK" : `FAIL: ${why}`} (${Date.now() - t0} ms)`)
  }
  /** Resultado "no aplicable" (entorno sin permiso que pedir): silencioso. */
  const markNope = async (why: string): Promise<void> => {
    state.selfTestVersion = CONFIG.selfTestVersion
    saveState()
    await log(`self-test reply: N/A: ${why}`)
  }

  let sid: string | null = null
  try {
    const wsDir = await findWorkspaceDir(client)
    if (!wsDir) {
      await markNope("no se encontró directorio de workspace")
      return
    }
    const targetParent = parentDirOf(wsDir)
    if (!targetParent) {
      await markNope("workspace es raíz de unidad: sin ruta exterior")
      return
    }
    const target = `${targetParent}\\.telegram-selftest\\probe.txt`

    const created = await client.session.create({ body: { title: CONFIG.selfTestSessionTitle }, query: { directory: wsDir } })
    const s = created.data as { id?: unknown } | undefined
    sid = typeof s?.id === "string" && s.id ? s.id : null
    if (!sid) {
      await report(false, "no se pudo crear la sesión de prueba")
      return
    }
    state.selfTestSessions = [...(state.selfTestSessions ?? []), sid]
    saveState()
    activeSelfTest = { sessionID: sid, phase: "waiting", detail: "" }

    // Si el agente no pide permiso (o el write fue auto-permitido), o se
    // cuelga, vence la prueba: abortar en vez de esperar forever.
    const guard = setTimeout(async () => {
      if (activeSelfTest?.sessionID !== sid || activeSelfTest.phase !== "waiting") return
      activeSelfTest.phase = "failed"
      activeSelfTest.detail = `timeout ${CONFIG.selfTestTimeoutMs} ms sin evento de permiso`
      try {
        await client.session.abort({ path: { id: sid } })
      } catch {
        // sesión ya terminada: no pasa nada
      }
    }, CONFIG.selfTestTimeoutMs)

    let promptErrored = false
    try {
      await client.session.prompt({
        path: { id: sid },
        body: {
          tools: { write: true },
          parts: [{ type: "text", text: CONFIG.selfTestPrompt }],
        },
      })
    } catch {
      promptErrored = true
    } finally {
      clearTimeout(guard)
    }

    const st = activeSelfTest
    activeSelfTest = null
    if (!st || st.sessionID !== sid) {
      // Otra instancia concurrente pisó el estado: no hay dato fiable de la
      // prueba, pero tampoco es un fallo del flujo de botones. Silencioso.
      await markNope("estado del auto-test perdido (instancia concurrente)")
      return
    }
    if (st.phase === "ok") {
      state.selfTestVersion = CONFIG.selfTestVersion
      saveState()
      await report(true, st.detail)
    } else if (st.phase === "waiting" && !promptErrored) {
      // La prueba terminó sin petición de permiso: o el write se auto-permitió
      // (entorno permisivo) o el modelo no intentó el tool. Ninguno es un fallo
      // del flujo de botones: no avisar por Telegram, marcar como vistos y no
      // repetir.
      await markNope("no se produjo un ask de permiso (write permitido o no intentado)")
    } else {
      await report(false, st.detail || "sin evento de permiso")
    }
  } catch (e) {
    await report(false, e instanceof Error ? e.message : String(e))
  } finally {
    selfTestRunning = false
    activeSelfTest = null
    if (sid) {
      state.selfTestSessions = (state.selfTestSessions ?? []).filter((s) => s !== sid)
      saveState()
      try {
        await client.session.delete({ path: { id: sid } })
      } catch {
        // si no se puede borrar queda una sesión "self-test": visible pero inofensiva
      }
    }
  }
}

/** True si la sesión es del auto-test (activo o aún persistido) → no mostrar nada visible. */
function isSelfTestSession(sessionID: string | null | undefined): boolean {
  if (!sessionID) return false
  if (activeSelfTest && activeSelfTest.sessionID === sessionID) return true
  return (state.selfTestSessions ?? []).includes(sessionID)
}

// ── Telegram: procesar respuestas (callback_query y reply) ─────────────

interface TgUser {
  id?: number
  is_bot?: boolean
}
interface TgChat {
  id?: number | string
}
interface TgMessage {
  message_id?: number
  text?: string
  chat?: TgChat
  from?: TgUser
  reply_to_message?: TgMessage
}
interface TgCallbackQuery {
  id?: string
  data?: string
  message?: TgMessage
}
interface TgUpdate {
  update_id?: number
  message?: TgMessage
  callback_query?: TgCallbackQuery
}

async function handleUpdate(client: PluginClient, token: string, chatId: string, update: TgUpdate): Promise<void> {
  const cq = update.callback_query
  if (cq && typeof cq.id === "string" && typeof cq.data === "string") {
    const parsed = parseCallbackData(cq.data)
    const messageId = typeof cq.message?.message_id === "number" ? cq.message.message_id : null
    if (!parsed) {
      await tgApi(token, "answerCallbackQuery", { callback_query_id: cq.id })
      return
    }
    const btn = state.buttons[parsed.token]
    if (!btn || Date.now() - btn.time >= CONFIG.buttonTtlMs) {
      await tgApi(token, "answerCallbackQuery", { callback_query_id: cq.id, text: CONFIG.replyExpiredLabel })
      return
    }
    try {
      await replyPermission(client, btn, parsed.reply)
      const kind: PermOutcome = parsed.reply === "reject" ? "rejected" : "granted"
      const ackText = kind === "rejected" ? CONFIG.replyRejectedLabel : CONFIG.replySuccessLabel
      await tgApi(token, "answerCallbackQuery", { callback_query_id: cq.id, text: ackText })
      // Acuse PERSISTENTE en este mensaje y sus gemelos (misma edición
      // quita los botones). settle no re-edita si el resultado ya estaba
      // fijado por el evento replied o un tap anterior.
      const self =
        messageId !== null
          ? { messageId, text: typeof cq.message?.text === "string" ? cq.message.text : "" }
          : undefined
      await settlePermOutcome(token, chatId, btn.permID, kind, self)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      console.warn("[telegram-answers] error al responder el permiso:", err)
      try {
        await client.app.log({
          body: {
            service: "telegram-answers",
            level: "error",
            message: `error al responder permiso: ${detail}`,
            extra: { sessionID: btn.sessionID, permID: btn.permID },
          },
        })
      } catch {
        // el log no debe bloquear la respuesta
      }
      // Permiso ya consumido en otro lado: no es un fallo nuestro; quitar los
      // botones muertos para no seguir pulsando en vano.
      const gone = /ya no está entre los pendientes|PermissionNotFoundError/i.test(detail)
      await tgApi(token, "answerCallbackQuery", {
        callback_query_id: cq.id,
        text: gone ? CONFIG.replyExpiredLabel : CONFIG.replyFailureLabel,
      })
      if (gone) {
        // Permiso muerto: conciliar sin pisar un resultado ya fijado (settle
        // solo limpia si otro camino ya lo resolvió).
        const self =
          messageId !== null
            ? { messageId, text: typeof cq.message?.text === "string" ? cq.message.text : "" }
            : undefined
        await settlePermOutcome(token, chatId, btn.permID, "expired", self)
      }
    }
    return
  }

  // Responder a una notificación: reinyecta el texto en la sesión que la generó
  const m = update.message
  if (!m || m.from?.is_bot) return
  if (m.chat && String(m.chat.id) !== String(chatId)) return
  const rt = m.reply_to_message
  if (!rt || typeof rt.message_id !== "number") return
  const key = String(rt.message_id)
  const rec = state.notified[key]
  if (!rec || Date.now() - rec.time >= CONFIG.notifiedTtlMs) return
  const text = typeof m.text === "string" ? m.text.trim() : ""
  if (!text) return

  // Sesión ocupada: ENCOLAR en vez de cortar el turno. Se reenvía cuando
  // OpenCode quede idle (drainPendingPrompts). El mapeo notified NO se borra:
  // puedes volver a responder en cualquier momento sin perder trazabilidad.
  if (busySessions.has(rec.sessionID)) {
    const entry: PendingPrompt = {
      id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`,
      sessionID: rec.sessionID,
      text,
      ts: Date.now(),
      status: "queued",
    }
    state.pendingPrompts = [...(state.pendingPrompts ?? []), entry].slice(-CONFIG.queueMaxEntries)
    saveState()
    await sendTelegram(token, chatId, escapeHtml(CONFIG.queueBusyAckLabel), { replyTo: rt.message_id, tag: "queued" })
    return
  }

  try {
    await client.session.prompt({
      path: { id: rec.sessionID },
      body: { parts: [{ type: "text", text, metadata: { via: "telegram-answers" } }] },
    })
    // Sin acuse en Telegram: el reply ya garantiza que llegó; solo se avisa si falla.
  } catch (err) {
    console.warn("[telegram-answers] error inyectando respuesta:", err)
    await sendTelegram(token, chatId, escapeHtml(CONFIG.replyPromptErrorLabel), { replyTo: rt.message_id, tag: "reply-error" })
  }
  delete state.notified[key]
  saveState()
}

// ── Polling de getUpdates (long-poll) ──────────────────────────────────

let polling = false

async function pollTelegram(client: PluginClient, token: string, chatId: string): Promise<void> {
  if (polling) return
  polling = true
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), (CONFIG.updateTimeoutSec + 15) * 1000)
  try {
    const url = `${TELEGRAM_API}${token}/getUpdates?timeout=${CONFIG.updateTimeoutSec}&offset=${state.offset + 1}`
    const res = await fetch(url, { signal: controller.signal })
    if (res.ok) {
      const payload = (await res.json()) as { result?: TgUpdate[] }
      const updates = payload.result ?? []
      for (const u of updates) {
        await handleUpdate(client, token, chatId, u)
        if (typeof u.update_id === "number" && u.update_id > state.offset) state.offset = u.update_id
      }
      if (updates.length > 0) saveState()
    }
  } catch (err) {
    console.warn("[telegram-answers] error en polling:", err)
  } finally {
    clearTimeout(timer)
    polling = false
  }
}

function startPolling(client: PluginClient, token: string, chatId: string): void {
  const tick = () => {
    void pollTelegram(client, token, chatId)
  }
  void tick()
  setInterval(tick, CONFIG.pollIntervalMs)
}

// ── Indicador "Trabajando …" (solo HTTP: no consume tokens de la IA) ──

interface WorkingMsg {
  messageId: number
  idx: number
  /** Cuándo se envió: la animación se auto-expira a CONFIG.workingTtlMs */
  started: number
}
const workingMsgs = new Map<string, WorkingMsg>()
let workingTimer: ReturnType<typeof setInterval> | null = null
/** Periodo actual de la animación: sube solo ante 429 (backoff) */
let workingPeriodMs = CONFIG.workingEditMs

/** Envíos de "Trabajando" aún en vuelo (sendMessage en retry ante 429):
 *  el idle espera por ellos (con tope) para editarlos en vez de duplicar. */
const pendingWorkingSends = new Map<string, Promise<number | null>>()
/** Última respuesta final por sesión: edita un "Trabajando" que llegó tarde. */
const recentFinals = new Map<string, { body: string; time: number }>()
/** Cuándo empezó el último turno busy por sesión: la final del turno ANTERIOR
 *  (time anterior al busy) nunca debe re-editarse sobre un "Trabajando" nuevo. */
const busySince = new Map<string, number>()

function rememberFinal(sessionID: string, body: string): void {
  recentFinals.set(sessionID, { body, time: Date.now() })
  if (recentFinals.size > 40) {
    const oldest = [...recentFinals.entries()].sort((a, b) => a[1].time - b[1].time)[0]
    if (oldest) recentFinals.delete(oldest[0])
  }
}

/** Solo editar un "Trabajando" a la final si la sesión terminó DESPUÉS de
 *  comenzar el turno busy en curso. Una final del turno ANTERIOR (time más
 *  viejo que turnStart) haría que cada busy re-enviase el mensaje previo en
 *  bucle hasta que la tarea actual termina. */
export function shouldEditLateWorking(
  lastFinal: { time: number } | undefined,
  turnStart: number,
  now: number,
  ttlMs: number,
): boolean {
  return !!lastFinal && lastFinal.time > turnStart && now - lastFinal.time < ttlMs
}

// ── Cola de Telegram: replies mientras la sesión está ocupada ──────────
// Un reply a una notificación con la sesión busy se ENCOLA (persistido) y se
// reenvía cuando OpenCode queda idle: uno por sessión, en cada idle. Así las
// respuestas llegan sin cortar el turno en curso.

/** Sesiones actualmente busy (visto desde session.status) */
const busySessions = new Set<string>()
/** ids de mensajes que YA reinyectamos desde la cola: para no re-encolarlos */
const recentDrainIds = new Map<string, number>()
/** Evita promover dos de la cola en el mismo idle */
const drainingNow = new Set<string>()

function isDrainedRecently(messageID: string | null | undefined): boolean {
  if (!messageID) return false
  if (!recentDrainIds.has(messageID)) return false
  const t = recentDrainIds.get(messageID) ?? 0
  return Date.now() - t < CONFIG.notifiedTtlMs
}

/**
 * Promueve UN mensaje de la cola persistida hacia la sesión cuando queda
 * idle. Con `client.session.prompt` entra igual que un prompt del chat: la
 * sesión se pone busy y, al terminar, un nuevo idle promoverá el siguiente.
 */
async function drainPendingPrompts(client: PluginClient, sessionID: string): Promise<void> {
  const plog = async (message: string): Promise<void> => {
    try {
      await client.app.log({ body: { service: "telegram-answers", level: "info", message, extra: { sessionID } } })
    } catch {
      console.log(`[telegram-answers] ${message}`)
    }
  }
  if (isSelfTestSession(sessionID) || drainingNow.has(sessionID)) return
  const queue = state.pendingPrompts ?? []
  const idx = queue.findIndex((p) => p.sessionID === sessionID && p.status === "queued")
  if (idx === -1) return
  drainingNow.add(sessionID)
  try {
    const entry = queue[idx]
    state.pendingPrompts!.splice(idx, 1, { ...entry, status: "promoting" })
    saveState()
    try {
      const res = await client.session.prompt({
        path: { id: sessionID },
        body: { parts: [{ type: "text", text: entry.text, metadata: { via: "telegram-answers" } }] },
      })
      const resData = res as unknown as { data?: { id?: unknown } }
      const mid = typeof resData?.data?.id === "string" ? (resData.data as { id: string }).id : null
      if (mid) {
        recentDrainIds.set(mid, Date.now())
        for (const [k, t] of recentDrainIds) if (Date.now() - t > CONFIG.notifiedTtlMs) recentDrainIds.delete(k)
      }
      // Releer y quitar SOLO si esta entrada sigue en "promoting" (el archivo
      // es compartido entre instancias)
      const live = loadState()
      const liveIdx = (live.pendingPrompts ?? []).findIndex((p) => p.id === entry.id)
      if (liveIdx !== -1 && live.pendingPrompts![liveIdx].status === "promoting") {
        live.pendingPrompts!.splice(liveIdx, 1)
        state.pendingPrompts = live.pendingPrompts
        saveState()
      }
    } catch (e) {
      // Falló la inyección: la entrada vuelve a "queued" para reintentar en el
      // próximo idle (no perdemos mensajes del usuario)
      const live = loadState()
      const liveIdx = (live.pendingPrompts ?? []).findIndex((p) => p.id === entry.id)
      if (liveIdx !== -1) live.pendingPrompts![liveIdx] = { ...entry, status: "queued" }
      state.pendingPrompts = live.pendingPrompts
      saveState()
      await plog(`cola: falló reenvío, se reintenta en el próximo idle (${e instanceof Error ? e.message : String(e)})`)
    }
  } finally {
    drainingNow.delete(sessionID)
  }
}

function workingText(frame: string): string {
  return escapeHtml(`${CONFIG.workingLabel} ${frame}`)
}

/** Una entrada pendiente vale para finalizar si aún no caducó. */
function isWorkingEntryFresh(entry: { time: number } | undefined, now: number): boolean {
  return !!entry && now - entry.time < CONFIG.workingTtlMs
}

/** Siguiente periodo de animación: se duplica ante 429, vuelve a base si va bien. */
function nextWorkingPeriod(currentMs: number, limited: boolean): number {
  if (limited) return Math.min(CONFIG.workingMaxEditMs, currentMs * 2)
  return CONFIG.workingEditMs
}

function stopWorkingTimer(): void {
  if (workingTimer) {
    clearInterval(workingTimer)
    workingTimer = null
  }
  workingPeriodMs = CONFIG.workingEditMs
}

function ensureWorkingTimer(token: string, chatId: string): void {
  if (workingTimer || workingMsgs.size === 0) return
  workingTimer = setInterval(() => {
    void workingTick(token, chatId)
  }, workingPeriodMs)
}

async function workingTick(token: string, chatId: string): Promise<void> {
  const now = Date.now()
  let expired = false
  let limited = false
  for (const [sid, w] of workingMsgs) {
    if (now - w.started >= CONFIG.workingTtlMs) {
      // Sin finalize desde hace rato (reinicio incluido): borrar, no colgar
      workingMsgs.delete(sid)
      delete state.working[sid]
      expired = true
      void tgApi(token, "deleteMessage", { chat_id: chatId, message_id: w.messageId })
      continue
    }
    w.idx = (w.idx + 1) % CONFIG.workingFrames.length
    const r = await editMessageText(token, chatId, w.messageId, workingText(CONFIG.workingFrames[w.idx]))
    if (r === "limited") limited = true
  }
  if (expired) saveState()
  if (workingMsgs.size === 0) {
    stopWorkingTimer()
    return
  }
  const next = nextWorkingPeriod(workingPeriodMs, limited)
  if (next !== workingPeriodMs) {
    // Backoff (o recuperación): reprogramar con el nuevo periodo
    workingPeriodMs = next
    stopWorkingTimerKeepPeriod()
    ensureWorkingTimer(token, chatId)
  }
}

/** Detiene el temporizador sin resetear el periodo de backoff en curso. */
function stopWorkingTimerKeepPeriod(): void {
  if (workingTimer) {
    clearInterval(workingTimer)
    workingTimer = null
  }
}

function startWorkingMessage(token: string, chatId: string, sessionID: string, messageId: number, since?: number): void {
  const started = since ?? Date.now()
  workingMsgs.set(sessionID, { messageId, idx: 0, started })
  state.working[sessionID] = { messageId, time: started }
  saveState()
  ensureWorkingTimer(token, chatId)
}

/**
 * Reclama el "Trabajando …" pendiente para finalizarlo: deja de animar y
 * olvida la entrada (en memoria y persistida). Devuelve su message_id o null.
 * Una reserva en vuelo (messageId 0, puesta por otra instancia que aún no
 * terminó de enviar) NO es editable: devuelve null sin tocarla.
 */
function takeWorking(sessionID: string): number | null {
  const mem = workingMsgs.get(sessionID)
  workingMsgs.delete(sessionID)
  const stored = state.working[sessionID]
  delete state.working[sessionID]
  if (mem || stored) saveState()
  if (mem) return mem.messageId
  if (stored && stored.messageId > 0 && isWorkingEntryFresh(stored, Date.now())) return stored.messageId
  return null
}

type WorkingSlot = { kind: "revive"; messageId: number } | { kind: "send" } | { kind: "skip" }

/**
 * Single-flight del "Trabajando …" entre instancias (TUI+server, busy
 * repetidos): bajo lock se relee el archivo fresco y se decide —
 * - "revive": ya hay un mensaje vivo → animarlo, NO enviar otro;
 * - "skip": otra instancia lo está enviando ahora (reserva messageId 0);
 * - "send": reservar el slot y enviar uno nuevo.
 * Con `force` se reserva aunque haya entrada (el mensaje anterior murió).
 */
async function claimWorkingSlot(sessionID: string, force = false): Promise<WorkingSlot> {
  return withStateLock(async () => {
    adoptState()
    const now = Date.now()
    const existing = state.working[sessionID]
    if (!force && existing && existing.messageId > 0 && now - existing.time < CONFIG.workingTtlMs) {
      return { kind: "revive", messageId: existing.messageId }
    }
    if (!force && existing && existing.messageId === 0 && now - existing.time < CONFIG.workingClaimTtlMs) {
      return { kind: "skip" }
    }
    state.working[sessionID] = { messageId: 0, time: now }
    saveState()
    return { kind: "send" }
  })
}

/** Libera una reserva propia (solo si sigue siendo reserva: messageId 0). */
async function clearWorkingSlot(sessionID: string): Promise<void> {
  await withStateLock(async () => {
    adoptState()
    const e = state.working[sessionID]
    if (e && e.messageId === 0) {
      delete state.working[sessionID]
      saveState()
    }
  })
}

/** La final de ESTE turno ya se entregó por otra vía: no duplicarla. */
export function isFinalAlreadyDelivered(lastFinal: { time: number } | undefined, turnStart: number): boolean {
  return !!lastFinal && lastFinal.time > turnStart
}

/**
 * Borra los "Trabajando …" huérfanos (caducados sin finalize, p.ej. tras un
 * reinicio): ni el temporizador ni la persistencia los dejan colgados.
 */
async function sweepStaleWorking(token: string, chatId: string, exceptSessionID?: string): Promise<void> {
  const now = Date.now()
  let changed = false
  for (const [sid, entry] of Object.entries(state.working)) {
    if (sid === exceptSessionID) continue
    if (entry.messageId === 0) {
      // Reserva de otra instancia: solo se limpia si el dueño murió
      if (now - entry.time >= CONFIG.workingClaimTtlMs) {
        workingMsgs.delete(sid)
        delete state.working[sid]
        changed = true
      }
      continue
    }
    if (now - entry.time < CONFIG.workingTtlMs) continue
    workingMsgs.delete(sid)
    delete state.working[sid]
    changed = true
    await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: entry.messageId })
  }
  for (const [sid, w] of workingMsgs) {
    if (sid === exceptSessionID || now - w.started < CONFIG.workingTtlMs) continue
    workingMsgs.delete(sid)
    delete state.working[sid]
    changed = true
    await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: w.messageId })
  }
  if (changed) saveState()
  if (workingMsgs.size === 0) stopWorkingTimer()
}

// ── Plugin ─────────────────────────────────────────────────────────────

const plugin: Plugin = async ({ client, directory }) => {
  loadEnvFile(directory)

  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID
  const log = async (message: string, extra?: Record<string, unknown>) => {
    try {
      await client.app.log({ body: { service: "telegram-answers", level: "info", message, extra } })
    } catch {
      console.log(`[telegram-answers] ${message}`)
    }
  }

  if (!token || !chatId) {
    await log("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Notificaciones y respuestas desactivadas.")
    return {}
  }

  startPolling(client, token, chatId)
  await log("Notificaciones y respuestas de Telegram habilitadas")
  // Auto-verificación E2E en segundo plano: informa sola por Telegram/log
  void runSelfTest(client, log, token, chatId)

  return {
    event: async ({ event }) => {
      try {
        const etype = event.type as string

        if (etype === "session.idle") {
          const props = (event.properties ?? {}) as Record<string, unknown>
          const sessionID = typeof props.sessionID === "string" ? props.sessionID : ""
          if (!sessionID) return
          if (isSelfTestSession(sessionID)) return
          const key = `idle:${sessionID}`
          if (!shouldNotify(key)) return

          const [sessionRes, messagesRes] = await Promise.all([
            client.session.get({ path: { id: sessionID } }),
            client.session.messages({ path: { id: sessionID } }),
          ])

          // El envío del final va bajo lock: si otra instancia ya notificó ESTA
          // misma respuesta (mismo message id del asistente), no reenviar.
          await withStateLock(async (locked) => {
            adoptState()
            const title = sessionRes.data?.title ?? CONFIG.emptySessionTitle
            if (CONFIG.skipSubagent && isSubagentSession(sessionRes.data?.parentID, title)) {
              await log(`idle de subagente ignorado: ${title}`)
              return
            }
            const entries: MessageEntry[] = (messagesRes.data ?? []) as MessageEntry[]
            const { agent, lastMessage, lastMessageID, lastMessageTime } = extractInfo(entries)

            if (!lastMessage) {
              await log(`session-idle no text: ${title}`)
              return
            }

            // Dedup entre instancias: limpiar también nuestro "Trabajando …"
            // huérfano para que no quede animando aunque otra ya finalizó.
            if (lastMessageID) {
              const prev = state.lastFinal?.[sessionID]
              if (prev && prev.messageID === lastMessageID && Date.now() - prev.time < CONFIG.dedupTtlMs) {
                takeWorking(sessionID)
                await log(`idle duplicado de otra instancia ignorado: ${title}`)
                return
              }
            }

            const agentLabel = agent.charAt(0).toUpperCase() + agent.slice(1)
            const header = `<b>${escapeHtml(CONFIG.sessionLabel)}: &quot;${escapeHtml(title)}&quot;</b>${escapeHtml(CONFIG.titleSeparator)}<b>${escapeHtml(CONFIG.agentLabel)}: ${escapeHtml(agentLabel)}</b>`
            // SIN truncado: el texto COMPLETO del último mensaje. Si pasa de
            // 4000, el "Trabajando …" se edita a la primera parte y el resto
            // llega como mensajes de continuación encadenados.
            const body = header + "\n\n" + markdownToHtml(lastMessage)
            rememberFinal(sessionID, body)

            await sweepStaleWorking(token, chatId, sessionID)

            const markLastFinal = (): void => {
              state.lastFinal = state.lastFinal ?? {}
              state.lastFinal[sessionID] = {
                messageID: lastMessageID ?? `t${lastMessageTime ?? Date.now()}`,
                time: Date.now(),
              }
            }

            // Si había un "Trabajando …", se EDITA a la respuesta final. Si el
            // edit falla, se borra y la final llega como mensaje nuevo: nunca
            // queda un "Trabajando" colgado.
            const workingId = takeWorking(sessionID)
            if (workingId !== null) {
              const edited = await editFinalToMessage(token, chatId, workingId, sessionID, body)
              if (edited) {
                markLastFinal()
                saveState()
                await log(`finalizada (editada): ${agent} - ${title}`)
                await drainPendingPrompts(client, sessionID)
                return
              }
              await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: workingId })
            }

            // El "Trabajando …" puede estar aún en vuelo (sendMessage en retry
            // ante 429): esperar con tope y editarlo en vez de enviar duplicado.
            const inFlight = pendingWorkingSends.get(sessionID)
            if (inFlight) {
              let lateWorkingId: number | null = null
              try {
                lateWorkingId = await Promise.race([
                  inFlight,
                  new Promise<null>((resolve) => setTimeout(() => resolve(null), 8000)),
                ])
              } catch {
                lateWorkingId = null
              }
              if (lateWorkingId !== null) {
                const edited = await editFinalToMessage(token, chatId, lateWorkingId, sessionID, body)
                if (edited) {
                  markLastFinal()
                  saveState()
                  await log(`finalizada (editada, en vuelo): ${agent} - ${title}`)
                  await drainPendingPrompts(client, sessionID)
                  return
                }
                await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: lateWorkingId })
              }
            }

            const messageId = await sendMultipart(token, chatId, sessionID, body, { tag: "idle-final" })
            if (messageId !== null) {
              markLastFinal()
              saveState()
            } else {
              // Última bala: editar el "Trabajando" que quedó animando con la
              // final (si el envío nuevo murió por 429) para no perder el texto.
              const alive = await takeWorking(sessionID)
              if (alive !== null) {
                const edited = await editFinalToMessage(token, chatId, alive, sessionID, body)
                if (edited) {
                  markLastFinal()
                  saveState()
                  await log(`finalizada (fallback edit): ${agent} - ${title}`)
                  await drainPendingPrompts(client, sessionID)
                  return
                }
              }
              await log(`idle no enviado: ${agent} - ${title}`)
              return
            }
            await log(`notified idle: ${agent} - ${title}`)
            await drainPendingPrompts(client, sessionID)
          })
        }

        // "Trabajando …": session.status marca busy al empezar a responder
        if (etype === "session.status") {
          const sprops = (event.properties ?? {}) as Record<string, unknown>
          const sessionID = typeof sprops.sessionID === "string" ? sprops.sessionID : ""
          const st = sprops.status as { type?: string } | null | undefined
          if (!sessionID || !st || typeof st.type !== "string") return
          if (isSelfTestSession(sessionID)) return
          if (st.type === "busy") {
            busySessions.add(sessionID)
            busySince.set(sessionID, Date.now())
            if (busySince.size > 40) {
              const oldest = [...busySince.entries()].sort((a, b) => a[1] - b[1])[0]
              if (oldest) busySince.delete(oldest[0])
            }
            if (!CONFIG.workingEnabled) return
            await sweepStaleWorking(token, chatId, sessionID)
            if (workingMsgs.has(sessionID)) return
            if (pendingWorkingSends.has(sessionID)) return
            // Single-flight entre instancias y busy repetidos: reclamar el
            // slot antes de enviar. "revive" = animar el existente;
            // "skip" = otra instancia lo envía ahora; "send" = enviar nuevo.
            const slot = await claimWorkingSlot(sessionID)
            if (slot.kind === "skip") return
            if (slot.kind === "revive") {
              const revived = await editMessageText(token, chatId, slot.messageId, workingText(CONFIG.workingFrames[0]))
              if (revived === "ok" || revived === "limited") {
                // "limited" (flood 429): conservar el mensaje y animarlo con
                // backoff en vez de borrar+recrear (eso duplicaba el
                // "Trabajando" bajo flood).
                startWorkingMessage(token, chatId, sessionID, slot.messageId)
                await log(`working (reutilizado): ${sessionID}`)
                return
              }
              await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: slot.messageId })
              const slot2 = await claimWorkingSlot(sessionID, true)
              if (slot2.kind !== "send") return
            }
            if (!shouldNotify(`status:${sessionID}`)) {
              await clearWorkingSlot(sessionID)
              return
            }
            try {
              const sres = await client.session.get({ path: { id: sessionID } })
              const title = sres.data?.title ?? ""
              if (CONFIG.skipSubagent && isSubagentSession(sres.data?.parentID, title)) {
                await log(`working de subagente ignorado: ${title}`)
                return
              }
            } catch {
              // sesión aún no disponible: notificar igual
            }
            const sendW = sendTelegram(token, chatId, workingText(CONFIG.workingFrames[0]), { tag: "working" })
            pendingWorkingSends.set(sessionID, sendW)
            const messageId = await sendW
            if (pendingWorkingSends.get(sessionID) === sendW) pendingWorkingSends.delete(sessionID)
            if (messageId === null) {
              await clearWorkingSlot(sessionID)
              return
            }
            // La sesión pudo terminar mientras este envío iba retrasado por
            // 429: si la final de ESTE turno ya se entregó por otra vía, el
            // "Trabajando" tardío se BORRA (editarlo duplicaría la respuesta).
            // Solo si aún no hay final entregada se edita como última bala.
            const lastFinal = recentFinals.get(sessionID)
            const turnStart = busySince.get(sessionID) ?? 0
            if (lastFinal && shouldEditLateWorking(lastFinal, turnStart, Date.now(), CONFIG.workingTtlMs)) {
              adoptState()
              if (isFinalAlreadyDelivered(state.lastFinal?.[sessionID], turnStart)) {
                await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: messageId })
                await log(`working tardío descartado (final ya entregada): ${sessionID}`)
                return
              }
              const edited = await editMessageText(token, chatId, messageId, lastFinal.body)
              if (edited === "ok") {
                state.notified[String(messageId)] = { sessionID, time: Date.now() }
                saveState()
                await log(`working tardío finalizado: ${sessionID}`)
                return
              }
              await tgApi(token, "deleteMessage", { chat_id: chatId, message_id: messageId })
              return
            }
            startWorkingMessage(token, chatId, sessionID, messageId)
            await log(`working: ${sessionID}`)
          } else if (st.type === "idle") {
            busySessions.delete(sessionID)
            // NO olvidar aquí: session.idle finaliza con takeWorking; un
            // idle de status solo barre huérfanos caducados.
            await sweepStaleWorking(token, chatId)
            void drainPendingPrompts(client, sessionID)
          }
        }

        if (etype === "permission.updated" || etype === "permission.asked" || etype === "permission.v2.asked") {
          const rawProps = (event.properties ?? {}) as Record<string, unknown>
          const ctx = permInfoFromEvent(etype, rawProps)
          if (!ctx) {
            await log(`permission event sin información: ${etype}`)
            return
          }
          const key = `perm:${ctx.permID}`
          if (!shouldNotify(key)) return

          // Auto-test: responder NO visible. Es la sesión desechable: el
          // permiso que pide es el desencadenado por runSelfTest y se responde
          // con el MISMO replyPermission de los botones (sin mandar nada a
          // Telegram) para validar el flujo real.
          if (isSelfTestSession(ctx.sessionID)) {
            const st = activeSelfTest
            if (st && st.phase === "waiting") {
              const tReply = Date.now()
              try {
                await replyPermission(client, { sessionID: ctx.sessionID, permID: ctx.permID, variant: ctx.variant, time: Date.now() }, "reject")
                st.phase = "ok"
                st.detail = `reject por ${ctx.variant} en ${Date.now() - tReply} ms`
              } catch (e) {
                st.phase = "failed"
                st.detail = e instanceof Error ? e.message : String(e)
              }
            }
            return
          }

          // El permiso llega sin contexto de qué sesión lo pide: añadimos el
          // título de la sesión para saber de qué chat/ventana viene. Si no hay
          // sessionID o falla la lectura, cae en "Sin título".
          let sessionTitle = CONFIG.emptySessionTitle
          if (ctx.sessionID) {
            try {
              const sessionRes = await client.session.get({ path: { id: ctx.sessionID } })
              sessionTitle = sessionRes.data?.title ?? CONFIG.emptySessionTitle
            } catch {
              // sesión aún no disponible — usar el título por defecto
            }
          }

          const sessionLine = `<b>${escapeHtml(CONFIG.sessionLabel)}: &quot;${escapeHtml(sessionTitle)}&quot;</b>`
          const msg = `${escapeHtml(CONFIG.permissionPrefix)}<b>${escapeHtml(CONFIG.permissionTitle)}</b>\n\n${sessionLine}\n\n<b>${escapeHtml(CONFIG.permissionToolLabel)}:</b> <code>${escapeHtml(ctx.tool)}</code>${ctx.pattern ? `\n<b>${escapeHtml(CONFIG.permissionPatternLabel)}:</b> <code>${escapeHtml(ctx.pattern)}</code>` : ""}`

          if (ctx.sessionID) {
            const btok = makeToken()
            const tPerm0 = Date.now()
            // Multiparte: si la herramienta o el patrón pasan de 4096, se envía
            // completo encadenado (los botones van en la primera parte).
            const anchor = await sendMultipart(token, chatId, ctx.sessionID, msg, { replyMarkup: buildPermKeyboard(btok), tag: "perm" })
            const dtPerm = Date.now() - tPerm0
            if (dtPerm > 10000) await log(`perm notify lento: ${dtPerm} ms (${ctx.tool})`)
            // Cuerpo plano espejo del HTML: permite conciliar gemelos (y este
            // mensaje) al resolverse el permiso, aunque haya varias instancias.
            const plainBody =
              `${CONFIG.permissionPrefix}${CONFIG.permissionTitle}\n\n` +
              `${CONFIG.sessionLabel}: "${sessionTitle}"\n\n` +
              `${CONFIG.permissionToolLabel}: ${ctx.tool}` +
              (ctx.pattern ? `\n${CONFIG.permissionPatternLabel}: ${ctx.pattern}` : "")
            state.buttons[btok] = { sessionID: ctx.sessionID, permID: ctx.permID, variant: ctx.variant, time: Date.now(), messageId: anchor, body: plainBody }
            saveState()
          } else {
            await sendTelegram(token, chatId, msg, { tag: "perm-notitle" })
          }
          await log(`notified permiso: ${ctx.tool}`)
        }

        // Permiso resuelto en CUALQUIER vía (botón de Telegram, TUI,
        // auto-aprobado): conciliar sus mensajes (incluidos gemelos de otra
        // instancia) con el resultado. Sin toast: la edición ES el acuse.
        if (etype === "permission.replied") {
          const info = repliedInfoFromEvent((event.properties ?? {}) as Record<string, unknown>)
          if (info) {
            const fixed = await settlePermOutcome(token, chatId, info.permID, info.kind)
            await log(`permiso conciliado (${info.kind}${fixed ? "" : ", ya fijado"}): ${info.permID}`)
          }
        }
      } catch (err) {
        console.warn("[telegram-answers] Error processing event:", err)
      }
    },
  }
}

// ── Markdown → HTML (Telegram) ─────────────────────────────────────────

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

/**
 * Convierte markdown (salida típica de un agente) a HTML compatible con
 * Telegram (parse_mode="HTML"). Soporta: negrita, cursiva, tachado, código
 * inline, bloques de código, encabezados, listas, enlaces, citas y hr.
 */
function markdownToHtml(md: string): string {
  const lines = escapeHtml(md).split("\n")
  const out: string[] = []
  let inCode = false
  const codeBuf: string[] = []

  for (const rawLine of lines) {
    const line = rawLine.replace(/\r$/, "")
    if (/^\s*```/.test(line)) {
      if (inCode) {
        out.push("<pre>" + codeBuf.join("\n") + "</pre>")
        codeBuf.length = 0
        inCode = false
      } else {
        inCode = true
      }
      continue
    }
    if (inCode) {
      codeBuf.push(line)
      continue
    }
    if (!line.trim()) {
      out.push("")
      continue
    }
    out.push(transformLine(line))
  }
  if (inCode && codeBuf.length > 0) {
    out.push("<pre>" + codeBuf.join("\n") + "</pre>")
  }

  return out.join("\n").replace(/\n{3,}/g, "\n\n")
}

function transformLine(line: string): string {
  const heading = /^#{1,6}\s+(.*)$/.exec(line)
  if (heading) return `<b>${transformInline(heading[1])}</b>`

  const quote = /^&gt;\s?(.*)$/.exec(line)
  if (quote) return `<i>\u25b8 ${transformInline(quote[1])}</i>`

  if (/^\s*(\*{3,}|-{3,}|_{3,})\s*$/.test(line)) return "\u2500".repeat(14)

  return transformInline(line.replace(/^\s*[-*+]\s+/, "\u2022 "))
}

function transformInline(text: string): string {
  return text
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/\*(.+?)\*/g, "<i>$1</i>")
    .replace(/~~(.+?)~~/g, "<s>$1</s>")
}

export {
  escapeHtml,
  extractInfo,
  isSubagentSession,
  buildPermKeyboard,
  isWorkingEntryFresh,
  markdownToHtml,
  nextWorkingPeriod,
  parseCallbackData,
  permInfoFromEvent,
  replyPermission,
  splitHtmlChunks,
  workingText,
  transformInline,
  isDrainedRecently,
  isSelfTestSession,
}
export type { PermReply, StoredButton, PendingPrompt, NotificationInfo }
export default plugin