// Mock del Bot API de Telegram: intercepta globalThis.fetch, responde en
// memoria con message_id crecientes y graba cada llamada. Sin red.
// Soporta colgar envios (para simular flood/429) y forzar el resultado de edits.
export function installMockTelegram() {
  const calls = []
  let nextMessageId = 1000
  const pendingUpdates = []
  const hungSends = []
  let hangPredicate = null
  let sendFailer = null
  let editImpl = null
  let updateSeq = 5000

  const jsonRes = (payload) => ({ ok: true, status: 200, json: async () => payload })

  const handler = async (url, opts = {}) => {
    const u = String(url)
    const body = opts.body ? JSON.parse(String(opts.body)) : {}
    const m = u.split("/").pop().split("?")[0]
    if (m === "getUpdates") {
      return jsonRes({ ok: true, result: pendingUpdates.splice(0) })
    }
    if (m === "sendMessage") {
      const id = nextMessageId++
      calls.push({ method: m, body, id })
      if (sendFailer) {
        const fail = sendFailer(body)
        if (fail) {
          return { ok: false, status: fail.status ?? 400, json: async () => ({ description: fail.description ?? "Bad Request" }) }
        }
      }
      if (hangPredicate && hangPredicate(body)) {
        await new Promise((resolve) => hungSends.push({ body, id, resolve }))
      }
      return jsonRes({ ok: true, result: { message_id: id } })
    }
    if (m === "editMessageText") {
      calls.push({ method: m, body })
      if (editImpl) {
        const r = editImpl(body)
        if (r === "limited") return { ok: false, status: 429, json: async () => ({ parameters: { retry_after: 1 } }) }
        if (r === "failed")
          return { ok: false, status: 400, json: async () => ({ description: "Bad Request: message to edit not found" }) }
      }
      return jsonRes({ ok: true, result: true })
    }
    calls.push({ method: m, body })
    return jsonRes({ ok: true, result: true })
  }

  const prevFetch = globalThis.fetch
  globalThis.fetch = handler

  return {
    calls,
    queueUpdate(u) {
      pendingUpdates.push({ update_id: updateSeq++, ...u })
    },
    hangSendsWhen(pred) {
      hangPredicate = pred
    },
    failSendsWhen(pred, fail) {
      sendFailer = (body) => (pred(body) ? fail : null)
    },
    clearSendFailures() {
      sendFailer = null
    },
    releaseHung() {
      hungSends.splice(0).forEach((h) => h.resolve())
    },
    setEditImpl(fn) {
      editImpl = fn
    },
    sends() {
      return calls.filter((c) => c.method === "sendMessage")
    },
    edits() {
      return calls.filter((c) => c.method === "editMessageText")
    },
    deletes() {
      return calls.filter((c) => c.method === "deleteMessage")
    },
    callbacks() {
      return calls.filter((c) => c.method === "answerCallbackQuery")
    },
    restore() {
      globalThis.fetch = prevFetch
    },
  }
}

// Espera hasta que cond() sea true (poll local). Devuelve false si vence.
export async function waitFor(cond, timeoutMs = 20000, stepMs = 50) {
  const t0 = Date.now()
  for (;;) {
    if (cond()) return true
    if (Date.now() - t0 > timeoutMs) return false
    await new Promise((r) => setTimeout(r, stepMs))
  }
}
