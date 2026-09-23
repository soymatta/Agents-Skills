// Integración del plugin SIN red ni usuario: cliente OpenCode falso +
// Bot API mockeado. Prueba los flujos que fallaban en producción:
//  1. permiso concedido/rechazado → el mensaje se EDITA con el resultado
//     (antes solo había un toast efímero y el cuerpo seguía "requerido")
//  2. N busy seguidos → UN solo "Trabajando", la final lo edita (1 mensaje)
//  3. "Trabajando" tardío (llega tras la final) → se BORRA, no duplica
// Ejecutar: npm test
import assert from "node:assert/strict"
import { setupTestHome } from "../../_harness/test-home.mjs"
import { installMockTelegram, waitFor } from "../../_harness/mock-telegram.mjs"
import { makeFakeClient, assistantEntry } from "../../_harness/fake-client.mjs"

const home = setupTestHome("tg-answers-")
const tg = installMockTelegram()
const fake = makeFakeClient()
const plugin = (await import("../notification.ts")).default
const hooks = await plugin({ client: fake, directory: home })
const fire = (type, properties) => hooks.event({ event: { type, properties } })
const workingSends = () => tg.sends().filter((c) => String(c.body.text).startsWith("Trabajando"))

const PERM_TEXT =
  "⚠️ Permiso requerido\n\nSesión: &quot;Test session&quot;\n\nHerramienta: external_directory\nPatrón: D:\\Files\\CamSimulator\\*"

// ── 1. Permiso concedido: acuse persistente en el mensaje ────────────────
{
  const n0 = tg.sends().length
  await fire("permission.asked", {
    id: "perm-grant-1",
    sessionID: "ses-perm-1",
    permission: "external_directory",
    patterns: ["D:\\Files\\CamSimulator\\*"],
  })
  assert.ok(await waitFor(() => tg.sends().length > n0), "perm notificado por Telegram")
  const permMsg = tg.sends().at(-1)
  const onceBtn = permMsg.body.reply_markup.inline_keyboard[0].find((b) => String(b.callback_data).startsWith("perm|once|"))
  assert.ok(onceBtn, "boton once presente")
  tg.queueUpdate({
    callback_query: { id: "cq-grant-1", data: onceBtn.callback_data, message: { message_id: permMsg.id, text: PERM_TEXT } },
  })
  assert.ok(await waitFor(() => tg.edits().some((e) => e.body.message_id === permMsg.id)), "mensaje de permiso editado")
  const edit = tg.edits().find((e) => e.body.message_id === permMsg.id)
  assert.ok(edit.body.text.includes("Permiso concedido"), `titulo concedido: ${edit.body.text.slice(0, 60)}`)
  assert.ok(!edit.body.text.includes("Permiso requerido"), "titulo viejo reemplazado")
  assert.deepEqual(edit.body.reply_markup, { inline_keyboard: [] }, "botones fuera en la misma edicion")
  assert.ok(tg.callbacks().some((c) => c.body.callback_query_id === "cq-grant-1"), "toast de acuse")
  assert.ok(fake.calls.v2replies >= 1, "permiso respondido a OpenCode")
  // Segundo click al mismo botón: expirado, SIN re-responder el permiso
  const v2before = fake.calls.v2replies
  const editsBefore = tg.edits().length
  tg.queueUpdate({
    callback_query: { id: "cq-grant-2", data: onceBtn.callback_data, message: { message_id: permMsg.id, text: edit.body.text } },
  })
  assert.ok(await waitFor(() => tg.callbacks().length >= 2), "segundo click contestado")
  assert.equal(fake.calls.v2replies, v2before, "no re-responde el permiso")
  assert.equal(tg.edits().length, editsBefore, "no re-edita")
}

// ── 2. Permiso rechazado ────────────────────────────────────────────────
{
  const n0 = tg.sends().length
  await fire("permission.asked", { id: "perm-rej-1", sessionID: "ses-perm-2", permission: "bash", patterns: ["rm -rf"] })
  assert.ok(await waitFor(() => tg.sends().length > n0), "perm2 notificado")
  const permMsg = tg.sends().at(-1)
  const rejBtn = permMsg.body.reply_markup.inline_keyboard[0].find((b) => String(b.callback_data).startsWith("perm|reject|"))
  tg.queueUpdate({
    callback_query: { id: "cq-rej-1", data: rejBtn.callback_data, message: { message_id: permMsg.id, text: PERM_TEXT } },
  })
  assert.ok(await waitFor(() => tg.edits().some((e) => e.body.message_id === permMsg.id)), "rechazo editado")
  const edit = tg.edits().find((e) => e.body.message_id === permMsg.id)
  assert.ok(edit.body.text.includes("Permiso rechazado"), "titulo rechazado")
}

// ── 3. N busy → un solo "Trabajando"; la final edita (1 mensaje) ────────
{
  const s = "ses-working-1"
  for (let i = 0; i < 3; i++) {
    await fire("session.status", { sessionID: s, status: { type: "busy" } })
  }
  assert.ok(await waitFor(() => workingSends().length >= 1), "trabajando enviado")
  await new Promise((r) => setTimeout(r, 600))
  assert.equal(workingSends().length, 1, `un solo Trabajando, hay ${workingSends().length}`)
  const workingId = workingSends()[0].id
  const sendsBefore = tg.sends().length
  fake.setMessages([assistantEntry("m-final-1", "listo, todo verificado")])
  await fire("session.idle", { sessionID: s })
  assert.ok(
    await waitFor(() => tg.edits().some((e) => e.body.message_id === workingId && String(e.body.text).includes("listo"))),
    "final edita el Trabajando",
  )
  await new Promise((r) => setTimeout(r, 600))
  assert.equal(tg.sends().length, sendsBefore, "la final no crea mensaje nuevo")
}

// ── 4. "Trabajando" tardío: se borra, no duplica la final ───────────────
{
  const s = "ses-late-1"
  const n0 = tg.sends().length
  tg.hangSendsWhen((body) => String(body.text).startsWith("Trabajando"))
  // NO await: el envío del "Trabajando" queda colgado a propósito
  const busyP = fire("session.status", { sessionID: s, status: { type: "busy" } })
  assert.ok(await waitFor(() => tg.sends().length > n0), "envio trabajando en vuelo")
  const lateId = tg.sends().at(-1).id
  await new Promise((r) => setTimeout(r, 300))
  fake.setMessages([assistantEntry("m-final-2", "final tardia entregada")])
  await fire("session.idle", { sessionID: s })
  assert.ok(
    await waitFor(() => tg.sends().some((c) => String(c.body.text).includes("final tardia")), 15000),
    "final entregada por via nueva",
  )
  tg.releaseHung()
  await busyP
  assert.ok(await waitFor(() => tg.deletes().some((d) => d.body.message_id === lateId)), "tardio borrado")
  assert.ok(
    !tg.edits().some((e) => e.body.message_id === lateId && String(e.body.text).includes("final tardia")),
    "tardio NO duplica la final",
  )
}

// ── 5. Gemelos + resuelto fuera (TUI): replied concilia ambos ──────────
{
  const s = "ses-twin-1"
  const nSends = tg.sends().length
  await fire("permission.asked", { id: "perm-twin-1", sessionID: s, permission: "external_directory", patterns: ["D:\\tmp\\*"] })
  assert.ok(await waitFor(() => tg.sends().length > nSends), "gemelo A notificado")
  const msgA = tg.sends().at(-1)
  // Mismo permiso, segunda instancia (debounce por instancia: esperar ventana)
  await new Promise((r) => setTimeout(r, 3200))
  await fire("permission.asked", { id: "perm-twin-1", sessionID: s, permission: "external_directory", patterns: ["D:\\tmp\\*"] })
  assert.ok(await waitFor(() => tg.sends().length > nSends + 1), "gemelo B notificado")
  const msgB = tg.sends().at(-1)
  assert.notEqual(msgA.id, msgB.id, "dos mensajes distintos")
  // Resuelto en el TUI sin tocar botones: replied concilia AMBOS
  const nEdits = tg.edits().length
  await fire("permission.replied", { sessionID: s, requestID: "perm-twin-1", reply: "always" })
  assert.ok(await waitFor(() => tg.edits().length >= nEdits + 2), "ambos conciliados")
  for (const m of [msgA, msgB]) {
    const e = tg.edits().find((x) => x.body.message_id === m.id)
    assert.ok(e && e.body.text.includes("Permiso concedido"), `gemelo ${m.id} concedido`)
    assert.ok(!e.body.text.includes("Permiso requerido"), `gemelo ${m.id} sin titulo viejo`)
    assert.deepEqual(e.body.reply_markup, { inline_keyboard: [] }, "botones fuera")
  }
  // Tap tardío en A: expirado, SIN pisar el concedido
  const tokA = msgA.body.reply_markup.inline_keyboard[0][0].callback_data
  const nEdits2 = tg.edits().length
  tg.queueUpdate({ callback_query: { id: "cq-twin-1", data: tokA, message: { message_id: msgA.id, text: "X" } } })
  assert.ok(await waitFor(() => tg.callbacks().some((c) => c.body.callback_query_id === "cq-twin-1")), "tap contestado")
  assert.equal(tg.edits().length, nEdits2, "tap tardio no re-edita")
}

console.log("OK: integracion telegram-answers")
process.exit(0)
