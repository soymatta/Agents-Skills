// Integración de opencode-tui-queue: hooks manejados con cliente falso,
// HOME temporal (el state real no se toca). Prueba captura trailing,
// vaciado en idle, /queue now sin duplicar, flush, stop/start y subagentes.
// Ejecutar: npm test
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { setupTestHome } from "../../_harness/test-home.mjs"
import { makeFakeClient } from "../../_harness/fake-client.mjs"

const home = setupTestHome("tui-queue-")
const fake = makeFakeClient()
const plugin = (await import("../queue.ts")).default
const hooks = await plugin({ client: fake })
const stateFile = join(home, ".config", "opencode", ".opencode-queue.json")
const entries = () => JSON.parse(readFileSync(stateFile, "utf-8")).entries
const fire = (type, properties) => hooks.event({ event: { type, properties } })
const chatMsg = (sessionID, messageID, text) =>
  hooks["chat.message"]({ sessionID, messageID }, { parts: [{ type: "text", text }] })
const cmd = (sessionID, args) =>
  hooks["command.execute.before"]({ command: "queue", sessionID, arguments: args }, { parts: [{ type: "text", text: `/queue ${args}` }] })

// ── A. trailing con sesion ocupada → encola y oculta el mensaje ─────────
{
  await fire("session.status", { sessionID: "s1", status: { type: "busy" } })
  const out = { parts: [{ type: "text", text: "revisa esto /queue" }] }
  await hooks["chat.message"]({ sessionID: "s1", messageID: "m1" }, out)
  assert.equal(out.parts.length, 1, "partes reemplazadas")
  assert.equal(out.parts[0].synthetic, true, "placeholder sintetico")
  assert.equal(out.parts[0].ignored, true, "placeholder ignorado")
  assert.ok(fake.calls.toasts.some((t) => String(t.message).includes("Encolado")), "toast de acuse")
  assert.deepEqual(entries().map((e) => e.text), ["revisa esto"], "texto limpio encolado")
  // idle → se promueve EXACTAMENTE una vez con el texto encolado
  await fire("session.status", { sessionID: "s1", status: { type: "idle" } })
  assert.equal(fake.calls.prompts.length, 1, "un prompt promovido")
  assert.deepEqual(fake.calls.prompts[0], { sessionID: "s1", text: "revisa esto" })
  assert.equal(entries().length, 0, "cola vacia tras promover")
  // el hook del mensaje reinyectado NO lo re-encola (bucle)
  const out2 = { parts: [{ type: "text", text: "revisa esto" }] }
  await hooks["chat.message"]({ sessionID: "s1", messageID: "prompt-1" }, out2)
  assert.equal(entries().length, 0, "sin re-encolado")
}

// ── B. trailing con sesion libre → no captura ───────────────────────────
{
  const out = { parts: [{ type: "text", text: "esto no /queue" }] }
  await chatMsg("s2", "m2", "esto no /queue")
  assert.equal(out.parts[0].text, "esto no /queue", "mensaje intacto")
  assert.equal(entries().length, 0, "nada encolado")
}

// ── C. /queue now ocupada → UNA sola entrada (regresion: se duplicaba) ──
{
  await fire("session.status", { sessionID: "s3", status: { type: "busy" } })
  const out = { parts: [] }
  await hooks["command.execute.before"]({ command: "queue", sessionID: "s3", arguments: "now texto urgente" }, out)
  assert.equal(entries().filter((e) => e.sessionID === "s3").length, 1, "now encola una sola vez")
  assert.equal(entries().find((e) => e.sessionID === "s3").text, "texto urgente")
  assert.ok(fake.calls.toasts.some((t) => String(t.message).includes("primera posición")), "toast de posicion")
  // idle la envia y la saca
  await fire("session.status", { sessionID: "s3", status: { type: "idle" } })
  assert.ok(fake.calls.prompts.some((p) => p.sessionID === "s3" && p.text === "texto urgente"), "now promovido")
}

// ── D. flush descarta ───────────────────────────────────────────────────
{
  await fire("session.status", { sessionID: "s4", status: { type: "busy" } })
  await chatMsg("s4", "m4", "pendiente uno /queue")
  await chatMsg("s4", "m5", "pendiente dos /queue")
  assert.equal(entries().filter((e) => e.sessionID === "s4").length, 2, "dos encolados")
  await cmd("s4", "flush")
  assert.equal(entries().filter((e) => e.sessionID === "s4").length, 0, "flush vacia")
  assert.ok(fake.calls.toasts.some((t) => String(t.message).includes("Flush: 2 descartados")), "toast de flush")
  await fire("session.status", { sessionID: "s4", status: { type: "idle" } })
}

// ── E. stop/start ───────────────────────────────────────────────────────
{
  await cmd("s5", "stop")
  assert.equal(JSON.parse(readFileSync(stateFile, "utf-8")).stopped, true, "pausado")
  await fire("session.status", { sessionID: "s5", status: { type: "busy" } })
  await chatMsg("s5", "m6", "no debe entrar /queue")
  assert.equal(entries().filter((e) => e.sessionID === "s5").length, 0, "pausado no encola")
  await cmd("s5", "start")
  await chatMsg("s5", "m7", "ahora si /queue")
  assert.equal(entries().filter((e) => e.sessionID === "s5").length, 1, "reanuda y encola")
  await cmd("s5", "flush")
  await fire("session.status", { sessionID: "s5", status: { type: "idle" } })
}

// ── F. subagente: ni captura ni consume ─────────────────────────────────
{
  fake.subagents.add("sub-1")
  const out = { parts: [{ type: "text", text: "hijo /queue" }] }
  await hooks["chat.message"]({ sessionID: "sub-1", messageID: "m8" }, out)
  assert.equal(out.parts[0].text, "hijo /queue", "mensaje de subagente intacto")
  assert.ok(!entries().some((e) => e.sessionID === "sub-1"), "nada del subagente")
}

// ── G. list / front / help responden por toast ──────────────────────────
{
  await fire("session.status", { sessionID: "s7", status: { type: "busy" } })
  await chatMsg("s7", "m9", "ver la lista /queue")
  const t0 = fake.calls.toasts.length
  await cmd("s7", "list")
  assert.ok(fake.calls.toasts.slice(t0).some((t) => String(t.message).includes("ver la lista")), "list muestra")
  await cmd("s7", "front")
  assert.ok(fake.calls.toasts.slice(t0).some((t) => String(t.message).includes("Siguiente:")), "front muestra")
  await cmd("s7", "inventado")
  assert.ok(fake.calls.toasts.slice(t0).some((t) => String(t.message).includes("/queue list")), "help muestra")
  await cmd("s7", "flush")
  await fire("session.status", { sessionID: "s7", status: { type: "idle" } })
}

// ── H. captura automática por defecto (sin sufijo) ──────────────────────
{
  await fire("session.status", { sessionID: "s8", status: { type: "busy" } })
  const out = { parts: [{ type: "text", text: "esto entra solo" }] }
  await hooks["chat.message"]({ sessionID: "s8", messageID: "m10" }, out)
  assert.equal(out.parts[0].ignored, true, "auto-oculto")
  assert.ok(entries().some((e) => e.sessionID === "s8" && e.text === "esto entra solo"), "auto-encolado")
  // Con sufijo se limpia igual
  const out2 = { parts: [{ type: "text", text: "con sufijo /queue" }] }
  await hooks["chat.message"]({ sessionID: "s8", messageID: "m11" }, out2)
  assert.ok(entries().some((e) => e.sessionID === "s8" && e.text === "con sufijo"), "sufijo limpio")
  // Modo sufijo explícito (flag off): el texto plano pasa, el sufijo encola
  const { CONFIG } = await import("../queue.ts")
  CONFIG.captureAllBusy = false
  try {
    const out3 = { parts: [{ type: "text", text: "pasa al modelo" }] }
    await hooks["chat.message"]({ sessionID: "s8", messageID: "m12" }, out3)
    assert.equal(out3.parts[0].text, "pasa al modelo", "flag off: intacto")
    assert.ok(!entries().some((e) => e.text === "pasa al modelo"), "flag off: no encola")
  } finally {
    CONFIG.captureAllBusy = true
  }
  await cmd("s8", "flush")
  await fire("session.status", { sessionID: "s8", status: { type: "idle" } })
}

console.log("OK: integracion tui-queue")
process.exit(0)
