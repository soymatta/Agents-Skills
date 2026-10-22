// Smoke de opencode-auto-session: logica pura + server() con un PluginInput falso.
// Sin red, sin TUI, sin lanzar el ps1. Ejecutar: npm test
import assert from "node:assert/strict"
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import plugin, {
  COMMAND_NAME,
  CONFIG,
  CONTEXT_HEADER,
  DUMP_FILENAME,
  DUMP_STEM,
  hiddenPart,
  dumpFileName,
  dumpPathFor,
  listDumps,
  partId,
  pruneDumps,
  DUMP_TITLE,
  HIDDEN_COMMAND_TEXT,
  NOTIFY_LOG,
  NOTIFY_SCRIPT,
  NOTIFY_SCRIPT_PS1,
  NOTIFY_SCRIPT_SH,
  PLUGIN_ID,
  buildRepoContext,
  clearSessionFiles,
  collectSessionFiles,
  describe,
  formatDump,
  isLimitError,
  isLimitErrorText,
  isSkippedDir,
  matchesSessionFile,
  notifyArgs,
  notifyCommandFor,
  notifyLogPath,
  notifyScriptFor,
  notifyScriptName,
  projectDirectory,
  scrubInjectedContext,
  server,
  toDumpMessages,
} from "../autosession.ts"

// El test no puede abrir una ventana de PowerShell.
CONFIG.runNotifyScript = false

// ── forma exigida por el cargador de OpenCode (`PluginModule`) ───────────
{
  const definition = plugin
  assert.equal(typeof definition, "object", "default export debe ser un objeto, no una funcion")
  assert.equal(definition.id, PLUGIN_ID)
  assert.equal(typeof definition.server, "function", "necesita id + server")
  assert.equal(definition.setup, undefined, "setup NO es parte del contrato: el loader lanza 'must default export an object with server()'")
  assert.equal(definition.tui, undefined)
  assert.equal(typeof server, "function")
}

// ── deteccion de limite ──────────────────────────────────────────────────
assert.equal(isLimitErrorText('{"message":"Free usage exceeded"}'), true)
assert.equal(isLimitErrorText("retrying in 30s"), true)
assert.equal(isLimitErrorText("Rate Limit hit"), true)
assert.equal(isLimitErrorText("HTTP 429 too many"), true)
assert.equal(isLimitErrorText("quota exceeded for model"), true)
assert.equal(isLimitErrorText("some other error"), false)
assert.equal(isLimitErrorText(""), false)

assert.equal(isLimitError({ message: "Free usage exceeded, subscribe to continue", status: 429 }), true)
assert.equal(isLimitError({ status: 402, message: "payment required" }), true)
assert.equal(isLimitError({ type: "provider_error", response: { body: '{"error":"too many requests"}' } }), true)
assert.equal(isLimitError({ status: 500, message: "internal error" }), false)
assert.equal(isLimitError(undefined), false)
assert.equal(isLimitError("plain string with quota exceeded"), true)

// Las tres formas que entrega el runtime deben llegar a los patrones.
assert.equal(isLimitError({ name: "ProviderError", data: { message: "Insufficient account funds" } }), true, "session.error: {name, data:{message}}")
assert.equal(
  isLimitError({ type: "retry", attempt: 2, message: "Upstream request failed: Insufficient account funds", next: 1 }),
  true,
  "session.status retry",
)

assert.equal(describe(new Error("boom")), "boom")
assert.equal(describe("hola"), "hola")
assert.equal(describe({ a: 1 }), '{"a":1}')

// ── historial -> dump ────────────────────────────────────────────────────
const conversation = [
  { info: { role: "user" }, parts: [{ type: "text", text: "arregla el bug de sesiones" }] },
  {
    info: { role: "assistant" },
    parts: [{ type: "text", text: "voy a mirarlo" }, { type: "reasoning", text: "SECRETO" }],
  },
]
assert.deepEqual(toDumpMessages(conversation), [
  { type: "user", text: "arregla el bug de sesiones" },
  { type: "assistant", text: "voy a mirarlo" },
])
assert.deepEqual(toDumpMessages([{ type: "user", text: "plano" }]), [{ type: "user", text: "plano" }], "acepta la forma plana")
assert.deepEqual(toDumpMessages([{ type: "assistant", content: [{ type: "text", text: "sdk" }] }]), [
  { type: "assistant", text: "sdk" },
])
assert.deepEqual(toDumpMessages([]), [])
assert.deepEqual(toDumpMessages([{ info: { role: "user" }, parts: [{ type: "reasoning", text: "x" }] }]), [], "sin texto no hay mensaje")

{
  const dump = formatDump(toDumpMessages(conversation), { savedAt: "2026-10-17T00:00:00.000Z", reason: "test", sessionID: "ses_1" })
  assert.ok(dump.startsWith(`# ${DUMP_TITLE}`), "titulo del dump")
  assert.match(dump, /### USER:\narregla el bug de sesiones/)
  assert.match(dump, /### ASSISTANT:\nvoy a mirarlo/)
  assert.match(dump, /- Motivo: test/)
  assert.match(dump, /- Sesion: ses_1/)
  assert.ok(!dump.includes("SECRETO"), "las partes de razonamiento no se guardan")
}

// ── rutas y scripts de aviso (deteccion de SO) ───────────────────────────
assert.equal(DUMP_FILENAME, ".opencode_session_dump.md")
assert.equal(DUMP_STEM, ".opencode_session_dump")
assert.equal(NOTIFY_SCRIPT, "limit-notify.ps1")
assert.equal(NOTIFY_SCRIPT_PS1, "limit-notify.ps1")
assert.equal(NOTIFY_SCRIPT_SH, "limit-notify.sh")
assert.equal(NOTIFY_LOG, "limit-notify.log")
assert.equal(COMMAND_NAME, "autosession")

assert.equal(notifyScriptName("win32"), "limit-notify.ps1")
assert.equal(notifyScriptName("linux"), "limit-notify.sh")
assert.equal(notifyScriptName("darwin"), "limit-notify.sh")

// El lanzador de Windows abre consola propia (`cmd /c start`); en Linux el sh
// corre y se registra en el log aunque no haya ventana.
assert.equal(notifyCommandFor("win32"), "cmd.exe")
assert.equal(notifyCommandFor("linux"), "/bin/sh")
assert.equal(notifyCommandFor("darwin"), "/bin/sh")

// En este repo conviven ambos scripts: cada SO resuelve el suyo.
assert.ok(notifyScriptFor(import.meta.url, "win32").endsWith("limit-notify.ps1"))
assert.ok(notifyScriptFor(import.meta.url, "linux").endsWith("limit-notify.sh"))
assert.ok(notifyScriptFor(import.meta.url).endsWith(notifyScriptName()))
{
  const args = notifyArgs("C:\\p\\limit-notify.ps1", "s1", "C:\\p\\.opencode_session_dump.md", "win32")
  assert.deepEqual(args, [
    "/c",
    "start",
    "",
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "C:\\p\\limit-notify.ps1",
    "-SessionID",
    "s1",
    "-DumpFile",
    "C:\\p\\.opencode_session_dump.md",
  ])
  assert.equal(args.includes("powershell.exe"), true, "un ps1 sin consola propia imprime a la nada")
}
assert.deepEqual(notifyArgs("/p/limit-notify.sh", "s1", "/p/.opencode_session_dump.md", "linux"), [
  "/p/limit-notify.sh",
  "s1",
  "/p/.opencode_session_dump.md",
])
assert.equal(notifyLogPath("/p/.opencode_session_dump.md"), join("/p", "limit-notify.log"))

// ── el dump no debe reinyectar el error de cuota ─────────────────────────
{
  const dump = [
    "# CONTEXTO DE SESION ANTERIOR (RECUPERADO AUTOMATICAMENTE)",
    "",
    "- Guardado: 2026-10-16T17:40:13.185Z",
    '- Motivo: session.execution.failed: {"status":429,"message":"Rate limit exceeded. Please try again later."}',
    "- Sesion: ses_x",
    "",
    "### USER:",
    "arregla el bug",
    "",
    "### ASSISTANT:",
    "voy a mirarlo",
  ].join("\n")
  const clean = scrubInjectedContext(dump)
  assert.ok(!/429/.test(clean), "fuera el status 429")
  assert.ok(!/rate limit/i.test(clean), "fuera el mensaje de limite")
  assert.ok(!/Guardado:|Motivo:|Sesion:/.test(clean), "fuera la cabecera del dump")
  assert.match(clean, /### USER:\narregla el bug/, "la conversacion se conserva")
  assert.match(clean, /### ASSISTANT:\nvoy a mirarlo/)
}

// `projectDirectory` lee `directory` del PluginInput; las formas anidadas se
// siguen aceptando (no acoplarse a una release concreta).
assert.equal(projectDirectory({ directory: "/dir", worktree: "/wt" }), "/dir")
assert.equal(projectDirectory({ location: { directory: "/loc", project: { directory: "/proj" } } }), "/proj")
assert.equal(projectDirectory({ location: { directory: "/loc" } }), "/loc")
assert.equal(projectDirectory(undefined), process.cwd())

// ── archivos de sesion del repo ──────────────────────────────────────────
assert.equal(matchesSessionFile(".opencode_session_dump.md"), true)
assert.equal(matchesSessionFile(".opencode_session_dump_2026.md"), true)
assert.equal(matchesSessionFile(".OPENCODE_SESSION_DUMP.md"), true, "case-insensitive")
assert.equal(matchesSessionFile("README.md"), false)
assert.equal(matchesSessionFile("session-notes.md"), false, "no entra por defecto")
assert.equal(matchesSessionFile("notas.md", [/^notas\.md$/]), true, "patron custom")

assert.equal(isSkippedDir("node_modules"), true)
assert.equal(isSkippedDir(".git"), true)
assert.equal(isSkippedDir("src"), false)

{
  const dir = mkdtempSync(join(tmpdir(), "autosession-scan-"))
  writeFileSync(join(dir, ".opencode_session_dump.md"), "dump raiz")
  writeFileSync(join(dir, "random.md"), "no cuenta")
  mkdirSync(join(dir, "sub"))
  writeFileSync(join(dir, "sub", ".opencode_session_dump_old.md"), "dump anidado")
  mkdirSync(join(dir, "node_modules"))
  writeFileSync(join(dir, "node_modules", ".opencode_session_dump_dep.md"), "ignorado")

  const files = collectSessionFiles(dir)
  assert.equal(files.length, 2, "raiz + anidado, sin node_modules")
  assert.ok(files.some((f) => f.endsWith(join("sub", ".opencode_session_dump_old.md"))))
  assert.ok(!files.some((f) => f.includes("node_modules")), "skip dirs")
  assert.deepEqual(collectSessionFiles(dir, CONFIG.sessionFilePatterns, CONFIG.skipDirs, 1).length, 1, "tope maxFiles")

  const read = (p) => (p.includes("node_modules") ? "no" : `contenido de ${p.split(/[\\/]/).pop()}`)
  const body = buildRepoContext(files, read)
  assert.match(body, /contenido de \.opencode_session_dump\.md/)
  assert.match(body, /contenido de \.opencode_session_dump_old\.md/)
  assert.equal(buildRepoContext([], read), "", "sin archivos = vacio")
  assert.equal(buildRepoContext(["/x"], () => "   "), "", "archivo vacio se omite")
  assert.equal(buildRepoContext(["/x"], () => {
    throw new Error("boom")
  }), "", "lectura fallida se omite")
}

{
  const big = "a".repeat(5000)
  const single = buildRepoContext(["/a"], () => big, 100, 100000)
  assert.ok(single.length < 200, "recorte por archivo")
  assert.match(single, /\[\.\.\.recortado\.\.\.\]/)
  const total = buildRepoContext(["/a", "/b", "/c"], () => big, 5000, 300)
  assert.ok(total.length <= 400, `tope total respetado (${total.length})`)
}

// ── server() con un PluginInput falso ───────────────────────────────────
/** Doble del cliente: solo la superficie que usa el plugin. */
function fakeClient(history = {}) {
  const toasts = []
  const reads = []
  return {
    toasts,
    reads,
    client: {
      session: {
        messages: async ({ path }) => {
          reads.push(path.id)
          return { data: history[path.id] ?? [] }
        },
      },
      tui: {
        showToast: async ({ body }) => {
          toasts.push(body)
          return true
        },
      },
    },
  }
}

{
  const directory = mkdtempSync(join(tmpdir(), "autosession-e2e-"))
  const history = {
    ses_limit: conversation,
    ses_retry: conversation,
    ses_con_asistente: conversation,
  }
  const fake = fakeClient(history)
  const hooks = await server({ client: fake.client, directory, worktree: directory, project: { directory } })

  assert.equal(typeof hooks.event, "function", "hook event registrado")
  assert.equal(typeof hooks["experimental.chat.system.transform"], "function", "hook de system prompt registrado")
  assert.equal(typeof hooks["command.execute.before"], "function", "hook de comando registrado")

  // ── eventos ────────────────────────────────────────────────────────────
  await hooks.event({
    event: { type: "session.created", properties: { sessionID: "ses_nueva", info: { id: "ses_nueva" } } },
  })
  await hooks.event({
    event: { type: "session.created", properties: { sessionID: "ses_sub", info: { id: "ses_sub", parentID: "ses_nueva" } } },
  })
  await hooks.event({
    event: {
      type: "session.execution.failed",
      properties: { sessionID: "ses_limit", error: { type: "provider-error", message: "Free usage exceeded. Add credits.", status: 429 } },
    },
  })
  await hooks.event({
    event: {
      type: "session.execution.failed",
      properties: { sessionID: "ses_otro", error: { type: "provider-error", message: "internal error", status: 500 } },
    },
  })
  await hooks.event({ event: { type: "session.text.delta", properties: { sessionID: "ses_otro", delta: "ignorado" } } })
  // `session.status` con `type: "retry"` es el punto robusto: trae el mensaje del
  // proveedor aunque no haya un error terminal.
  await hooks.event({
    event: {
      type: "session.status",
      properties: { sessionID: "ses_retry", status: { type: "retry", attempt: 2, message: "Upstream request failed: Insufficient account funds", next: 1 } },
    },
  })
  // Un retry que NO es de cuota no debe guardar nada.
  await hooks.event({
    event: { type: "session.status", properties: { sessionID: "ses_otro", status: { type: "retry", attempt: 1, message: "Upstream request failed: socket hang up", next: 1 } } },
  })

  const dumpFile = dumpPathFor(directory, "ses_retry")
  assert.ok(dumpFile.endsWith(dumpFileName("ses_retry")), "ruta del dump por sesion")
  assert.ok(dumpFileName("ses_retry").includes("ses_retry"), "el nombre lleva el id de la sesion")
  assert.notEqual(
    dumpFileName("ses_otra_sesion"),
    dumpFileName("ses_retry"),
    "dos sesiones no comparten archivo: no se sobrescriben",
  )
  const dump = readFileSync(dumpFile, "utf-8")
  assert.ok(dump.startsWith(`# ${DUMP_TITLE}`), "titulo del dump")
  assert.match(dump, /### USER:\narregla el bug de sesiones/)
  assert.match(dump, /### ASSISTANT:\nvoy a mirarlo/)
  assert.ok(!dump.includes("SECRETO"), "las partes de razonamiento no se guardan")
  assert.ok(!dump.includes("ignorado"), "solo se guarda el historial del evento de limite")
  assert.match(dump, /Motivo: session\.status retry/, "el ultimo limite procesado es el retry")
  assert.match(dump, /Sesion: ses_retry/)
  assert.ok(!dump.includes("ses_otro"), "un 500 y un retry sin cuota no guardan dump")

  // El log de avisos es append-only: registra los dos limites reales.
  const notifyLog = readFileSync(notifyLogPath(dumpFile), "utf-8").trim().split("\n")
  assert.equal(notifyLog.length, 2, "un aviso por limite detectado")
  assert.ok(notifyLog.some((line) => line.includes("ses_limit")))
  assert.ok(notifyLog.some((line) => line.includes("ses_retry")))
  assert.ok(!notifyLog.some((line) => line.includes("ses_otro")))
  assert.ok(notifyLog.every((line) => /LIMITE GRATIS ALCANZADO/.test(line)))

  // El aviso tambien sale como toast (antes era synthetic en la sesion).
  assert.ok(fake.toasts.some((t) => t.title === "LIMITE GRATIS ALCANZADO"), "el limite se anuncia en la UI")
  assert.ok(fake.toasts.some((t) => t.variant === "warning"))

  // ── inyeccion en la sesion nueva ───────────────────────────────────────
  const firstRequest = { sessionID: "ses_nueva", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](firstRequest, firstRequest)
  assert.equal(firstRequest.system.length, 1, "se inyecta un system part")
  assert.ok(firstRequest.system[0].includes(CONTEXT_HEADER))
  assert.match(firstRequest.system[0], /### USER:\narregla el bug de sesiones/)
  assert.ok(!/insufficient/i.test(firstRequest.system[0]), "el error de cuota no se reinyecta")
  assert.ok(firstRequest.system[0].length <= CONFIG.maxInjectChars + CONTEXT_HEADER.length + 200, "tope de inyeccion")

  const secondRequest = { sessionID: "ses_nueva", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](secondRequest, secondRequest)
  assert.equal(secondRequest.system.length, 0, "una inyeccion por sesion")

  const withAssistant = { sessionID: "ses_con_asistente", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](withAssistant, withAssistant)
  assert.equal(withAssistant.system.length, 0, "una sesion con respuesta ya no recibe el contexto viejo")

  const subRequest = { sessionID: "ses_sub", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](subRequest, subRequest)
  assert.equal(subRequest.system.length, 0, "las subsesiones no heredan el contexto del repo")

  // ── /autosession ──────────────────────────────────────────────────────
  const runCommand = async (sessionID, args, output = { parts: [{ id: "template" }] }) => {
    await hooks["command.execute.before"]({ command: COMMAND_NAME, sessionID, arguments: args }, output)
    return output
  }
  const lastToast = () => fake.toasts[fake.toasts.length - 1]

  // Otro comando no se toca.
  const other = { parts: [{ id: "p1" }] }
  await hooks["command.execute.before"]({ command: "init", sessionID: "ses_nueva", arguments: "" }, other)
  assert.deepEqual(other.parts, [{ id: "p1" }], "el hook ignora los demas comandos")

  const dumpOutput = await runCommand("ses_nueva", "dump")
  assert.equal(dumpOutput.parts.length, 1, "el prompt del comando se reemplaza por la parte oculta")
  assert.equal(dumpOutput.parts[0].text, HIDDEN_COMMAND_TEXT)
  assert.equal(dumpOutput.parts[0].synthetic, true)
  assert.equal(dumpOutput.parts[0].ignored, true, "el modelo no gasta turno")

  // El reemplazo debe ser EN SU SITIO: el runtime conserva su referencia al array
  // y es esa la que pasa al modelo. Reasignar `output.parts` no cambia nada.
  {
    const parts = [{ id: "plantilla" }, { id: "argumentos" }]
    const output = { parts }
    await hooks["command.execute.before"]({ command: COMMAND_NAME, sessionID: "ses_nueva", arguments: "" }, output)
    assert.equal(output.parts, parts, "la misma referencia de array")
    assert.equal(parts.length, 1, "el array original queda con una sola parte")
    assert.equal(parts[0].text, HIDDEN_COMMAND_TEXT)
  }
  assert.match(lastToast().message, new RegExp(dumpFileName("ses_nueva")))
  // El dump de `ses_nueva` es SU archivo: el de `ses_retry` sigue intacto.
  assert.match(readFileSync(dumpPathFor(directory, "ses_nueva"), "utf-8"), /Motivo: manual \/autosession dump/)
  assert.match(readFileSync(dumpFile, "utf-8"), /Sesion: ses_retry/, "el dump de la otra sesion no se sobrescribio")

  await runCommand("ses_nueva", "files")
  assert.match(lastToast().message, /archivo\(s\)/)

  await runCommand("ses_nueva", "")
  assert.match(lastToast().message, new RegExp(PLUGIN_ID))
  // Un archivo por sesion: los tres limites vistos dejan tres dumps.
  assert.match(lastToast().message, /Archivos de sesion en el repo: 3/)
  assert.match(lastToast().message, /Dumps: 3 \(sesion actual: \.opencode_session_dump-ses_nueva\.md\)/)

  // `inject` fuerza la inyeccion aunque la sesion ya tenga respuesta.
  await runCommand("ses_con_asistente", "inject")
  assert.match(lastToast().message, /armado/i)
  const armed = { sessionID: "ses_con_asistente", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](armed, armed)
  assert.equal(armed.system.length, 1, "/autosession inject fuerza la inyeccion")

  // ── /autosession simulate: recorrer el limite sin gastar cuota ─────────
  await runCommand("ses_nueva", "simulate")
  assert.match(lastToast().message, /Simulacion ejecutada/i)
  assert.match(lastToast().message, /Dump:/)
  const simuladoFile = dumpPathFor(directory, "ses_nueva")
  assert.match(readFileSync(simuladoFile, "utf-8"), /Motivo: session\.execution\.failed \(simulado\)/)
  assert.match(readFileSync(simuladoFile, "utf-8"), /Free usage limit exceeded \(simulado\)/)

  // Con texto propio decide solo el texto (sin status): asi se prueba el
  // mensaje real del proveedor contra LIMIT_PATTERNS.
  const before = readFileSync(simuladoFile, "utf-8")
  await runCommand("ses_nueva", "simulate Error 400: credit balance too low")
  assert.match(lastToast().message, /NO coincide/i)
  assert.equal(readFileSync(simuladoFile, "utf-8"), before, "sin match no se toca el dump")

  await runCommand("ses_nueva", "simulate free usage exceeded for this key")
  assert.match(lastToast().message, /Simulacion ejecutada/i)
  assert.match(readFileSync(simuladoFile, "utf-8"), /free usage exceeded for this key/)

  // El verbo se compara entero: un texto desconocido cae en status.
  await runCommand("ses_nueva", "simulacion")
  assert.match(lastToast().message, new RegExp(PLUGIN_ID), "verbo desconocido -> status")

  // ── /autosession reset: desatasca el "limite pegado" ───────────────────
  // Con el dump en disco, la sesion nueva recibe el contexto viejo...
  const beforeReset = { sessionID: "ses_tras_reset", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](beforeReset, beforeReset)
  assert.equal(beforeReset.system.length, 1)
  assert.ok(!/rate limit|429/i.test(beforeReset.system[0]), "el error de cuota no se reinyecta")

  await runCommand("ses_nueva", "reset")
  assert.match(lastToast().message, /archivo\(s\) de sesion borrados/)
  assert.equal(existsSync(dumpFile), false, "reset borra el dump")

  const afterReset = { sessionID: "ses_tras_reset_2", model: {}, system: [] }
  await hooks["experimental.chat.system.transform"](afterReset, afterReset)
  assert.equal(afterReset.system.length, 0, "sin dumps no hay contexto que inyectar")

  // clearSessionFiles es la primitiva del reset; cuenta lo que borra.
  writeFileSync(join(directory, ".opencode_session_dump_otro.md"), "x")
  assert.equal(clearSessionFiles(directory), 1)
  assert.equal(clearSessionFiles(directory), 0, "idempotente")

  await hooks.dispose?.()
}

// ── server() sin input (sondeo del cargador) no debe lanzar ─────────────
assert.deepEqual(await server(undefined), {}, "sin client: hooks vacios, sin lanzar")
{
  const hooks = await server({})
  assert.equal(typeof hooks.event, "function", "sin client igual devuelve los hooks")
  assert.equal(await hooks.dispose?.(), undefined)
}

// ── ids de parte y retencion de dumps ────────────────────────────────────
{
  // El runtime decodifica el id de la parte y exige el prefijo `prt`: con
  // cualquier otro, el comando devuelve 500 y el aviso no llega a verse.
  const id = partId()
  assert.ok(id.startsWith("prt_"), `el id de parte empieza por prt_ (${id})`)
  assert.equal(id.length, 30, "prt_ + 26 caracteres, como los ids del runtime")
  const deterministic = partId(() => 0.5)
  assert.equal(deterministic.length, 30)
  assert.ok(/^prt_[0-9a-zA-Z]{26}$/.test(deterministic), "solo base62 tras el prefijo")
  assert.notEqual(partId(), partId(), "dos partes no comparten id")
  const part = hiddenPart("ses_id")
  assert.ok(String(part.id).startsWith("prt_"), "hiddenPart usa un id valido")
}

{
  // Un archivo por sesion no puede crecer sin limite.
  const dir = mkdtempSync(join(tmpdir(), "autosession-dumps-"))
  for (let i = 0; i < 5; i++) {
    writeFileSync(join(dir, dumpFileName(`ses_${i}`)), `dump ${i}`)
  }
  writeFileSync(join(dir, "otro.md"), "no es un dump")
  assert.equal(listDumps(dir).length, 5, "solo cuenta los dumps del plugin")
  assert.equal(pruneDumps(dir, 3), 2, "borra los mas viejos sobrantes")
  assert.equal(listDumps(dir).length, 3, "conserva los mas recientes")
  assert.ok(existsSync(join(dir, "otro.md")), "no toca archivos ajenos")
  assert.equal(pruneDumps(dir, 0), 0, "keep 0 no borra nada (evita vaciar el historial por error)")
  assert.equal(listDumps(dir).length, 3)
}

console.log("OK: smoke auto-session")
