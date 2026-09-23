import type { Plugin } from "@opencode-ai/plugin"
import type { Part } from "@opencode-ai/sdk"
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const STATE_FILE = join(homedir(), ".config", "opencode", ".opencode-queue.json")

/**
 * ── CONFIGURACIÓN EDITABLE ─────────────────────────────────────────────
 * Todo lo que una persona deba personalizar vive aquí: etiquetas, idioma,
 * límites. No hace falta tocar la lógica del plugin.
 * ───────────────────────────────────────────────────────────────────────
 */
const CONFIG = {
  /** Máximo de mensajes encolados (los más viejos se descartan) */
  maxEntries: 25,
  /** Captura por defecto: todo lo escrito con la sesión ocupada se encola
   *  SIN necesidad del sufijo " /queue" (que sigue válido y se limpia).
   *  En false vuelve al modo sufijo explícito. `/queue stop` pausa igual. */
  captureAllBusy: true,
  /** Cuántos segundos conserva la marca "este mensaje lo reinyecté yo" */
  drainTtlMs: 24 * 60 * 60 * 1000,
  /** Placeholder oculto: no llega al modelo ni se muestra en el TUI */
  hiddenText: "...",
  /** Etiqueta del plugin en los logs */
  logTag: "tui-queue",
  /** Texto de ayuda del comando /queue */
  helpText:
    "Queue (captura automática en ocupado: lo que escribas se encola y sale al quedar libre): /queue list | /queue front | /queue now <texto> | /queue stop | /queue start | /queue flush [all].",
}

// ── Estado persistido entre reinicios de OpenCode ─────────────────────

export interface QueueEntry {
  id: string
  sessionID: string
  text: string
  ts: number
}

export interface QueueState {
  /** Captura activa: encolar cuando la sesión esté ocupada */
  alwaysOn: boolean
  /** Pausado manual: no encolar ni promover nada */
  stopped: boolean
  entries: QueueEntry[]
}

export function makeId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

export function defaultState(): QueueState {
  return { alwaysOn: true, stopped: false, entries: [] }
}

export function loadQueueFrom(file: string): QueueState {
  try {
    if (existsSync(file)) {
      const raw = JSON.parse(readFileSync(file, "utf-8")) as Partial<QueueState>
      return {
        alwaysOn: raw.alwaysOn !== false,
        stopped: raw.stopped === true,
        entries: Array.isArray(raw.entries)
          ? raw.entries.filter((e) => e && typeof e.id === "string" && typeof e.sessionID === "string" && typeof e.text === "string")
          : [],
      }
    }
  } catch {
    // estado corrupto → empezar de cero
  }
  return defaultState()
}

function loadQueue(): QueueState {
  return loadQueueFrom(STATE_FILE)
}

export function saveQueueRaw(state: QueueState, file = STATE_FILE): void {
  mkdirSync(join(homedir(), ".config", "opencode"), { recursive: true })
  writeFileSync(file, JSON.stringify(state))
}

// ── Lógica pura de la cola (testeable sin red) ────────────────────────

/** Añade un mensaje a la cola de la sesión (podando el exceso). Mutador. */
export function enqueueText(state: QueueState, sessionID: string, text: string, max = CONFIG.maxEntries): QueueEntry {
  const entry: QueueEntry = { id: makeId(), sessionID, text, ts: Date.now() }
  state.entries = [...state.entries, entry].slice(-max)
  return entry
}

/** Saca el más antiguo de la sesión. Mutador. Devuelve null si vacía. */
export function promoteOne(state: QueueState, sessionID: string): QueueEntry | null {
  const idx = state.entries.findIndex((e) => e.sessionID === sessionID)
  if (idx === -1) return null
  const [entry] = state.entries.splice(idx, 1)
  return entry
}

/** Entradas de una sesión (o de todas si sessionID es null), en orden. */
export function listOf(state: QueueState, sessionID: string | null): QueueEntry[] {
  return sessionID === null ? state.entries.slice() : state.entries.filter((e) => e.sessionID === sessionID)
}

/** Devuelve la siguiente que se promovería. */
export function frontOf(state: QueueState, sessionID: string | null): QueueEntry | null {
  const list = listOf(state, sessionID)
  return list.length > 0 ? list[0] : null
}

/** Borra una entrada por id. Devuelve true si existía. */
export function removeById(state: QueueState, id: string): boolean {
  const before = state.entries.length
  state.entries = state.entries.filter((e) => e.id !== id)
  return state.entries.length < before
}

/** Vacía las entradas de una sesión (o todas). Devuelve cuántas borró. */
export function flushFor(state: QueueState, sessionID: string | null): number {
  const before = state.entries.length
  state.entries = sessionID === null ? [] : state.entries.filter((e) => e.sessionID !== sessionID)
  return before - state.entries.length
}

/**
 * Detecta la sintaxis trailing: un mensaje normal que TERMINA en " /queue"
 * (o "/queue" como última palabra). Devuelve el texto limpio y si hay que
 * encolarlo.
 */
export function extractTrailingQueue(text: string): { text: string; queueIt: boolean } {
  const cleaned = text.replace(/\s+$/, "")
  const m = /\s+\/queue\s*$/.exec(text)
  if (!m) return { text, queueIt: false }
  const trimmed = cleaned.slice(0, cleaned.length - m[0].trimEnd().length).trimEnd()
  return { text: trimmed.replace(/\s+\/queue$/, ""), queueIt: true }
}

export type QueueOp = "list" | "front" | "now" | "stop" | "start" | "flush" | "help"

/** Parsea los argumentos de /queue (después de "/queue"). */
export function parseQueueArgs(args: string): { op: QueueOp; text: string; all: boolean } {
  const tokens = args.trim().split(/\s+/)
  const head = (tokens[0] ?? "").toLowerCase()
  if (head === "list") return { op: "list", text: "", all: false }
  if (head === "front") return { op: "front", text: "", all: false }
  if (head === "now") return { op: "now", text: args.slice(3).trim(), all: false }
  if (head === "stop") return { op: "stop", text: "", all: false }
  if (head === "start") return { op: "start", text: "", all: false }
  if (head === "flush") {
    const rest = args.trim().slice(head.length).trim().toLowerCase()
    return { op: "flush", text: "", all: rest === "all" }
  }
  return { op: "help", text: "", all: false }
}

export function isQueueCommand(text: string): boolean {
  return /^\s*\/queue\b/.test(text)
}

type PluginClient = Parameters<Plugin>[0]["client"]

// ── Plugin ─────────────────────────────────────────────────────────────

const plugin: Plugin = async ({ client }) => {
  const log = async (message: string): Promise<void> => {
    try {
      await client.app.log({ body: { service: CONFIG.logTag, level: "info", message } })
    } catch {
      console.log(`[${CONFIG.logTag}] ${message}`)
    }
  }

  let qstate = loadQueue()
  const saveQueue = (): void => {
    try {
      saveQueueRaw(qstate)
    } catch {
      // ignore state write errors
    }
  }

  /** Sesiones busy según los eventos de sesión */
  const busySessions = new Set<string>()
  /** Mensajes que reinyectó este plugin: para no re-encolarlos */
  const recentDrainIds = new Map<string, number>()
  /** Mientras promovemos, ignoramos el chat.message que provoca el prompt */
  let promotingNow: string | null = null

  const isDrainedRecently = (sessionID: string, messageID: string | undefined): boolean => {
    if (!messageID) return false
    if (recentDrainIds.get(messageID) && Date.now() - (recentDrainIds.get(messageID) ?? 0) < CONFIG.drainTtlMs) return true
    return false
  }

  const pruneDrainIds = (): void => {
    const now = Date.now()
    for (const [k, t] of recentDrainIds) if (now - t > CONFIG.drainTtlMs) recentDrainIds.delete(k)
  }

  async function toast(title: string, message: string, variant: "info" | "success" | "warning" | "error" = "info"): Promise<void> {
    try {
      await client.tui.showToast({ body: { title, message, variant, duration: 4000 } })
    } catch {
      await log(`toast (${variant}): ${message}`)
    }
  }

  const preview = (text: string, max = 60): string => (text.length > max ? `${text.slice(0, max - 1)}\u2026` : text)

  /** Promueve UN mensaje de la cola hacia la sesión (uno por idle). */
  async function drainPromote(sessionID: string): Promise<void> {
    if (promotingNow !== null) return
    if (!qstate.alwaysOn || qstate.stopped) return
    const entry = promoteOne(qstate, sessionID)
    if (!entry) return
    saveQueue()
    promotingNow = sessionID
    try {
      const res = await client.session.prompt({
        path: { id: sessionID },
        body: { parts: [{ type: "text", text: entry.text }] },
      })
      const resData = res as unknown as { data?: { id?: unknown } }
      if (typeof resData?.data?.id === "string") recentDrainIds.set(resData.data.id, Date.now())
      pruneDrainIds()
      await toast(CONFIG.logTag, `Enviado de la cola: ${preview(entry.text)}`, "success")
    } catch {
      // Devolver al frente para reintentar en el próximo idle (no perderlo)
      qstate.entries = [entry, ...qstate.entries].slice(-CONFIG.maxEntries)
      saveQueue()
      await toast(CONFIG.logTag, `No pude enviarlo; reintentaré en el próximo idle`, "error")
    } finally {
      promotingNow = null
    }
  }

  async function handleQueueCommand(sessionID: string, rawArgs: string): Promise<void> {
    const { op, text, all } = parseQueueArgs(rawArgs)
    switch (op) {
      case "list": {
        const items = listOf(qstate, sessionID)
        if (items.length === 0) {
          await toast(CONFIG.logTag, "Cola vacía", "info")
          break
        }
        const lines = items.slice(0, 3).map((e, i) => `${i + 1}. ${preview(e.text)}`)
        const more = items.length > 3 ? ` (+${items.length - 3} más)` : ""
        await toast(CONFIG.logTag, lines.join("\n") + more, "info")
        break
      }
      case "front": {
        const f = frontOf(qstate, sessionID)
        if (!f) await toast(CONFIG.logTag, "Sin pendientes en la cola", "info")
        else await toast(CONFIG.logTag, `Siguiente: ${preview(f.text)}`, "info")
        break
      }
      case "now": {
        if (!text) {
          await toast(CONFIG.logTag, "/queue now <texto>: envía ya o pone el primero.", "info")
          break
        }
        if (qstate.stopped) {
          await toast(CONFIG.logTag, "Cola pausada: usa /queue start", "warning")
          break
        }
        if (busySessions.has(sessionID)) {
          const entry = enqueueText(qstate, sessionID, text, CONFIG.maxEntries)
          // enqueueText añade al final: mover al frente SIN duplicar
          qstate.entries = [entry, ...qstate.entries.filter((e) => e.id !== entry.id)].slice(0, CONFIG.maxEntries)
          saveQueue()
          await toast(CONFIG.logTag, "Sesión ocupada: encolado en primera posición", "warning")
        } else {
          promotingNow = sessionID
          try {
            await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text }] } })
          } finally {
            promotingNow = null
          }
          await toast(CONFIG.logTag, "Enviado", "success")
        }
        break
      }
      case "stop": {
        qstate.stopped = true
        saveQueue()
        await toast(CONFIG.logTag, "Cola pausada: no se encolará ni enviará nada.", "warning")
        break
      }
      case "start": {
        qstate.stopped = false
        saveQueue()
        await toast(CONFIG.logTag, "Cola reanudada", "success")
        break
      }
      case "flush": {
        const n = flushFor(qstate, all ? null : sessionID)
        saveQueue()
        await toast(CONFIG.logTag, all ? `Flush: ${n} descartados de todas las sesiones` : `Flush: ${n} descartados de esta sesión`, "info")
        break
      }
      default:
        await toast(CONFIG.logTag, CONFIG.helpText, "info")
    }
    await log(`/queue ${rawArgs.trim() || "(help)"}`)
  }

  /** Cachea si una sesión es subagente (parentID) para no encolar sus hijos. */
  const knownSubagent = new Map<string, boolean>()
  async function isSubagentRoot(sessionID: string): Promise<boolean> {
    if (knownSubagent.has(sessionID)) return knownSubagent.get(sessionID)!
    try {
      const s = await client.session.get({ path: { id: sessionID } })
      const isSub = !!s.data?.parentID
      knownSubagent.set(sessionID, isSub)
      return isSub
    } catch {
      return false
    }
  }

  const hiddenPart = (sessionID: string, messageID: string | undefined): Part => ({
    id: makeId(),
    sessionID,
    messageID: messageID ?? "",
    type: "text",
    text: CONFIG.hiddenText,
    synthetic: true,
    ignored: true,
  })

  return {
    "chat.message": async ({ sessionID, messageID }, output) => {
      try {
        // Mensajes de/para subagentes: no encolar ni consumir
        if (await isSubagentRoot(sessionID)) return
        const isDrain = promotingNow === sessionID || isDrainedRecently(sessionID, messageID)
        // Lo que reinyectó el plugin de Telegram: ya pasó por SU cola
        const fromTelegram = (output.parts ?? []).some(
          (p) => p.type === "text" && !!p.metadata && p.metadata.via === "telegram-answers",
        )
        if (isDrain || fromTelegram) return

        const userText = (output.parts ?? [])
          .filter((p): p is Extract<Part, { type: "text" }> => p.type === "text" && !!p.text && !p.synthetic && !p.ignored)
          .map((p) => p.text)
          .join("\n")
          .trim()
        if (!userText) return

        // Comando leading en texto plano (fallback si /queue no llegó como comando)
        if (isQueueCommand(userText)) {
          const rest = userText.replace(/^\s*\/queue\s*/, "")
          output.parts = [hiddenPart(sessionID, messageID)]
          await handleQueueCommand(sessionID, rest)
          return
        }

        // Captura: por defecto TODO lo escrito en ocupado se encola
        // (CONFIG.captureAllBusy); el sufijo " /queue" sigue válido y se
        // limpia para no ensuciar la cola.
        if (!qstate.alwaysOn || qstate.stopped || !busySessions.has(sessionID)) return
        const { text: cleaned, queueIt } = extractTrailingQueue(userText)
        if (!queueIt && !CONFIG.captureAllBusy) return
        const body = (queueIt ? cleaned : userText).trim()
        output.parts = [hiddenPart(sessionID, messageID)]
        if (body) {
          enqueueText(qstate, sessionID, body, CONFIG.maxEntries)
          saveQueue()
          await toast(
            CONFIG.logTag,
            body.length <= 45 ? `Encolado: ${body}` : `Encolado (${listOf(qstate, sessionID).length} pendientes)`,
            "info",
          )
          await log(`encolado${queueIt ? " (trailing /queue)" : " (auto)"}: ${preview(body)}`)
        } else {
          await toast(CONFIG.logTag, "Nada que encolar (mensaje vacío)", "info")
        }
      } catch (err) {
        console.warn(`[${CONFIG.logTag}] chat.message error:`, err)
      }
    },

    "command.execute.before": async ({ command, sessionID, arguments: args }, output) => {
      try {
        if (command !== "queue") return
        output.parts = [hiddenPart(sessionID, undefined)]
        await handleQueueCommand(sessionID, args ?? "")
      } catch (err) {
        console.warn(`[${CONFIG.logTag}] command.execute.before error:`, err)
      }
    },

    event: async ({ event }) => {
      try {
        const etype = event.type as string
        const props = (event.properties ?? {}) as Record<string, unknown>
        const sessionID = typeof props.sessionID === "string" ? props.sessionID : ""

        if (etype === "session.status") {
          const st = props.status as { type?: string } | null | undefined
          if (!sessionID || !st || typeof st.type !== "string") return
          if (await isSubagentRoot(sessionID)) return
          if (st.type === "busy") busySessions.add(sessionID)
          else if (st.type === "idle") {
            busySessions.delete(sessionID)
            await drainPromote(sessionID)
          }
          return
        }

        if (etype === "session.idle") {
          if (!sessionID) return
          if (await isSubagentRoot(sessionID)) return
          busySessions.delete(sessionID)
          await drainPromote(sessionID)
        }
      } catch (err) {
        console.warn(`[${CONFIG.logTag}] event error:`, err)
      }
    },
  }
}

export { CONFIG }
export default plugin