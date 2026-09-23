// Cliente falso de OpenCode para manejar plugins en pruebas: graba prompts,
// toasts y logs; responde sesiones sintéticas. Sin TUI ni servidor real.
export function makeFakeClient() {
  const calls = { prompts: [], toasts: [], logs: [], v2replies: 0 }
  let messagesImpl = async () => ({ data: [] })
  const subagents = new Set()
  const fake = {
    calls,
    subagents,
    failNextPrompt: false,
    setMessages(entries) {
      messagesImpl = async () => ({ data: entries })
    },
    session: {
      list: async () => ({ data: [] }),
      create: async () => ({ data: { id: "selftest-session" } }),
      get: async ({ path }) => {
        const id = path?.id ?? "s"
        return { data: { id, title: "Test session", parentID: subagents.has(id) ? "parent-1" : null } }
      },
      messages: async () => messagesImpl(),
      prompt: async ({ path, body }) => {
        if (fake.failNextPrompt) {
          fake.failNextPrompt = false
          throw new Error("prompt down")
        }
        const text = (body?.parts ?? []).map((p) => p.text ?? "").join("\n")
        calls.prompts.push({ sessionID: path?.id, text })
        return { data: { id: `prompt-${calls.prompts.length}` } }
      },
      abort: async () => ({}),
      delete: async () => ({}),
    },
    app: {
      log: async ({ body }) => {
        calls.logs.push(body)
        return {}
      },
    },
    tui: {
      showToast: async ({ body }) => {
        calls.toasts.push(body)
        return {}
      },
    },
  }
  // Transporte interno para replyPermission() (ruta v2 del plugin Telegram)
  fake._client = {
    post: async ({ url }) => {
      if (String(url).endsWith("/reply")) calls.v2replies++
      return { error: undefined }
    },
    get: async () => ({ error: undefined, data: { data: [] } }),
  }
  return fake
}

// Entrada de mensaje asistente sintética para session.messages().
export function assistantEntry(id, text, time = Date.now()) {
  return { info: { role: "assistant", id, time: { completed: time } }, parts: [{ type: "text", text }] }
}
