import type { Hooks, Plugin, PluginInput, PluginModule } from "@opencode-ai/plugin"
import { spawn } from "node:child_process"
import { randomUUID } from "node:crypto"
import { appendFileSync, existsSync, readFileSync, readdirSync, rmSync, statSync, unlinkSync, writeFileSync } from "node:fs"
import { basename, dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

export const PLUGIN_ID = "opencode-auto-session"
export const DUMP_STEM = ".opencode_session_dump"
export const DUMP_FILENAME = `${DUMP_STEM}.md`
/** Script de aviso de Windows. */
export const NOTIFY_SCRIPT_PS1 = "limit-notify.ps1"
/** Script de aviso de Linux/macOS. */
export const NOTIFY_SCRIPT_SH = "limit-notify.sh"
/** Nombre del log donde el aviso queda registrado aunque no haya ventana. */
export const NOTIFY_LOG = "limit-notify.log"
/** Alias historico (Windows) conservado para compatibilidad. */
export const NOTIFY_SCRIPT = NOTIFY_SCRIPT_PS1
export const DUMP_TITLE = "CONTEXTO DE SESION ANTERIOR (RECUPERADO AUTOMATICAMENTE)"
export const CONTEXT_HEADER = "ARCHIVOS DE SESION PREVIOS DEL REPO (leidos automaticamente):"
/** Texto de la parte oculta que neutraliza el turno del comando. */
export const HIDDEN_COMMAND_TEXT = "..."

/**
 * ── CONFIGURACION EDITABLE ─────────────────────────────────────────────
 */
export const CONFIG = {
  /** Adjuntar al prompt los archivos de sesion del repo al abrir una sesion nueva. */
  injectRepoContext: true,
  /** Ejecutar el script de aviso del SO (limit-notify.ps1 / limit-notify.sh). */
  runNotifyScript: true,
  /** Mostrar el aviso tambien dentro de la sesion (toast), no solo en la ventana. */
  notifyInSession: true,
  /** Segundos que la ventana del aviso permanece visible. */
  notifyKeepOpenSeconds: 20,
  /** Al inyectar contexto, borrar la cabecera del dump (Motivo/429) para que un
   *  error viejo no vuelva a entrar en el prompt y la sesion "parezca" limitada. */
  stripLimitFromInjection: true,
  /** Nombres de archivo que cuentan como "archivo de sesion".
   *  Por defecto solo los dumps de este plugin; añade tus patrones aqui. */
  sessionFilePatterns: [/^\.opencode_session_dump.*\.md$/i],
  /** Directorios que nunca se recorren */
  skipDirs: ["node_modules", ".git", "dist", "build", "out", ".venv", "__pycache__", ".pytest_cache"],
  /** Topes de seguridad: no inflar el contexto ni leer archivos enormes */
  maxFiles: 5,
  maxCharsPerFile: 20000,
  maxTotalChars: 60000,
  /** Tope del bloque que se inyecta en el prompt (mas bajo: se paga en tokens). */
  maxInjectChars: 12000,
  /** No volver a guardar el dump de la misma sesion dentro de esta ventana (ms). */
  dumpDebounceMs: 5000,
  /** Dumps que se conservan en el proyecto (el resto, los mas viejos, se borran). */
  dumpKeep: 20,
  /** Error sintetico que usa `/autosession simulate` para recorrer todo el camino del limite. */
  simulatedError: { type: "provider-error", message: "Free usage limit exceeded (simulado)", status: 429 },
}

/** Patrones que indican limite/cuota del proveedor. */
export const LIMIT_PATTERNS: RegExp[] = [
  /free usage/i,
  /free tier/i,
  /free limit/i,
  /usage limit/i,
  /quota/i,
  /rate limit/i,
  /too many requests/i,
  /insufficient (?:account )?(?:balance|credits?|funds?|quota)/i,
  /out of credits/i,
  /retrying in/i,
  /\b429\b/,
  /\b402\b/,
]

/** Codigos HTTP que equivalen a limite/cuota. */
export const LIMIT_STATUS = [429, 402]

/** Vista estructural de un valor desconocido: evita acoplarse a los tipos del SDK. */
export function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null) return null
  return value as Record<string, unknown>
}

/** Texto plano de un error/valor para logs y motivos. */
export function describe(value: unknown): string {
  if (typeof value === "string") return value
  if (value instanceof Error) return value.message
  try {
    return JSON.stringify(value) ?? String(value)
  } catch {
    return String(value)
  }
}

/**
 * Todo el texto de un error del proveedor. Cubre las tres formas que entrega el
 * runtime: el error plano (`type`, `message`, `status`), el error envuelto de
 * `session.error` (`{ name, data: { message } }`) y el objeto de `session.status`
 * con `type: "retry"` (`{ type, attempt, message, next }`).
 */
export function limitHaystack(error: unknown): string {
  const record = asRecord(error)
  if (!record) return typeof error === "string" ? error : ""
  const parts: string[] = []
  for (const key of ["type", "name", "message", "status"]) {
    const value = record[key]
    if (value !== undefined && value !== null) parts.push(String(value))
  }
  for (const key of ["data", "error"]) {
    const nested = asRecord(record[key])
    if (nested && nested.message !== undefined && nested.message !== null) parts.push(String(nested.message))
  }
  const response = asRecord(record.response)
  if (response && typeof response.body === "string") parts.push(response.body)
  return parts.join(" ")
}

export function isLimitErrorText(haystack: string, patterns: RegExp[] = LIMIT_PATTERNS): boolean {
  return patterns.some((re) => re.test(haystack))
}

/** True si el error del proveedor es un limite/cuota. */
export function isLimitError(error: unknown): boolean {
  const record = asRecord(error)
  const status = record && typeof record.status === "number" ? record.status : undefined
  if (status !== undefined && LIMIT_STATUS.includes(status)) return true
  return isLimitErrorText(limitHaystack(error))
}

/** Lineas de cabecera del dump (metadatos, no conversacion). */
export const DUMP_META_LINE = /^-\s*(Guardado|Motivo|Sesion)\s*:/i

/**
 * Limpia el texto de un dump antes de inyectarlo en el prompt: fuera la cabecera
 * de metadatos (`- Motivo: ... 429`) y cualquier linea que case con los patrones
 * de limite. Sin esto, un error de cuota viejo vuelve a entrar en el system
 * prompt de cada sesion nueva y la sesion "parece" rate-limited hasta que se
 * borra el dump a mano.
 */
export function scrubInjectedContext(text: string, patterns: RegExp[] = LIMIT_PATTERNS): string {
  return text
    .split(/\r?\n/)
    .filter((line) => !DUMP_META_LINE.test(line) && !isLimitErrorText(line, patterns))
    .join("\n")
}

/** True si el nombre de archivo coincide con algun patron de archivo de sesion. */
export function matchesSessionFile(name: string, patterns: RegExp[] = CONFIG.sessionFilePatterns): boolean {
  return patterns.some((re) => re.test(name))
}

/** True si el directorio debe saltarse en el recorrido. */
export function isSkippedDir(name: string, skipDirs: string[] = CONFIG.skipDirs): boolean {
  return skipDirs.includes(name)
}

/**
 * Recorre `root` buscando archivos cuyo nombre case con `patterns`.
 * Devuelve rutas absolutas, ordenadas, sin entrar en `skipDirs`.
 */
export function collectSessionFiles(
  root: string,
  patterns: RegExp[] = CONFIG.sessionFilePatterns,
  skipDirs: string[] = CONFIG.skipDirs,
  maxFiles: number = CONFIG.maxFiles,
): string[] {
  const found: string[] = []
  const walk = (dir: string, depth: number): void => {
    if (found.length >= maxFiles || depth > 12) return
    let entries: string[]
    try {
      entries = readdirSync(dir)
    } catch {
      return
    }
    for (const name of entries.sort()) {
      if (found.length >= maxFiles) return
      const full = join(dir, name)
      let isDir = false
      try {
        isDir = statSync(full).isDirectory()
      } catch {
        continue
      }
      if (isDir) {
        if (isSkippedDir(name, skipDirs)) continue
        walk(full, depth + 1)
      } else if (matchesSessionFile(name, patterns)) {
        found.push(full)
      }
    }
  }
  walk(root, 0)
  return found
}

/**
 * Compone el bloque de contexto a partir de rutas de archivo. Aplica los topes
 * por archivo y totales; si un archivo no se puede leer, lo omite.
 */
export function buildRepoContext(
  files: string[],
  read: (path: string) => string,
  maxCharsPerFile: number = CONFIG.maxCharsPerFile,
  maxTotalChars: number = CONFIG.maxTotalChars,
): string {
  let out = ""
  for (const file of files) {
    if (out.length >= maxTotalChars) break
    let body: string
    try {
      body = read(file)
    } catch {
      continue
    }
    const trimmed = body.trim()
    if (!trimmed) continue
    const capped = trimmed.length > maxCharsPerFile ? `${trimmed.slice(0, maxCharsPerFile)}\n[...recortado...]` : trimmed
    const block = `\n\n## ${file}\n${capped}`
    out += block.length > maxTotalChars - out.length ? block.slice(0, Math.max(0, maxTotalChars - out.length)) : block
  }
  return out
}

export interface DumpMeta {
  title?: string
  savedAt?: string
  reason?: string
  sessionID?: string
}

/**
 * Convierte lo que devuelve `client.session.messages` (`{ info, parts }[]`) a la
 * forma plana que consume `formatDump`. El texto de cada mensaje son sus partes
 * `text` unidas por saltos de linea.
 */
export function toDumpMessages(history: readonly unknown[]): { type: string; text: string }[] {
  const out: { type: string; text: string }[] = []
  for (const raw of history) {
    const item = asRecord(raw)
    if (!item) continue
    const info = asRecord(item.info) ?? item
    const role = typeof info.role === "string" ? info.role : typeof item.type === "string" ? item.type : ""
    const text = extractText(item)
    if (!role || !text.trim()) continue
    out.push({ type: role, text })
  }
  return out
}

/** Texto de un mensaje, sea `parts[]` (API), `content[]` (SDK) o `text` (plano). */
function extractText(item: Record<string, unknown>): string {
  const collect = (chunks: unknown[]): string =>
    chunks
      .map((part) => {
        const record = asRecord(part)
        return record && record.type === "text" && typeof record.text === "string" ? record.text : ""
      })
      .filter((chunk) => chunk.length > 0)
      .join("\n")
  for (const key of ["parts", "content"]) {
    const chunks = item[key]
    if (Array.isArray(chunks)) {
      const text = collect(chunks)
      if (text) return text
    }
  }
  return typeof item.text === "string" ? item.text : ""
}

/**
 * Markdown del historial. Acepta tanto los mensajes planos (`{ type, text }`,
 * salida de `toDumpMessages`) como la forma del SDK (`{ type/role, content[] }`).
 */
export function formatDump(messages: readonly object[], meta: DumpMeta = {}): string {
  let out = `# ${meta.title ?? DUMP_TITLE}\n\n`
  const details: string[] = []
  if (meta.savedAt) details.push(`- Guardado: ${meta.savedAt}`)
  if (meta.reason) details.push(`- Motivo: ${meta.reason}`)
  if (meta.sessionID) details.push(`- Sesion: ${meta.sessionID}`)
  if (details.length > 0) out += `${details.join("\n")}\n\n`
  for (const raw of messages) {
    const message = asRecord(raw)
    if (!message) continue
    const kind =
      typeof message.type === "string" ? message.type : typeof message.role === "string" ? message.role : ""
    if (!kind) continue
    let text = ""
    if (typeof message.text === "string") {
      text = message.text
    } else if (kind === "assistant") {
      const content = Array.isArray(message.content) ? message.content : []
      text = content
        .map((part) => {
          const record = asRecord(part)
          return record && record.type === "text" && typeof record.text === "string" ? record.text : ""
        })
        .filter((chunk) => chunk.length > 0)
        .join("\n")
    } else if (typeof message.content === "string") {
      text = message.content
    }
    const trimmed = text.trim()
    if (!trimmed) continue
    out += `### ${kind.toUpperCase()}:\n${trimmed}\n\n---\n\n`
  }
  return out
}

/**
 * Sufijo unico del dump. Se usa el id de la sesion (unico y estable: volver a
 * volcar la misma sesion actualiza SU archivo) y, si no hay, un UUID.
 */
export function dumpIdFor(sessionID: string, uuid: () => string = randomUUID): string {
  const clean = String(sessionID ?? "").replace(/[^A-Za-z0-9_-]/g, "").slice(0, 40)
  return clean.length >= 6 ? clean : uuid().replace(/-/g, "").slice(0, 12)
}

/** Nombre del dump de una sesion: un archivo por sesion, sin sobrescribirse. */
export function dumpFileName(sessionID: string, uuid: () => string = randomUUID): string {
  return `${DUMP_STEM}-${dumpIdFor(sessionID, uuid)}.md`
}

/**
 * Ruta del dump. Sin `sessionID` devuelve el nombre base historico (el que
 * usaba la version que sobrescribia todo); con el, un archivo por sesion.
 */
export function dumpPathFor(directory: string, sessionID?: string): string {
  return join(directory, sessionID ? dumpFileName(sessionID) : DUMP_FILENAME)
}

/** Dumps existentes en el proyecto, del mas nuevo al mas viejo. */
export function listDumps(directory: string): string[] {
  try {
    return readdirSync(directory)
      .filter((name) => /^\.opencode_session_dump.*\.md$/i.test(name))
      .map((name) => join(directory, name))
      .sort((a, b) => {
        try {
          return statSync(b).mtimeMs - statSync(a).mtimeMs
        } catch {
          return 0
        }
      })
  } catch {
    return []
  }
}

/**
 * Conserva los `keep` dumps mas recientes: un archivo por sesion creceria sin
 * limite en un proyecto con muchas sesiones.
 */
export function pruneDumps(directory: string, keep: number): number {
  if (!Number.isFinite(keep) || keep <= 0) return 0
  const extra = listDumps(directory).slice(keep)
  let removed = 0
  for (const file of extra) {
    try {
      unlinkSync(file)
      removed++
    } catch {
      // archivo en uso o sin permisos: se deja
    }
  }
  return removed
}

/**
 * Directorio del proyecto. El runtime entrega `directory` en el `PluginInput`;
 * el resto de las formas se aceptan para no acoplarse a una release concreta.
 */
export function projectDirectory(context: unknown): string {
  const record = asRecord(context)
  const location = asRecord(record?.location)
  const project = asRecord(record?.project) ?? asRecord(location?.project)
  const candidate = record?.directory ?? project?.directory ?? location?.directory
  return typeof candidate === "string" && candidate.length > 0 ? candidate : process.cwd()
}

/** Script de aviso segun el sistema operativo. */
export function notifyScriptName(platform: string = process.platform): string {
  return platform === "win32" ? NOTIFY_SCRIPT_PS1 : NOTIFY_SCRIPT_SH
}

/**
 * Candidatos del script de aviso del SO: junto al .ts (dev) y en la subcarpeta
 * con el id del plugin (instalacion global).
 */
export function notifyScriptCandidates(metaUrl: string, platform: string = process.platform): string[] {
  const dir = dirname(fileURLToPath(new URL(metaUrl)))
  const name = notifyScriptName(platform)
  return [join(dir, name), join(dir, PLUGIN_ID, name)]
}

/** Ruta del script de aviso del SO, resuelta desde el modulo que lo carga. */
export function notifyScriptFor(metaUrl: string, platform: string = process.platform): string {
  const candidates = notifyScriptCandidates(metaUrl, platform)
  return candidates.find((candidate) => existsSync(candidate)) ?? candidates[0]
}

/**
 * Argumentos del lanzador.
 * - Windows: `cmd /c start "" powershell ...` abre una consola propia. Un ps1
 *   lanzado en segundo plano sin consola imprime a la nada (el aviso nunca se
 *   veia).
 * - Linux/macOS: `/bin/sh <script> <session> <dump>`; el propio script abre una
 *   terminal si no la tiene y siempre deja el aviso en `limit-notify.log`.
 */
export function notifyArgs(
  scriptPath: string,
  sessionID: string,
  dumpFile: string,
  platform: string = process.platform,
): string[] {
  if (platform === "win32") {
    return [
      "/c",
      "start",
      "",
      "powershell.exe",
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      scriptPath,
      "-SessionID",
      sessionID,
      "-DumpFile",
      dumpFile,
    ]
  }
  return [scriptPath, sessionID, dumpFile]
}

export function notifyCommandFor(platform: string = process.platform): string {
  return platform === "win32" ? "cmd.exe" : "/bin/sh"
}

/** Entorno que recibe el script (los .sh usan variables si no reciben argumentos). */
export function notifyEnv(sessionID: string, dumpFile: string): NodeJS.ProcessEnv {
  return {
    ...process.env,
    OPENCODE_LIMIT_SESSION: sessionID,
    OPENCODE_LIMIT_DUMP: dumpFile,
    OPENCODE_LIMIT_KEEP_OPEN: String(CONFIG.notifyKeepOpenSeconds),
  }
}

/**
 * Lanza el script de aviso del SO en segundo plano (fire-and-forget): muestra
 * LIMITE GRATIS ALCANZADO en su propia ventana sin bloquear el servidor.
 */
export function runLimitNotify(scriptPath: string, sessionID: string, dumpFile: string, platform: string = process.platform): void {
  if (!CONFIG.runNotifyScript) return
  try {
    const child = spawn(notifyCommandFor(platform), notifyArgs(scriptPath, sessionID, dumpFile, platform), {
      detached: true,
      stdio: "ignore",
      windowsHide: false,
      env: notifyEnv(sessionID, dumpFile),
    })
    // spawn falla de forma asincrona (ENOENT): sin este handler el aviso
    // desaparecia sin dejar rastro (era el caso de Linux sin pwsh instalado).
    child.on("error", (error) => console.warn(`[${PLUGIN_ID}] notify error: ${describe(error)}`))
    child.unref()
  } catch (error) {
    console.warn(`[${PLUGIN_ID}] notify error: ${describe(error)}`)
  }
}

/** Ruta del log de avisos, junto al dump del proyecto. */
export function notifyLogPath(dumpFile: string): string {
  return join(dirname(dumpFile), NOTIFY_LOG)
}

/** Registro durable del aviso (independiente de que se abra o no una ventana). */
export function appendNotifyLog(dumpFile: string, sessionID: string, reason: string): void {
  try {
    appendFileSync(notifyLogPath(dumpFile), `${new Date().toISOString()} LIMITE GRATIS ALCANZADO sesion=${sessionID} motivo=${reason.slice(0, 200)}\n`)
  } catch (error) {
    console.warn(`[${PLUGIN_ID}] notify log error: ${describe(error)}`)
  }
}

/** Borra los dumps del proyecto. Devuelve cuantos elimino. */
export function clearSessionFiles(
  root: string,
  patterns: RegExp[] = CONFIG.sessionFilePatterns,
  skipDirs: string[] = CONFIG.skipDirs,
): number {
  const files = collectSessionFiles(root, patterns, skipDirs, Number.MAX_SAFE_INTEGER)
  let removed = 0
  for (const file of files) {
    try {
      unlinkSync(file)
      removed += 1
    } catch {
      // sin permisos o ya borrado: se ignora
    }
  }
  return removed
}

/**
 * Superficie minima del cliente que usa el plugin. Se declara aqui (en vez de
 * importar el tipo del SDK) para que el plugin no dependa de la version del SDK
 * y para poder inyectar un doble en los tests.
 */
export interface SessionClient {
  session: {
    messages: (args: { path: { id: string } }) => Promise<unknown>
  }
  tui: {
    showToast: (args: { body: { title: string; message: string; variant?: string; duration?: number } }) => Promise<unknown>
  }
}

/** Ids internos (entradas de cola, claves): no los valida el runtime. */
export function makeId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

const ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

/**
 * Id de PARTE. El runtime lo decodifica al crear el mensaje del comando y exige
 * el prefijo `prt` (con cualquier otro aborta con 500:
 * `Expected a string starting with "prt"`). Mismo formato que sus ids: prefijo,
 * guion bajo y 26 caracteres base62.
 */
export function partId(random: () => number = Math.random): string {
  let out = "prt_"
  for (let i = 0; i < 26; i++) {
    out += ID_ALPHABET[Math.floor(random() * ID_ALPHABET.length) % ID_ALPHABET.length]
  }
  return out
}

/** Parte oculta que reemplaza el prompt del comando: el modelo no llega a verlo. */
export function hiddenPart(sessionID: string): Record<string, unknown> {
  return {
    id: partId(),
    sessionID,
    messageID: "",
    type: "text",
    text: HIDDEN_COMMAND_TEXT,
    synthetic: true,
    ignored: true,
  }
}

/**
 * Sustituye las partes del comando EN SU SITIO. El runtime conserva su propia
 * referencia al array y es ESA la que pasa al modelo: reasignar `output.parts`
 * (por ejemplo `output.parts = [x]`) no cambia nada y el prompt del comando
 * acaba llegando al modelo. Solo mutar el array surte efecto.
 */
export function replaceParts(output: { parts: unknown[] }, part: unknown): void {
  output.parts.splice(0, output.parts.length, part)
}

/**
 * Nombre del comando de archivo que expone `/autosession` en la paleta. El
 * runtime construye la lista de comandos a partir de `<config>/commands/*.md`;
 * un comando registrado en runtime no aparece ahi.
 */
export const COMMAND_NAME = "autosession"

/**
 * Plugin de OpenCode (API clasica): `{ id, server }`. Guarda el historial al
 * alcanzar el limite y adjunta los dumps del repo al abrir una sesion nueva.
 */
export async function server(input: PluginInput): Promise<Hooks> {
  const warn = (message: string): void => {
    try {
      console.warn(`[${PLUGIN_ID}] ${message}`)
    } catch {
      // sin consola: no hay nada mas que hacer
    }
  }

  // Nunca lanzar: un throw aparece como "plugin failed" y desactiva el plugin.
  try {
    const client = input.client as unknown as SessionClient
    const directory = projectDirectory(input)
    const platform = process.platform
    /** Un dump por sesion: sin esto, cada sesion sobrescribia al anterior. */
    const dumpPaths = new Map<string, string>()
    const dumpFileFor = (sessionID: string): string => {
      const known = dumpPaths.get(sessionID)
      if (known) return known
      const path = dumpPathFor(directory, sessionID)
      dumpPaths.set(sessionID, path)
      return path
    }
    const notifyScript = notifyScriptFor(import.meta.url, platform)

    /** Sesiones ya avisadas: el aviso se dispara una vez por sesion. */
    const notified = new Set<string>()
    /** Ultimo dump por sesion (debounce de eventos repetidos del mismo fallo). */
    const lastDump = new Map<string, number>()
    /** Sesiones con inyeccion forzada por `/autosession inject`. */
    const armedInjection = new Set<string>()
    /** Sesiones que ya recibieron el contexto (una inyeccion por sesion). */
    const injectedSessions = new Set<string>()
    /** Subsesiones (parentID): no heredan el contexto de sesiones anteriores. */
    const subagentSessions = new Set<string>()
    /** Cache del bloque de contexto; se invalida al escribir un dump nuevo. */
    let repoContextCache: string | null = null

    const toast = async (title: string, message: string, variant: "info" | "success" | "warning" | "error" = "info"): Promise<void> => {
      warn(`${title}: ${message}`)
      try {
        await client.tui.showToast({ body: { title, message, variant, duration: 6000 } })
      } catch (error) {
        warn(`toast fallo: ${describe(error)}`)
      }
    }

    function repoContextFor(): string {
      if (repoContextCache !== null) return repoContextCache
      let block = ""
      try {
        if (CONFIG.injectRepoContext) {
          const files = collectSessionFiles(directory)
          if (files.length > 0) {
            const read = (path: string): string => {
              const raw = readFileSync(path, "utf-8")
              return CONFIG.stripLimitFromInjection ? scrubInjectedContext(raw) : raw
            }
            const body = buildRepoContext(files, read, CONFIG.maxCharsPerFile, CONFIG.maxInjectChars)
            if (body) block = `${CONTEXT_HEADER}\n${body}`
          }
        }
      } catch (error) {
        warn(`repo scan error: ${describe(error)}`)
      }
      repoContextCache = block
      return block
    }

    /** Historial de la sesion como mensajes planos, tolerante a fallos de la API. */
    async function readHistory(sessionID: string): Promise<{ type: string; text: string }[]> {
      try {
        const response = asRecord(await client.session.messages({ path: { id: sessionID } }))
        const data = response && Array.isArray(response.data) ? response.data : []
        return toDumpMessages(data)
      } catch (error) {
        warn(`no pude leer el historial de ${sessionID}: ${describe(error)}`)
        return []
      }
    }

    /** True si la sesion ya tuvo al menos una respuesta del asistente. */
    async function hasAssistantReply(sessionID: string): Promise<boolean> {
      const history = await readHistory(sessionID)
      return history.some((message) => message.type === "assistant")
    }

    async function dumpSession(sessionID: string, reason: string, options: { force?: boolean } = {}): Promise<void> {
      const now = Date.now()
      const previous = lastDump.get(sessionID)
      if (!options.force && previous !== undefined && now - previous < CONFIG.dumpDebounceMs) return
      lastDump.set(sessionID, now)
      const dumpFile = dumpFileFor(sessionID)
      const messages = await readHistory(sessionID)
      const body = formatDump(messages, {
        savedAt: new Date().toISOString(),
        reason,
        sessionID,
      })
      try {
        writeFileSync(dumpFile, body, "utf-8")
      } catch (error) {
        warn(`no pude escribir ${basename(dumpFile)}: ${describe(error)}`)
        return
      }
      repoContextCache = null
      const pruned = pruneDumps(directory, CONFIG.dumpKeep)
      warn(
        `limite detectado (${reason.slice(0, 120)}): dump de ${messages.length} mensajes en ${basename(dumpFile)}` +
          (pruned > 0 ? ` (${pruned} dump(s) viejo(s) borrado(s))` : ""),
      )
      appendNotifyLog(dumpFile, sessionID, reason)
      if (!notified.has(sessionID)) {
        notified.add(sessionID)
        runLimitNotify(notifyScript, sessionID, dumpFile, platform)
        if (CONFIG.notifyInSession) {
          await toast(
            "LIMITE GRATIS ALCANZADO",
            [
              `Sesion: ${sessionID}`,
              `Dump: ${basename(dumpFile)}`,
              `Log: ${notifyLogPath(dumpFile)}`,
              "Limpia con /autosession reset si el limite se queda pegado.",
            ].join(" | "),
            "warning",
          )
        }
      }
    }

    /**
     * Camino completo del limite: deteccion (`isLimitError`) -> dump -> aviso.
     * Lo usan tanto los eventos reales como `/autosession simulate`.
     */
    async function handleFailure(type: string, sessionID: string, error: unknown, options: { force?: boolean } = {}): Promise<boolean> {
      if (!isLimitError(error)) return false
      await dumpSession(sessionID, `${type}: ${describe(error)}`, options)
      return true
    }

    function statusText(sessionID: string): string {
      const files = collectSessionFiles(directory)
      const armed = armedInjection.has(sessionID) ? "si" : "no"
      return [
        `${PLUGIN_ID}`,
        `Proyecto: ${directory}`,
        `Dumps: ${listDumps(directory).length} (sesion actual: ${basename(dumpFileFor(sessionID))})`,
        `Archivos de sesion en el repo: ${files.length}`,
        `Inyeccion forzada: ${armed}`,
        `Aviso (${platform}): ${notifyScript}`,
        `Comandos: /autosession status | dump | files | inject | simulate | reset`,
      ].join(" | ")
    }

    /** Verbos de `/autosession`. La respuesta va a un toast (no hay canal in-session). */
    async function handleCommand(sessionID: string, rest: string): Promise<void> {
      const verb = (rest.split(/\s+/)[0] ?? "").toLowerCase()
      const arg = rest.slice(verb.length).trim()
      try {
        if (verb === "dump") {
          await dumpSession(sessionID, "manual /autosession dump", { force: true })
          await toast("autosession", `Dump guardado en ${basename(dumpFileFor(sessionID))}.`, "success")
          return
        }
        if (verb === "files") {
          const files = collectSessionFiles(directory)
          await toast(
            "autosession",
            files.length === 0
              ? "Sin archivos de sesion en el repo."
              : `${files.length} archivo(s): ${files.map((file) => file).join(", ")}`,
          )
          return
        }
        if (verb === "inject" || verb === "restore") {
          armedInjection.add(sessionID)
          await toast("autosession", "Contexto armado: se inyectara en el proximo request de esta sesion.", "success")
          return
        }
        if (verb === "reset" || verb === "clear" || verb === "clean") {
          // Desatasca un "limite pegado": borra los dumps que se reinyectan en
          // cada sesion nueva y reinicia los avisos por sesion.
          const removed = clearSessionFiles(directory)
          repoContextCache = null
          notified.clear()
          lastDump.clear()
          dumpPaths.clear()
          injectedSessions.clear()
          await toast(
            "autosession",
            removed > 0
              ? `${removed} archivo(s) de sesion borrados. Las sesiones nuevas ya no reciben el contexto viejo.`
              : "Sin archivos de sesion que borrar.",
            "success",
          )
          return
        }
        if (verb === "simulate" || verb === "simular" || verb === "test" || verb === "probar") {
          // Simula el limite sin gastar cuota: mismo isLimitError, mismo dump,
          // mismo script de aviso del SO.
          const error = arg ? { type: "provider-error", message: arg } : { ...CONFIG.simulatedError }
          const handled = await handleFailure("session.execution.failed (simulado)", sessionID, error, { force: true })
          await toast(
            "autosession",
            handled
              ? [
                  "Simulacion ejecutada.",
                  `Error probado: ${describe(error)}`,
                  `Dump: ${basename(dumpFileFor(sessionID))}`,
                  `Log: ${notifyLogPath(dumpFileFor(sessionID))}`,
                  "Limpia con /autosession reset antes de seguir.",
                ].join(" | ")
              : `El error simulado NO coincide con los patrones de limite: ${describe(error)}`,
            handled ? "success" : "warning",
          )
          return
        }
        await toast("autosession", statusText(sessionID))
      } catch (error) {
        warn(`comando autosession fallo: ${describe(error)}`)
      }
    }

    const hooks: Hooks = {
      event: async ({ event }) => {
        try {
          const record = asRecord(event)
          const type = typeof record?.type === "string" ? record.type : ""
          const properties = asRecord(record?.properties) ?? {}
          const sessionID = typeof properties.sessionID === "string" ? properties.sessionID : ""
          if (!sessionID) return

          if (type === "session.created") {
            const info = asRecord(properties.info)
            const parentID = info && typeof info.parentID === "string" ? info.parentID : ""
            if (parentID) subagentSessions.add(sessionID)
            return
          }

          // `session.status` con `type: "retry"` es el punto mas robusto: trae el
          // mensaje del proveedor y se emite aunque no haya un error terminal.
          if (type === "session.status") {
            const status = asRecord(properties.status)
            if (!status || status.type !== "retry") return
            await handleFailure("session.status retry", sessionID, status)
            return
          }

          if (type === "session.error") {
            await handleFailure(type, sessionID, properties.error)
            return
          }

          if (type === "session.execution.failed") {
            await handleFailure(type, sessionID, properties.error ?? properties)
          }
        } catch (error) {
          warn(`hook event fallo: ${describe(error)}`)
        }
      },

      // Contexto del repo: se adjunta al system prompt de una sesion nueva, una
      // sola vez (o cuando `/autosession inject` lo arma a mano).
      "experimental.chat.system.transform": async (hookInput, output) => {
        try {
          if (!CONFIG.injectRepoContext) return
          const sessionID = typeof hookInput?.sessionID === "string" ? hookInput.sessionID : ""
          if (!sessionID || !Array.isArray(output?.system)) return
          if (subagentSessions.has(sessionID)) return
          const armed = armedInjection.has(sessionID)
          if (!armed && injectedSessions.has(sessionID)) return
          if (!armed && (await hasAssistantReply(sessionID))) {
            injectedSessions.add(sessionID)
            return
          }
          armedInjection.delete(sessionID)
          const block = repoContextFor()
          injectedSessions.add(sessionID)
          if (!block) return
          output.system.push(block)
          warn(`contexto de repo inyectado en ${sessionID} (${block.length} chars)`)
        } catch (error) {
          warn(`hook system.transform fallo: ${describe(error)}`)
        }
      },

      // `/autosession ...`: reemplaza el prompt por una parte oculta (el modelo
      // no gasta turno) y ejecuta el verbo.
      "command.execute.before": async (hookInput, output) => {
        try {
          if (hookInput?.command !== COMMAND_NAME) return
          const sessionID = typeof hookInput.sessionID === "string" ? hookInput.sessionID : ""
          replaceParts(output as { parts: unknown[] }, hiddenPart(sessionID))
          await handleCommand(sessionID, String(hookInput.arguments ?? "").trim())
        } catch (error) {
          warn(`hook command.execute.before fallo: ${describe(error)}`)
        }
      },
    }

    warn(`activo en ${directory} (dump: ${DUMP_STEM}-<sesion>.md, aviso: ${notifyScript})`)
    return hooks
  } catch (error) {
    warn(`server fallo: ${describe(error)}`)
    return {}
  }
}

const plugin: PluginModule & { server: Plugin } = { id: PLUGIN_ID, server }

export { plugin }
export default plugin
