// Smoke de la lógica pura de opencode-tui-queue: sin red, sin TUI.
// Ejecutar: npm test
import assert from "node:assert/strict"
import { mkdtempSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import {
  defaultState,
  enqueueText,
  extractTrailingQueue,
  flushFor,
  frontOf,
  isQueueCommand,
  listOf,
  loadQueueFrom,
  makeId,
  parseQueueArgs,
  promoteOne,
  removeById,
  saveQueueRaw,
} from "../queue.ts"

// ── cola: enqueue / promote / list / front / remove / flush ─────────────
{
  const st = defaultState()
  assert.deepEqual(st, { alwaysOn: true, stopped: false, entries: [] }, "estado inicial")
  const a = enqueueText(st, "s1", "primero")
  const b = enqueueText(st, "s1", "segundo")
  enqueueText(st, "s2", "otra sesion")
  assert.equal(st.entries.length, 3, "3 entradas")
  assert.deepEqual(
    listOf(st, "s1").map((e) => e.text),
    ["primero", "segundo"],
    "list filtra por sesion",
  )
  assert.equal(listOf(st, null).length, 3, "list null = todas")
  assert.equal(frontOf(st, "s1")?.text, "primero", "front = mas antiguo")
  assert.equal(promoteOne(st, "s1")?.id, a.id, "promote saca el mas antiguo")
  assert.equal(promoteOne(st, "s9"), null, "promote vacio = null")
  assert.equal(removeById(st, b.id), true, "remove existente")
  assert.equal(removeById(st, "nope"), false, "remove ausente")
  assert.equal(flushFor(st, "s2"), 1, "flush por sesion")
  enqueueText(st, "s1", "x")
  enqueueText(st, "s2", "y")
  assert.equal(flushFor(st, null), 2, "flush all")
  assert.equal(st.entries.length, 0, "cola vacia")
}

// ── poda: lo mas viejo se descarta al pasar el maximo ───────────────────
{
  const st = defaultState()
  for (let i = 0; i < 30; i++) enqueueText(st, "s1", `m${i}`, 25)
  assert.equal(st.entries.length, 25, "tope 25")
  assert.equal(st.entries[0].text, "m5", "se podan los viejos")
  assert.equal(st.entries.at(-1).text, "m29", "se conserva lo nuevo")
}

// ── extractTrailingQueue ────────────────────────────────────────────────
assert.deepEqual(extractTrailingQueue("haz esto /queue"), { text: "haz esto", queueIt: true }, "trailing basico")
assert.deepEqual(extractTrailingQueue("hola"), { text: "hola", queueIt: false }, "sin marca")
assert.deepEqual(extractTrailingQueue("mira /queue esto"), { text: "mira /queue esto", queueIt: false }, "marca en medio no vale")
assert.deepEqual(extractTrailingQueue("  /queue  "), { text: "", queueIt: true }, "solo la marca")
assert.deepEqual(extractTrailingQueue("a /queue /queue"), { text: "a", queueIt: true }, "doble marca colapsa")
assert.deepEqual(extractTrailingQueue("foo/queue"), { text: "foo/queue", queueIt: false }, "sin espacio no vale")
assert.deepEqual(extractTrailingQueue("foo /queue\n"), { text: "foo", queueIt: true }, "salto final")

// ── parseQueueArgs ──────────────────────────────────────────────────────
assert.deepEqual(parseQueueArgs("list"), { op: "list", text: "", all: false })
assert.deepEqual(parseQueueArgs("LIST"), { op: "list", text: "", all: false }, "case-insensitive")
assert.deepEqual(parseQueueArgs("front"), { op: "front", text: "", all: false })
assert.deepEqual(parseQueueArgs("now haz esto ya"), { op: "now", text: "haz esto ya", all: false })
assert.deepEqual(parseQueueArgs("now"), { op: "now", text: "", all: false })
assert.deepEqual(parseQueueArgs("stop"), { op: "stop", text: "", all: false })
assert.deepEqual(parseQueueArgs("start"), { op: "start", text: "", all: false })
assert.deepEqual(parseQueueArgs("flush"), { op: "flush", text: "", all: false })
assert.deepEqual(parseQueueArgs("flush all"), { op: "flush", text: "", all: true })
assert.deepEqual(parseQueueArgs("flush ALL"), { op: "flush", text: "", all: true })
assert.deepEqual(parseQueueArgs(""), { op: "help", text: "", all: false })
assert.deepEqual(parseQueueArgs("foo"), { op: "help", text: "", all: false })

// ── isQueueCommand ──────────────────────────────────────────────────────
assert.equal(isQueueCommand("/queue list"), true)
assert.equal(isQueueCommand("  /queue"), true)
assert.equal(isQueueCommand("/queuex"), false, "prefijo mas largo no")
assert.equal(isQueueCommand("x /queue"), false, "no leading")

// ── makeId: unicos ──────────────────────────────────────────────────────
assert.notEqual(makeId(), makeId(), "ids unicos")

// ── persistencia: roundtrip + corrupto + ausente ────────────────────────
{
  const dir = mkdtempSync(join(tmpdir(), "queue-state-"))
  const file = join(dir, "q.json")
  assert.deepEqual(loadQueueFrom(join(dir, "no-existe.json")), defaultState(), "ausente = default")
  const st = defaultState()
  enqueueText(st, "s1", "persistido")
  saveQueueRaw(st, file)
  const back = loadQueueFrom(file)
  assert.equal(back.entries.length, 1, "roundtrip conserva")
  assert.equal(back.entries[0].text, "persistido", "texto intacto")
  assert.equal(back.alwaysOn, true, "flags intactos")
  writeFileSync(file, "{corrupto")
  assert.deepEqual(loadQueueFrom(file), defaultState(), "corrupto = default")
}

console.log("OK: smoke tui-queue")
