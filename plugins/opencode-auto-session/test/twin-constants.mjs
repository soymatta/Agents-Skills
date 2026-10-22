// Guard de "constantes gemelas": limit-notify.sh y limit-notify.ps1 son dos
// implementaciones de la MISMA logica, y nada impide que sus valores compartidos
// diverjan en silencio. Este test extrae cada constante de ambos archivos y falla
// cuando no coinciden. Corre en cualquier plataforma: solo lee texto, no ejecuta
// ninguno de los dos scripts.
//
// No compara lo que es deliberadamente distinto por plataforma (SIGTERM/SIGKILL,
// ventana de terminal): eso se documenta abajo como POSIX_ONLY.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const sh = readFileSync(join(here, "..", "limit-notify.sh"), "utf-8")
const ps1 = readFileSync(join(here, "..", "limit-notify.ps1"), "utf-8")

function extract(text, pattern, label) {
  const match = text.match(pattern)
  assert.ok(match, `no se pudo extraer ${label}; el formato del script cambio`)
  return match[1]
}

// ── valores por defecto compartidos ─────────────────────────────────────────
const shKeep = extract(
  sh,
  /KEEP_OPEN_SECONDS="\$\{3:-\$\{OPENCODE_LIMIT_KEEP_OPEN:-(\d+)\}\}"/,
  "KEEP_OPEN_SECONDS (.sh)",
)
const ps1Keep = extract(
  ps1,
  /\$KeepOpenSeconds\s*=\s*\$\(if\s*\(\$env:OPENCODE_LIMIT_KEEP_OPEN\)\s*\{\s*\[int\]\$env:OPENCODE_LIMIT_KEEP_OPEN\s*\}\s*else\s*\{\s*(\d+)\s*\}\s*\)/,
  "KeepOpenSeconds (.ps1)",
)
assert.equal(shKeep, ps1Keep, "KEEP_OPEN por defecto debe ser igual en ambos scripts")

const shRecover = extract(sh, /RECOVER="\$\{OPENCODE_LIMIT_RECOVER:-(\d+)\}"/, "RECOVER (.sh)")
const ps1Recover = extract(
  ps1,
  /\$Recover\s*=\s*\$\(if\s*\(\$env:OPENCODE_LIMIT_RECOVER\)\s*\{\s*\$env:OPENCODE_LIMIT_RECOVER\s*\}\s*else\s*\{\s*"(\d+)"\s*\}\s*\)/,
  "Recover (.ps1)",
)
assert.equal(shRecover, ps1Recover, "RECOVER por defecto debe ser igual (0 = solo avisar)")
assert.equal(shRecover, "0", "la recuperacion debe venir desactivada por defecto")

const shCooldown = extract(sh, /COOLDOWN="\$\{OPENCODE_LIMIT_COOLDOWN:-(\d+)\}"/, "COOLDOWN (.sh)")
const ps1Cooldown = extract(
  ps1,
  /\$Cooldown\s*=\s*\$\(if\s*\(\$env:OPENCODE_LIMIT_COOLDOWN\)\s*\{\s*\[int\]\$env:OPENCODE_LIMIT_COOLDOWN\s*\}\s*else\s*\{\s*(\d+)\s*\}\s*\)/,
  "Cooldown (.ps1)",
)
assert.equal(shCooldown, ps1Cooldown, "COOLDOWN por defecto debe ser igual en ambos scripts")

const shKillNode = extract(sh, /KILL_NODE="\$\{OPENCODE_LIMIT_KILL_NODE:-(\d+)\}"/, "KILL_NODE (.sh)")
const ps1KillNode = extract(
  ps1,
  /\$KillNode\s*=\s*\$\(if\s*\(\$env:OPENCODE_LIMIT_KILL_NODE\)\s*\{\s*\$env:OPENCODE_LIMIT_KILL_NODE\s*\}\s*else\s*\{\s*"(\d+)"\s*\}\s*\)/,
  "KillNode (.ps1)",
)
assert.equal(shKillNode, ps1KillNode, "KILL_NODE por defecto debe ser igual en ambos scripts")

// ── banner, log y stamp ─────────────────────────────────────────────────────
const shBanner = extract(sh, /^BANNER="([^"]+)"/m, "BANNER (.sh)")
const ps1Banner = extract(ps1, /^\$banner = "([^"]+)"/m, "banner (.ps1)")
assert.equal(shBanner, ps1Banner, "el banner visible debe ser identico")

for (const name of ["limit-notify.log", ".limit-notify.stamp"]) {
  assert.ok(sh.includes(name), `(.sh) debe usar ${name}`)
  assert.ok(ps1.includes(name), `(.ps1) debe usar ${name}`)
}

// ── hojas de cache permitidas ───────────────────────────────────────────────
// El .sh exige que el ultimo componente de la ruta sea de cache; el .ps1 aplica
// la misma regla con un arreglo. Si un script lista una hoja y el otro no, uno
// de los dos deja de limpiar (o limpia de mas) sin que nadie lo note.
const shLeaves = extract(sh, /case "\$\(basename "\$dir"\)" in\s*\n\s*([^)]*)\)/, "hojas de cache (.sh)")
  .split("|")
  .map(value => value.trim())
const ps1Leaves = extract(
  ps1,
  /if \(@\(([^)]*)\) -notcontains \$leaf\)/,
  "hojas de cache (.ps1)",
)
  .split(",")
  .map(value => value.trim().replace(/^"|"$/g, ""))

assert.deepEqual(
  [...shLeaves].sort(),
  [...ps1Leaves].sort(),
  "las hojas de cache permitidas deben ser las mismas en ambos scripts",
)

// ── CLI de VPN ──────────────────────────────────────────────────────────────
const vpnNames = ["proton-vpn-cli", "protonvpn-cli"]
for (const name of vpnNames) {
  assert.ok(sh.includes(name), `(.sh) debe reconocer ${name}`)
  assert.ok(ps1.includes(name), `(.ps1) debe reconocer ${name}`)
}

// ── base de datos saneada ───────────────────────────────────────────────────
const dbTables = extract(sh, /\[([^\]]*account[^\]]*)\]/, "tablas de opencode.db (.sh)")
  .split(",")
  .map(value => value.trim().replace(/^'|'$/g, ""))
const ps1Tables = extract(ps1, /\[([^\]]*account[^\]]*)\]/, "tablas de opencode.db (.ps1)")
  .split(",")
  .map(value => value.trim().replace(/^'|'$/g, ""))
assert.deepEqual(
  [...dbTables].sort(),
  [...ps1Tables].sort(),
  "las tablas saneadas de opencode.db deben ser las mismas en ambos scripts",
)

// ── variables de entorno ────────────────────────────────────────────────────
// Compartidas: cambian el comportamiento en ambas plataformas.
const sharedEnvs = [
  "OPENCODE_LIMIT_SESSION",
  "OPENCODE_LIMIT_DUMP",
  "OPENCODE_LIMIT_KEEP_OPEN",
  "OPENCODE_LIMIT_RECOVER",
  "OPENCODE_LIMIT_COOLDOWN",
  "OPENCODE_LIMIT_KILL_NODE",
]
for (const name of sharedEnvs) {
  assert.ok(sh.includes(name), `(.sh) debe honrar ${name}`)
  assert.ok(ps1.includes(name), `(.ps1) debe honrar ${name}`)
}

// Solo POSIX: espera tras SIGTERM y ventana propia. En Windows no aplican
// (Stop-Process es inmediato y el toast/consola ya es una ventana).
const posixOnlyEnvs = ["OPENCODE_LIMIT_KILL_WAIT", "OPENCODE_LIMIT_WINDOW"]
for (const name of posixOnlyEnvs) {
  assert.ok(sh.includes(name), `(.sh) debe honrar ${name}`)
  assert.ok(!ps1.includes(name), `(.ps1) no debe fingir que honra ${name}`)
}

console.log(
  `OK: ${sharedEnvs.length} constante(s) compartida(s) y ${posixOnlyEnvs.length} ` +
    "especifica(s) de POSIX verificadas en limit-notify.sh/.ps1",
)
