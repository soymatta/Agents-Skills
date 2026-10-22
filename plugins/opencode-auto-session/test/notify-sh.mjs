// Verifica limit-notify.sh y limit-notify.ps1 (aviso + recuperacion):
// sintaxis POSIX, aviso durable en el log, delegacion al emulador de terminal y
// -lo critico- que la recuperacion (cerrar OpenCode, limpiar cache, rotar VPN)
// toque EXACTAMENTE lo que debe y nada mas.
//
// No mata nada real: `pgrep` esta falso y solo reporta procesos de prueba
// (unos `sleep` que el test controla). Asi se comprueba de verdad que los
// senalados mueren, que el ajeno sobrevive y que el script no se mata a si
// mismo. El emulador de terminal tambien es falso: los tests nunca abren
// ventanas.
//
// TRAMPA (confirmada: cierro sesiones reales de OpenCode): el script hace
// `export PATH="$PATH:/usr/bin:/usr/local/bin"`, asi que un caso con el PATH
// recortado AUN encuentra el `pgrep`/`ps` REALES, y con RECOVER=1 eso mata los
// procesos de OpenCode del usuario. Por eso todo spawn de este archivo pasa por
// `spawnSync`, envuelto abajo: se exige HOME/TMPDIR de sandbox y `pgrep`+`ps`
// falsos como PRIMER directorio del PATH. Un caso que no los traiga aborta el
// test en vez de tocar el sistema.
//
// El .ps1 no se ejecuta aqui (no hay PowerShell en Linux): se auditan sus
// invariantes de seguridad de forma estatica.
import assert from "node:assert/strict"
import { spawn, spawnSync as nodeSpawnSync } from "node:child_process"
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

if (process.platform === "win32") {
  console.log("SKIP: limit-notify.sh es POSIX (Windows usa limit-notify.ps1)")
  process.exit(0)
}

const here = dirname(fileURLToPath(import.meta.url))
const script = join(here, "..", "limit-notify.sh")
const ps1 = join(here, "..", "limit-notify.ps1")

// Guarda de seguridad: intercepta todo `spawnSync` de este archivo y rechaza
// cualquier ejecucion del script que no corra con herramientas falsas. Evita
// que un caso nuevo (o un PATH recortado) alcance el `pgrep` real y cierre
// procesos del usuario. El `sh -n` no pasa por aqui (no ejecuta el script).
function spawnSync(cmd, args, opts = {}) {
  if (cmd === "/bin/sh" && Array.isArray(args) && args[0] === script) {
    const env = opts.env ?? process.env
    const home = String(env.HOME ?? "")
    const first = String(env.PATH ?? "").split(":")[0]
    assert.ok(home.startsWith(tmpdir()), `HOME debe ser un sandbox, no "${home}"`)
    assert.ok(String(env.TMPDIR ?? "").startsWith(tmpdir()), "TMPDIR debe ser un sandbox")
    assert.ok(first.startsWith(tmpdir()), `PATH[0] ("${first}") debe ser un sandbox, no el PATH del sistema`)
    for (const tool of ["pgrep", "ps"]) {
      assert.ok(existsSync(join(first, tool)), `PATH[0] ("${first}") debe traer un ${tool} falso`)
    }
  }
  return nodeSpawnSync(cmd, args, opts)
}

assert.ok(existsSync(script), "existe limit-notify.sh")
assert.ok(existsSync(ps1), "existe limit-notify.ps1")

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
}

function waitForFile(path, timeoutMs = 3000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (existsSync(path)) return true
    sleep(25)
  }
  return existsSync(path)
}

function alive(pid) {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// Asincrono a proposito: un bucle que bloquee el event loop deja al hijo muerto
// como zombie sin recolectar, y `kill(pid, 0)` lo seguiria viendo vivo.
async function waitDead(pid, timeoutMs = 4000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (!alive(pid)) return true
    await pause(25)
  }
  return !alive(pid)
}

// Un `sleep` de verdad cuyo PID pasamos al `pgrep` falso: el script puede
// matarlo y el test puede comprobar si sobrevivio.
function spawnVictim() {
  return spawn("sleep", ["600"], { stdio: "ignore", detached: false })
}

function codeOnly(body) {
  return body
    .replace(/<#[\s\S]*?#>/g, "")
    .split("\n")
    .filter((line) => !/^\s*#/.test(line))
    .join("\n")
}

// ── 0. invariantes de seguridad ───────────────────────────────────────────
// Solo se audita el codigo: los comentarios explican los errores corregidos y
// nombran justo lo prohibido (`pgrep -f`, `rm -rf`), asi que se descartan.
{
  const sh = codeOnly(readFileSync(script, "utf-8"))
  // Matar por linea de comandos alcanza la terminal, la shell del script y
  // cualquier ruta con "opencode" (el propio script): solo vale el nombre exacto.
  assert.ok(!/pgrep\s+-\w*f\b/.test(sh), "sh: no debe matar por patron de linea de comandos")
  assert.match(sh, /pgrep -x/, "sh: identifica procesos por nombre exacto")
  assert.match(sh, /\$\$/, "sh: excluye su propio PID")
  // El servidor de OpenCode es el padre del script: perdonarlo dejaria vivo lo
  // unico que hay que cerrar.
  assert.ok(!/PPID/.test(sh), "sh: no perdona al proceso padre (el servidor es el padre)")
  // rm -rf "$VAR"/* con VAR vacio apunta a la raiz.
  assert.ok(!/rm\s+-rf?\s+["']?\$/.test(sh), "sh: no borra con una ruta variable sin validar")
  for (const keep of ["skills", "plugins", "commands", "agents"]) {
    assert.ok(!new RegExp(`rm[^\\n]*${keep}`).test(sh), `sh: no borra .opencode/${keep}`)
  }
  // El filtro de caché exige que el ultimo componente sea de cache.
  assert.match(sh, /basename "\$dir"/, "sh: valida el ultimo componente antes de borrar")
  // gnome-terminal y sus alias no aceptan `-e` con varios argumentos.
  assert.match(sh, /launcher="--"/, "sh: usa el lanzador correcto en gnome-terminal")
  for (const forbidden of [/\bsudo\b/, /\bpkexec\b/, /curl\s+-[^\n]*\|\s*(ba)?sh/, /wget\s+-[^\n]*\|\s*(ba)?sh/, /\bapt(-get)?\s+install\b/]) {
    assert.ok(!forbidden.test(sh), `sh: no usa privilegios ni instala nada: ${forbidden}`)
  }

  const win = codeOnly(readFileSync(ps1, "utf-8"))
  // `taskkill /IM node.exe /T` se lleva por delante editores y otros Node.
  assert.ok(!/taskkill/i.test(win), "ps1: no usa taskkill en bloque")
  assert.match(win, /Win32_Process/, "ps1: filtra los procesos Node por linea de comandos")
  assert.match(win, /CommandLine -match "opencode"/, "ps1: solo cierra Node de OpenCode")
  assert.match(win, /Remove-Item/, "ps1: limpia la cache")
  assert.ok(!/Remove-Item[^\n]*\$env:\w+\s*\*/i.test(win), "ps1: no borra con comodin sobre una variable de entorno")
  for (const keep of ["skills", "plugins", "commands", "agents"]) {
    assert.ok(!new RegExp(`Remove-Item[^\\n]*${keep}`).test(win), `ps1: no borra .opencode/${keep}`)
  }
  assert.match(win, /GetPathRoot/, "ps1: rechaza rutas raiz antes de borrar")
  for (const forbidden of [/Start-Process[^\n]*sudo/i, /winget\s+install/i, /choco\s+install/i, /Invoke-WebRequest[^\n]*\|\s*Invoke-Expression/i]) {
    assert.ok(!forbidden.test(win), `ps1: no usa privilegios ni instala nada: ${forbidden}`)
  }
}

// ── 1. sintaxis POSIX ────────────────────────────────────────────────────
{
  const syntax = spawnSync("/bin/sh", ["-n", script], { encoding: "utf-8" })
  assert.equal(syntax.status, 0, `sh -n fallo: ${syntax.stderr}`)
}

// Banco de pruebas: HOME/TMPDIR/LOCALAPPDATA falsos (con caches de mentira) y
// un proyecto falso con lo que NO se debe borrar.
function makeSandbox(label, { terminal = null } = {}) {
  const root = mkdtempSync(join(tmpdir(), `notify-sh-${label}-`))
  const home = join(root, "home")
  const project = join(root, "project")
  const bin = join(root, "bin")
  for (const dir of [
    join(home, ".cache", "opencode"),
    join(home, ".config", "opencode"),
    join(root, "appdata", "OpenCode", "Cache"),
    join(project, ".opencode", "cache"),
    join(project, ".opencode", "tmp"),
    bin,
  ]) {
    mkdirSync(dir, { recursive: true })
  }
  // Cache: debe desaparecer.
  for (const dir of [join(home, ".cache", "opencode"), join(root, "appdata", "OpenCode", "Cache"), join(project, ".opencode", "cache"), join(project, ".opencode", "tmp")]) {
    writeFileSync(join(dir, "basura.bin"), "x")
  }
  // Config y datos del proyecto: deben sobrevivir.
  writeFileSync(join(home, ".config", "opencode", "opencode.json"), "{}")
  for (const [name, content] of [["skills", "skill"], ["plugins", "plugin"], ["commands", "command"], ["agents", "agent"]]) {
    const dir = join(project, ".opencode", name)
    mkdirSync(dir, { recursive: true })
    writeFileSync(join(dir, "guardar.md"), content)
  }
  writeFileSync(join(project, ".opencode", "opencode.json"), "{}")
  const dump = join(project, ".opencode_session_dump.md")
  writeFileSync(dump, "dump")

  // `pgrep` falso: reporta procesos de prueba que el test controla, incluido el
  // propio PID del script (leido del pidfile) para comprobar que se excluye.
  // Nunca reporta el PID de este proceso de node: matarlo abortaria el test.
  const pgrep = join(bin, "pgrep")
  writeFileSync(
    pgrep,
    `#!/bin/sh\nname=""\nwhile [ $# -gt 0 ]; do case "$1" in -x) name="$2" ;; esac; shift; done\n` +
      `self="$(cat "$OPENCODE_TEST_SELF_PID_FILE" 2>/dev/null || true)"\n` +
      `case "$name" in\n` +
      `  opencode) printf '%s\\n' "$OPENCODE_TEST_OPENCODE $self" ;;\n` +
      `  node) printf '%s\\n' "$OPENCODE_TEST_NODE" ;;\n` +
      `esac\n`,
  )
  // De los procesos Node solo cierra los que son de OpenCode.
  const ps = join(bin, "ps")
  writeFileSync(ps, `#!/bin/sh\ncase "$*" in *"$OPENCODE_TEST_NODE_OPENCODE"*) echo "node /opt/opencode/server.js" ;; *) echo "node vite dev" ;; esac\n`)
  // rm real, que registra lo que se le pide (para auditar rutas prohibidas).
  const rmLog = join(root, "rm.log")
  const rm = join(bin, "rm")
  writeFileSync(rm, `#!/bin/sh\nprintf '%s\\n' "$*" >> "${rmLog}"\nexec /bin/rm "$@"\n`)
  const vpnLog = join(root, "vpn.log")
  const vpn = join(bin, "proton-vpn-cli")
  writeFileSync(vpn, `#!/bin/sh\nprintf '%s\\n' "$*" >> "${vpnLog}"\n`)
  const tools = [pgrep, ps, rm, vpn]

  // El emulador solo existe cuando se prueba la delegacion, y se pasa por
  // TERMINAL para que el script no encuentre uno de verdad en el sistema (eso
  // abriria una ventana real). El nombre del falso decide el lanzador.
  const termArgs = join(root, "term-args.txt")
  let terminalPath = null
  if (terminal) {
    terminalPath = join(bin, terminal)
    writeFileSync(terminalPath, `#!/usr/bin/env sh\nprintf '%s\\n' "$@" > "${termArgs}"\n`)
    tools.push(terminalPath)
  }
  for (const f of tools) chmodSync(f, 0o755)

  const pidFile = join(root, "script.pid")
  return { root, home, project, bin, dump, rmLog, vpnLog, termArgs, pidFile, terminalPath }
}

// ── 2. sin TTY delega en el emulador y deja UNA sola linea de log ────────
{
  const sb = makeSandbox("term", { terminal: "x-terminal-emulator" })
  const res = spawnSync("/bin/sh", [script, "ses_pty", sb.dump, "0"], {
    encoding: "utf-8",
    cwd: sb.project,
    env: {
      ...process.env,
      PATH: `${sb.bin}:${process.env.PATH ?? ""}`,
      HOME: sb.home,
      TMPDIR: sb.root,
      TERMINAL: sb.terminalPath,
      OPENCODE_LIMIT_KILL_WAIT: "0",
    },
  })
  assert.equal(res.status, 0, res.stderr)
  assert.equal(res.stdout, "", "sin TTY delega en el emulador en vez de imprimir al servidor")

  assert.ok(waitForFile(sb.termArgs), "el emulador falso se ejecuto")
  const args = readFileSync(sb.termArgs, "utf-8").trim().split("\n")
  // gnome-terminal y sus alias (x-terminal-emulator en Debian) rechazan `-e`
  // con varios argumentos: la ventana no abriria.
  assert.equal(args[0], "--", `x-terminal-emulator recibe '--', no '-e' (${args.join(" ")})`)
  assert.equal(args[1], "sh")
  assert.ok(args[2].endsWith("limit-notify.sh"), "pasa la ruta absoluta del script")
  assert.equal(args[3], "ses_pty")
  assert.equal(args[4], sb.dump)
  assert.equal(args[5], "0")

  const log = readFileSync(join(sb.project, "limit-notify.log"), "utf-8")
  assert.match(log, /LIMITE GRATIS ALCANZADO/)
  assert.match(log, /sesion=ses_pty/)
  assert.equal(log.trim().split("\n").length, 1, `el aviso no se duplica al delegar (log: ${log})`)
  // La delegacion no debe hacer trabajo destructivo por su cuenta.
  assert.ok(!existsSync(sb.rmLog), "delegar no borra nada")
}

// ── 2b. terminal que si acepta `-e` ─────────────────────────────────────
{
  const sb = makeSandbox("term-konsole", { terminal: "konsole" })
  const res = spawnSync("/bin/sh", [script, "ses_konsole", sb.dump, "0"], {
    encoding: "utf-8",
    cwd: sb.project,
    env: { ...process.env, PATH: `${sb.bin}:${process.env.PATH ?? ""}`, HOME: sb.home, TMPDIR: sb.root, TERMINAL: sb.terminalPath, OPENCODE_LIMIT_KILL_WAIT: "0" },
  })
  assert.equal(res.status, 0, res.stderr)
  assert.ok(waitForFile(sb.termArgs), "el emulador falso se ejecuto")
  assert.equal(readFileSync(sb.termArgs, "utf-8").trim().split("\n")[0], "-e", "konsole recibe '-e'")
}

// ── 3. recuperacion completa: mata lo justo, borra lo justo, rota la VPN ──
{
  const sb = makeSandbox("recover")
  const opencodeA = spawnVictim()
  const opencodeB = spawnVictim()
  const nodeOpencode = spawnVictim()
  const nodeForeign = spawnVictim()
  // El wrapper publica su PID y hace exec: ese es el PID real del script.
  const wrapper = (ses) => ["-c", 'printf "%s\\n" "$$" > "$1"; exec /bin/sh "$2" "$3" "$4" "0"', "sh", sb.pidFile, script, ses, sb.dump]
  try {
    const res = spawnSync("/bin/sh", wrapper("ses_recover"), {
      encoding: "utf-8",
      cwd: sb.project,
      env: {
        PATH: `${sb.bin}:${process.env.PATH ?? ""}`,
        HOME: sb.home,
        TMPDIR: sb.root,
        LOCALAPPDATA: sb.root,
        APPDATA: join(sb.root, "appdata"),
        TERMINAL: "",
        OPENCODE_LIMIT_KILL_WAIT: "0",
        OPENCODE_LIMIT_WINDOW: "0",
        OPENCODE_LIMIT_RECOVER: "1",
        OPENCODE_TEST_OPENCODE: `${opencodeA.pid} ${opencodeB.pid}`,
        OPENCODE_TEST_NODE: `${nodeOpencode.pid} ${nodeForeign.pid}`,
        OPENCODE_TEST_NODE_OPENCODE: String(nodeOpencode.pid),
        OPENCODE_TEST_SELF_PID_FILE: sb.pidFile,
      },
    })
    assert.equal(res.status, 0, res.stderr)
    assert.match(res.stdout, /LIMITE GRATIS ALCANZADO/)
    assert.match(res.stdout, /Cerrando 3 proceso\(s\)/, `cierra OpenCode y el Node de OpenCode, no el ajeno (stdout: ${res.stdout})`)
    assert.match(res.stdout, /Proceso completado/, "llega al final: no se mata a si mismo")

    // El `pgrep` falso reporto el PID real del script entre los de OpenCode: si
    // no se excluyera, cerraria el proceso que esta avisando (el fallo del
    // script original) y no llegaria al final.
    const selfPid = Number(readFileSync(sb.pidFile, "utf-8").trim())
    assert.ok(selfPid > 0, "el wrapper publico el PID del script")
    assert.ok(!res.stdout.includes(String(selfPid)), "no incluye su propio PID entre los procesos a cerrar")

    // Los procesos de OpenCode mueren; el Node ajeno vive.
    assert.ok(await waitDead(opencodeA.pid), "cierra el primer proceso de OpenCode")
    assert.ok(await waitDead(opencodeB.pid), "cierra el segundo proceso de OpenCode")
    assert.ok(await waitDead(nodeOpencode.pid), "cierra el proceso Node de OpenCode")
    assert.ok(alive(nodeForeign.pid), "no toca un proceso Node ajeno a OpenCode")

    // VPN: desconecta y reconecta por la ruta mas rapida.
    const vpn = readFileSync(sb.vpnLog, "utf-8").trim().split("\n")
    assert.deepEqual(vpn, ["disconnect", "connect --fastest"])

    // Cache borrada.
    for (const dir of [join(sb.home, ".cache", "opencode"), join(sb.root, "appdata", "OpenCode", "Cache"), join(sb.project, ".opencode", "cache"), join(sb.project, ".opencode", "tmp")]) {
      assert.equal(readdirSync(dir).length, 0, `vacia ${dir}`)
    }
    // Datos del proyecto y config global intactos.
    for (const name of ["skills", "plugins", "commands", "agents"]) {
      assert.ok(existsSync(join(sb.project, ".opencode", name, "guardar.md")), `conserva .opencode/${name}`)
    }
    assert.ok(existsSync(join(sb.project, ".opencode", "opencode.json")), "conserva la config del proyecto")
    assert.ok(existsSync(join(sb.home, ".config", "opencode", "opencode.json")), "conserva la config global")
    assert.ok(existsSync(sb.dump), "conserva el dump de la sesion")

    // Auditoria de rutas: rm solo recibio contenido de cache.
    const rmLog = readFileSync(sb.rmLog, "utf-8")
    for (const bad of [".opencode/skills", ".opencode/plugins", ".opencode/commands", ".opencode/agents", "opencode.json", ".opencode_session_dump", ".config/opencode"]) {
      assert.ok(!rmLog.includes(bad), `rm nunca recibe una ruta con "${bad}" (${rmLog})`)
    }
    const rmTargets = rmLog.trim().split("\n").map((line) => line.split(" ").pop())
    for (const target of rmTargets) {
      assert.ok(target.startsWith(sb.root) || target.startsWith(".opencode/"), `rm solo actua dentro del sandbox o en .opencode relativo (${target})`)
    }
    assert.match(rmLog, /\.cache\/opencode\/basura\.bin/, "rm recibe el contenido de la cache")

    // Rastro de lo que se hizo y enfriamiento marcado para no entrar en bucle.
    assert.match(readFileSync(join(sb.project, "limit-notify.log"), "utf-8"), /recuperacion sesion=ses_recover cerrados=3/)
    assert.ok(existsSync(join(sb.project, ".limit-notify.stamp")), "deja marca de enfriamiento")
  } finally {
    for (const child of [opencodeA, opencodeB, nodeOpencode, nodeForeign]) {
      try {
        child.kill("SIGKILL")
      } catch {
        /* ya murio */
      }
    }
  }
}

// ── 4. enfriamiento: no vuelve a cerrar OpenCode si el limite sigue ───────
{
  const sb = makeSandbox("cooldown")
  const env = { ...process.env, PATH: `${sb.bin}:${process.env.PATH ?? ""}`, HOME: sb.home, TMPDIR: sb.root, TERMINAL: "", OPENCODE_LIMIT_KILL_WAIT: "0", OPENCODE_LIMIT_WINDOW: "0", OPENCODE_LIMIT_RECOVER: "1" }
  const first = spawnSync("/bin/sh", [script, "ses_1", sb.dump, "0"], { encoding: "utf-8", cwd: sb.project, env })
  assert.equal(first.status, 0, first.stderr)
  const rmAfterFirst = readFileSync(sb.rmLog, "utf-8")

  const second = spawnSync("/bin/sh", [script, "ses_2", sb.dump, "0"], { encoding: "utf-8", cwd: sb.project, env })
  assert.equal(second.status, 0, second.stderr)
  assert.match(second.stdout, /Recuperacion omitida/, "el segundo aviso no vuelve a cerrar OpenCode")
  assert.equal(readFileSync(sb.rmLog, "utf-8"), rmAfterFirst, "no vuelve a limpiar cache")

  // Con el tope desactivado si recupera. Se vuelve a ensuciar la cache: la
  // primera pasada ya la dejo vacia.
  writeFileSync(join(sb.home, ".cache", "opencode", "basura.bin"), "x")
  const third = spawnSync("/bin/sh", [script, "ses_3", sb.dump, "0"], { encoding: "utf-8", cwd: sb.project, env: { ...env, OPENCODE_LIMIT_COOLDOWN: "0" } })
  assert.equal(third.status, 0, third.stderr)
  assert.match(third.stdout, /Proceso completado/, "COOLDOWN=0 desactiva el tope")
  assert.notEqual(readFileSync(sb.rmLog, "utf-8"), rmAfterFirst, "vuelve a limpiar cache")
}

// ── 5. por defecto (OPENCODE_LIMIT_RECOVER sin definir): solo avisa ─────
// El limite gratuito es de la cuenta y salta a diario: cerrar OpenCode en cada
// salto tiraria la sesion en la que se esta trabajando.
{
  const sb = makeSandbox("notify-only")
  const opencode = spawnVictim()
  try {
    const res = spawnSync("/bin/sh", [script, "ses_only", sb.dump, "0"], {
      encoding: "utf-8",
      cwd: sb.project,
      env: {
        ...process.env,
        PATH: `${sb.bin}:${process.env.PATH ?? ""}`,
        HOME: sb.home,
        TMPDIR: sb.root,
        TERMINAL: "",
        OPENCODE_LIMIT_WINDOW: "0",
        OPENCODE_TEST_OPENCODE: String(opencode.pid),
      },
    })
    assert.equal(res.status, 0, res.stderr)
    assert.match(res.stdout, /LIMITE GRATIS ALCANZADO/)
    assert.match(res.stdout, /solo aviso/)
    assert.ok(alive(opencode.pid), "no cierra procesos")
    assert.ok(!existsSync(sb.rmLog), "no limpia cache")
    assert.match(readFileSync(join(sb.project, "limit-notify.log"), "utf-8"), /recuperacion omitida \(RECOVER=0\)/)
  } finally {
    try {
      opencode.kill("SIGKILL")
    } catch {
      /* ya murio */
    }
  }
}

// ── 6. sin emulador ni TTY: imprime el aviso igual ──────────────────────
{
  const root = mkdtempSync(join(tmpdir(), "notify-sh-headless-"))
  const home = join(root, "home")
  const emptyBin = join(root, "empty-bin")
  mkdirSync(home, { recursive: true })
  mkdirSync(emptyBin)
  // Falsos que no reportan nada: el script debe concluir "sin procesos", no
  // adivinar. Sin ellos el `pgrep` real veria los procesos del usuario.
  for (const tool of ["pgrep", "ps"]) {
    writeFileSync(join(emptyBin, tool), "#!/bin/sh\nexit 1\n")
    chmodSync(join(emptyBin, tool), 0o755)
  }
  const dump = join(root, ".opencode_session_dump.md")
  writeFileSync(dump, "dump")

  const res = spawnSync("/bin/sh", [script, "ses_headless", dump, "0"], {
    encoding: "utf-8",
    cwd: root,
    env: { PATH: emptyBin, HOME: home, TERMINAL: "", TMPDIR: root, OPENCODE_LIMIT_KILL_WAIT: "0", OPENCODE_LIMIT_WINDOW: "0", OPENCODE_LIMIT_RECOVER: "1" },
  })
  assert.equal(res.status, 0, res.stderr)
  assert.match(res.stdout, /LIMITE GRATIS ALCANZADO/, "sin emulador el aviso va a stdout")
  assert.match(res.stdout, /Sesion: ses_headless/)
  assert.match(res.stdout, /No se encontro ningun proceso de OpenCode/, "sin pgrep no adivina: no cierra nada")
  assert.match(res.stdout, /No se encontro la CLI de Proton VPN/, "sin CLI de VPN no instala nada")

  const log = readFileSync(join(root, "limit-notify.log"), "utf-8")
  assert.match(log, /LIMITE GRATIS ALCANZADO/)
  assert.match(log, /sesion=ses_headless/)
}

// ── 7. variables de entorno cuando no hay argumentos ────────────────────
{
  const root = mkdtempSync(join(tmpdir(), "notify-sh-env-"))
  const home = join(root, "home")
  const emptyBin = join(root, "empty-bin")
  mkdirSync(home, { recursive: true })
  mkdirSync(emptyBin)
  for (const tool of ["pgrep", "ps"]) {
    writeFileSync(join(emptyBin, tool), "#!/bin/sh\nexit 1\n")
    chmodSync(join(emptyBin, tool), 0o755)
  }
  const dump = join(root, ".opencode_session_dump.md")
  writeFileSync(dump, "dump")
  const res = spawnSync("/bin/sh", [script], {
    encoding: "utf-8",
    cwd: root,
    env: { PATH: emptyBin, HOME: home, TERMINAL: "", TMPDIR: root, OPENCODE_LIMIT_SESSION: "ses_env", OPENCODE_LIMIT_DUMP: dump, OPENCODE_LIMIT_KEEP_OPEN: "0", OPENCODE_LIMIT_KILL_WAIT: "0", OPENCODE_LIMIT_WINDOW: "0", OPENCODE_LIMIT_RECOVER: "1" },
  })
  assert.equal(res.status, 0, res.stderr)
  const log = readFileSync(join(root, "limit-notify.log"), "utf-8")
  assert.match(log, /sesion=ses_env/)
  assert.match(log, new RegExp(dump.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")))
}

// ── 8. la guarda rechaza cualquier entorno que no sea sandbox ────────────
{
  const unsafe = [
    { env: { PATH: "/usr/bin:/bin", HOME: "/root", TMPDIR: tmpdir() }, why: /HOME debe ser un sandbox/ },
    { env: { PATH: "/usr/bin:/bin", HOME: tmpdir(), TMPDIR: tmpdir() }, why: /PATH\[0\].*sandbox/ },
    { env: { PATH: tmpdir(), HOME: tmpdir(), TMPDIR: tmpdir() }, why: /pgrep falso/ },
  ]
  for (const { env, why } of unsafe) {
    assert.throws(() => spawnSync("/bin/sh", [script, "ses_guard", "/tmp/x", "0"], { env }), why)
  }
  // El `sh -n` no ejecuta el script: no pasa por la guarda.
  assert.equal(spawnSync("/bin/sh", ["-n", script], { encoding: "utf-8" }).status, 0)
}

console.log("OK: notify-sh")
