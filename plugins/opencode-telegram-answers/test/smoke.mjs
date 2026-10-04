// Smoke test: valida las funciones puras del plugin sin tocar Telegram.
// Requiere Node >= 22.6 (importa el .ts directamente con type stripping).
// Ejecutar: npm test
import assert from "node:assert/strict"
import {
  buildPermKeyboard,
  htmlToPlainText,
  isFinalAlreadyDelivered,
  isSubagentSession,
  isWorkingEntryFresh,
  markdownToHtml,
  nextWorkingPeriod,
  parseCallbackData,
  permInfoFromEvent,
  permOutcomeText,
  repliedInfoFromEvent,
  replyPermission,
  shouldEditLateWorking,
  splitHtmlChunks,
  workingText,
} from "../notification.ts"

// ── markdownToHtml ─────────────────────────────────────────────────────
{
  const html = markdownToHtml("**bold** y *ital* y `code`")
  assert.ok(html.includes("<b>bold</b>"), "negrita")
  assert.ok(html.includes("<i>ital</i>"), "cursiva")
  assert.ok(html.includes("<code>code</code>"), "codigo inline")
}

// Encabezados
assert.ok(markdownToHtml("## Título").includes("<b>Título</b>"), "heading")

// Listas
assert.ok(markdownToHtml("- a\n- b").includes("\u2022 a"), "lista no ordenada")

// Citas
assert.ok(markdownToHtml("> nota").includes("<i>\u25b8 nota</i>"), "cita")

// Tachado
assert.ok(markdownToHtml("~~x~~").includes("<s>x</s>"), "tachado")

// Enlace
assert.ok(markdownToHtml("[texto](https://example.com)").includes('<a href="https://example.com">texto</a>'), "enlace")

// Bloque de codigo (no debe romper el HTML y debe escapar contenido)
{
  const html = markdownToHtml("```\nSELECT 1 < 2;\n```")
  assert.ok(html.includes("<pre>SELECT 1 &lt; 2;</pre>"), "bloque de codigo escapado")
}

// Sin saltos de linea triples
assert.ok(!markdownToHtml("a\n\n\n\nb").includes("\n\n\n"), "max 2 saltos")

// ── isSubagentSession ───────────────────────────────────────────────────
assert.equal(isSubagentSession("abc", "Tarea principal"), true, "parentID => subagente")
assert.equal(isSubagentSession(null, "Eval exploración y romper (@general subagent)"), true, "titulo subagente")
assert.equal(isSubagentSession(undefined, "Refactor modulo (@build subagent)"), true, "titulo subagente 2")
assert.equal(isSubagentSession(null, "Citaflex"), false, "sesion normal")
assert.equal(isSubagentSession(undefined, ""), false, "sin titulo")
assert.equal(isSubagentSession("", null), false, "parentID vacio")

// ── permInfoFromEvent ──────────────────────────────────────────────────
// v1 (permission.updated)
assert.deepEqual(permInfoFromEvent("permission.updated", { id: "p1", sessionID: "s1", title: "Edit file", type: "edit", pattern: "src/a.ts" }), {
  permID: "p1",
  sessionID: "s1",
  tool: "Edit file",
  pattern: "src/a.ts",
  variant: "v1",
})

// v2 (permission.asked)
assert.deepEqual(
  permInfoFromEvent("permission.asked", { id: "p2", sessionID: "s2", permission: "bash", patterns: ["rm -rf *", "ls"] }),
  { permID: "p2", sessionID: "s2", tool: "bash", pattern: "rm -rf *, ls", variant: "v2" },
)

// v2 resource (permission.v2.asked) sin patterns pero con resources
assert.deepEqual(
  permInfoFromEvent("permission.v2.asked", { id: "p3", sessionID: "s3", action: "write", resources: ["a.txt"] }),
  { permID: "p3", sessionID: "s3", tool: "write", pattern: "a.txt", variant: "v2" },
)

// Sin id → null (no se puede responder)
assert.equal(permInfoFromEvent("permission.updated", { title: "x" }), null)
// Sin tool → null
assert.equal(permInfoFromEvent("permission.updated", { id: "p4", title: "" }), null)

// ── parseCallbackData ──────────────────────────────────────────────────
assert.deepEqual(parseCallbackData("perm|once|tok3n"), { reply: "once", token: "tok3n" })
assert.deepEqual(parseCallbackData("perm|always|tok3n"), { reply: "always", token: "tok3n" })
assert.deepEqual(parseCallbackData("perm|reject|tok3n"), { reply: "reject", token: "tok3n" })
assert.equal(parseCallbackData("perm|maybe|tok3n"), null, "respuesta invalida")
assert.equal(parseCallbackData("otro|once|tok3n"), null, "prefijo invalido")
assert.equal(parseCallbackData("perm|once"), null, "faltan partes")
assert.equal(parseCallbackData(""), null, "vacio")

// ── buildPermKeyboard ──────────────────────────────────────────────────
{
  const kb = buildPermKeyboard("tok3n")
  assert.equal(kb.inline_keyboard.length, 1, "una fila de botones")
  assert.equal(kb.inline_keyboard[0].length, 3, "3 botones: once/always/reject")
  const data = kb.inline_keyboard[0].map((b) => b.callback_data)
  assert.ok(data.includes("perm|once|tok3n"), "boton once")
  assert.ok(data.includes("perm|always|tok3n"), "boton always")
  assert.ok(data.includes("perm|reject|tok3n"), "boton reject")
  // callback_data <= 64 bytes (límite de Telegram)
  for (const c of data) assert.ok(Buffer.byteLength(c) <= 64, `callback_data corto: ${c}`)
}

// ── transformInline / escape ───────────────────────────────────────────
assert.ok(markdownToHtml("a < b && c").includes("a &lt; b &amp;&amp; c"), "escape HTML")

// ── Regresión 400 "can't parse entities" (Telegram rechaza anidados del
// mismo tipo y cruces: <b><b>, <i><i>, </b> donde iba </i>) ─────────────
{
  // Validador: pila estricta + prohibido anidar el mismo tag + `code`
  // atómico (Telegram: ni dentro de formato ni con formato dentro)
  const wellFormed = (html, label) => {
    const stack = []
    for (const m of html.matchAll(/<\/?([a-zA-Z][a-zA-Z0-9]*)[^>]*>/g)) {
      const full = m[0]
      const name = m[1].toLowerCase()
      if (full.startsWith("</")) {
        assert.equal(stack.pop(), name, `${label}: cierre </${name}> con pila [${stack}] en ${html.slice(0, 80)}`)
      } else if (!["br", "hr", "img", "meta"].includes(name)) {
        if (name === "code") assert.deepEqual(stack, [], `${label}: <code> anidado en [${stack}]`)
        assert.ok(!stack.includes(name), `${label}: <${name}> anidado en ${html.slice(0, 80)}`)
        stack.push(name)
      }
    }
    assert.deepEqual(stack, [], `${label}: sin etiquetas abiertas en ${html.slice(0, 80)}`)
  }

  // Patrones exactos del fallo en producción
  const cases = [
    '| 2.1 | ¶23/¶30/¶76 | **Pregunta y objetivo piden causalidad ("¿De qué manera...**',
    '*"Las respuestas Likert exportadas desde Google Forms **ya se encuentran en formato numérico (1 a 5)**"*',
    '**razonamiento**. Error de *mejor* en una definición clave.\n• **¶8: "si *infiere* o no en el ejercicio prof**',
    '*"considerando el **riego** del sesgo de automatización"* -> **riesgo**.',
    '## **3.5 Nombres propios en minúscu** con **más**',
    '> *nota* con **negrita** y *otra*',
    '**a *b** c*',
    '***triple*** y **doble**',
    'sin cierre *asi queda',
    '**sin cierre asi queda',
    '[texto con **bold**](https://example.com/a*b)',
    '```\n**no** *tocar* `ni` esto\n```',
    // Regresión `</code>` vs `</i>`: código con formato alrededor y dentro
    'DONE. Error `400` de entidades con *cursiva* y **negrita `mixta`** fin',
    'texto *itálico* con `código` y **bold `más`**',
    '## título con `código` y **bold**',
    '> nota con `código` y *ital*',
    '[`x` y](https://example.com)',
    'backtick huérfano `asi queda',
    '**bold con `code` dentro** y *ital con `code` dentro*',
  ]
  for (const c of cases) wellFormed(markdownToHtml(c), JSON.stringify(c.slice(0, 40)))

  // Wrapper de encabezado/cita no duplica el tag interno
  assert.ok(!markdownToHtml("## **T**").includes("<b><b>"), "heading sin <b><b>")
  assert.ok(!markdownToHtml("> *n*").includes("<i><i>"), "cita sin <i><i>")
  // Marcadores huérfanos quedan literales (sin etiquetas abiertas)
  assert.ok(!markdownToHtml("a *b c").includes("<i>"), "cursiva huerfana literal")
  assert.ok(!markdownToHtml("a **b c").includes("<b>"), "negrita huerfana literal")
  // htmlToPlainText desmonta sin dejar restos
  assert.equal(htmlToPlainText("<b>hola</b> &quot;mundo&quot; &amp; <i>x</i>"), 'hola "mundo" & x', "plain fallback")
}

// ── splitHtmlChunks (sin truncado: techo absoluto 4096 = limite Telegram) ─
{
  // Bajo el límite: un solo trozo, idéntico
  assert.deepEqual(splitHtmlChunks("corto"), ["corto"], "texto corto en un trozo")
  // Presupuesto completo: 4096 en UN trozo (antes se partía en 4000)
  assert.equal(splitHtmlChunks("z".repeat(4096)).length, 1, "4096 en un trozo")
  {
    const two = splitHtmlChunks("z".repeat(4097))
    assert.equal(two.length, 2, "4097 en dos trozos")
    for (const p of two) assert.ok(p.length <= 4096, `trozo <= 4096: ${p.length}`)
  }
  // Texto plano largo (sin HTML): se parte en trozos que unidos dan el original
  const long = Array.from({ length: 9000 }, (_, i) => String.fromCharCode(97 + (i % 26))).join("")
  const parts = splitHtmlChunks(long)
  assert.ok(parts.length >= 3, `unión de partes: ${parts.length}`)
  for (const p of parts) assert.ok(p.length <= 4096, `trozo <= 4096: ${p.length}`)
  assert.equal(parts.join(""), long, "el texto completo se conserva (nada truncado)")
  // Etiquetas abiertas a través del corte: se cierran y se reabren
  {
    const h = "<b>inicio</b> " + "x".repeat(3000) + " <i>cursiva</i> " + "y".repeat(1500)
    const chunked = splitHtmlChunks(h)
    assert.ok(chunked.length > 1, "se parte en varios trozos")
    for (const c of chunked) {
      assert.ok(!/<[^>]*$/.test(c), `sin "<" colgante: ${c.slice(-30)}`)
      const opens = [...c.matchAll(/<([a-zA-Z][a-zA-Z0-9]*)[^>]*>/g)].map((m) => m[1])
      const closes = [...c.matchAll(/<\/([a-zA-Z][a-zA-Z0-9]*)>/g)].map((m) => m[1])
      const balance = opens.length - closes.length
      assert.ok(balance === 0, `HTML balanceado en el trozo: ${balance}`)
    }
  }
  // Anidado adverso: ningún trozo supera 4096 ni con cierres incluidos
  {
    const h = "<b>" + "palabra ".repeat(1200) + "<i>anidada " + "x".repeat(2500) + "</i> cola " + "y".repeat(1500) + "</b>"
    const chunked = splitHtmlChunks(h)
    assert.ok(chunked.length > 1, "adverso se parte")
    for (const c of chunked) assert.ok(c.length <= 4096, `adverso <= 4096: ${c.length}`)
  }
  // Corte nunca parte etiqueta (<a href="..."> lleva espacio) ni entidad
  // (&quot;) a medias: eso era 400 "can't parse entities" en producción
  {
    const link = '<a href="https://example.com/una/ruta/muy/larga/con/muchos/segmentos">texto del enlace</a> '
    const h = "<b>cabecera</b> " + link.repeat(60) + 'cola &quot;citada&quot; ' + "z".repeat(3000)
    const chunked = splitHtmlChunks(h)
    assert.ok(chunked.length > 1, "enlaces se parten")
    for (const c of chunked) {
      assert.ok(!/<[^>]*$/.test(c), "sin \"<\" colgante")
      const lt = c.lastIndexOf("<")
      assert.ok(lt === -1 || c.indexOf(">", lt) !== -1, "sin etiqueta partida")
      const amp = c.lastIndexOf("&")
      assert.ok(amp === -1 || c.indexOf(";", amp) !== -1, "sin entidad partida")
      assert.ok(c.length <= 4096, `trozo <= 4096: ${c.length}`)
    }
  }
  // Límite personalizado
  assert.deepEqual(splitHtmlChunks("abcdef", 3).join(""), "abcdef", "limite custom")
}

// ── workingText (indicador "Trabajando ...") ───────────────────────────
{
  const t = workingText("...")
  assert.ok(t.startsWith("Trabajando"), "label")
  assert.ok(t.endsWith("..."), "frame")
  assert.ok(!t.includes("<"), "sin HTML escapado")
  // Si el label llevara caracteres especiales, deben quedar escapados
  const frame = "<b>&"
  const t2 = workingText(frame)
  assert.ok(t2.includes("&lt;b&gt;&amp;"), "label escapado")
}

// ── replyPermission (v1 -> v2 -> lookup+retry -> permission2) ────────────
{
  const btn = { sessionID: "s1", permID: "per_x", time: Date.now() }
  const ok = { error: undefined }
  const err = (status) => ({ error: { message: "nope" }, response: { status } })
  const notFound = { error: { _tag: "PermissionNotFoundError", requestID: "per_x" }, response: { status: 404 } }
  const noGet = async () => ({ error: undefined, data: { data: [] } })

  // v1 directa funciona: no toca la ruta v2
  {
    const inner = { post: async () => { throw new Error("no debe llamarse") }, get: noGet }
    const client = { postSessionIdPermissionsPermissionId: async () => ok, client: inner }
    await replyPermission(client, btn, "once")
  }
  // v1 falla -> la ruta v2 interna (bajo `_client`, runtime SDK 1.18.x) responde
  {
    let v2called = false
    const post = async ({ url }) => {
      if (url.includes("/api/session/") && url.endsWith("/reply")) { v2called = true; return ok }
      throw new Error("ruta equivocada: " + url)
    }
    const client = { postSessionIdPermissionsPermissionId: async () => err(404), _client: { post, get: noGet } }
    await replyPermission(client, btn, "always")
    assert.ok(v2called, "fallback v2 usado cuando v1 falla (404)")
  }
  // Sin metodo v1 -> v2 interna directo (candidato `client`, no `_client`)
  {
    const post = async () => ok
    await replyPermission({ client: { post, get: noGet } }, btn, "reject")
    await replyPermission({ api: { post, get: noGet } }, btn, "once")
  }
  // 404 directo + el pendiente vive en otra sesión -> reintenta con la real
  {
    const calls = []
    const post = async ({ path }) => {
      calls.push(path.sessionID)
      return path.sessionID === "s-real" ? ok : notFound
    }
    const get = async ({ url }) => {
      if (url === "/api/session/{sessionID}/permission") {
        return { error: undefined, data: { data: [{ id: "per_x", sessionID: "s-real" }] } }
      }
      return { error: undefined, data: { data: [] } }
    }
    const client = { postSessionIdPermissionsPermissionId: async () => err(404), _client: { post, get } }
    await replyPermission(client, btn, "once")
    assert.deepEqual(calls, ["s1", "s-real"], "reintenta con la sesión dueña")
  }
  // 404 directo + ya no está en pendientes -> error claro
  {
    const post = async () => notFound
    const client = { postSessionIdPermissionsPermissionId: async () => err(404), _client: { post, get: noGet } }
    await assert.rejects(
      () => replyPermission(client, btn, "once"),
      /ya no está entre los pendientes/,
      "informa permiso consumido",
    )
  }
  // sin transporte interno -> mensaje claro
  {
    assert.equal((await replyPermission({}, btn, "once").then(() => "ok", (e) => e.message)).includes("no inner http client"), true)
  }
}

// ── isWorkingEntryFresh (pendientes "Trabajando", TTL = 30 min) ─────────
{
  const now = Date.now()
  assert.equal(isWorkingEntryFresh({ time: now }, now), true, "fresca")
  assert.equal(isWorkingEntryFresh({ time: now - 29 * 60 * 1000 }, now), true, "casi al limite")
  assert.equal(isWorkingEntryFresh({ time: now - 31 * 60 * 1000 }, now), false, "caducada")
  assert.equal(isWorkingEntryFresh(undefined, now), false, "ausente")
}

// ── nextWorkingPeriod (backoff de animación: base 1500, techo 6000) ─────
{
  assert.equal(nextWorkingPeriod(1500, false), 1500, "sin 429 mantiene base")
  assert.equal(nextWorkingPeriod(1500, true), 3000, "429 duplica")
  assert.equal(nextWorkingPeriod(3500, true), 6000, "429 respeta techo")
  assert.equal(nextWorkingPeriod(6000, true), 6000, "techo estable")
  assert.equal(nextWorkingPeriod(3000, false), 1500, "recupera a base")
}

// ── shouldEditLateWorking (regresión: bucle de mensaje anterior) ────────
{
  const now = Date.now()
  const ttl = 30 * 60 * 1000
  // Sin final que consultar: nunca editar
  assert.equal(shouldEditLateWorking(undefined, 0, now, ttl), false, "sin final: no editar")
  // Final DENTRO del turno busy actual (time > turnStart): editar a la final
  assert.equal(shouldEditLateWorking({ time: now - 1000 }, now - 5000, now, ttl), true, "final del turno actual: editar")
  // Final del turno ANTERIOR a este busy (time < turnStart): NO re-enviar
  assert.equal(shouldEditLateWorking({ time: now - 6000 }, now - 5000, now, ttl), false, "final previa al busy: no re-enviar")
  // Final caducada (fuera del TTL): no editar aunque sea del turno actual
  assert.equal(shouldEditLateWorking({ time: now - ttl - 1000 }, now - 5000, now, ttl), false, "final caducada: no editar")
  // Sin referencia de turno (turnStart 0): comportamiento previo por edad
  assert.equal(shouldEditLateWorking({ time: now - 1000 }, 0, now, ttl), true, "sin turnStart: vale por edad")
}

// ── permOutcomeText (acuse persistente del permiso) ─────────────────────
{
  const orig = "⚠️ Permiso requerido\n\nSesión: &quot;X&quot;\n\nHerramienta: bash"
  const g = permOutcomeText(orig, "granted")
  assert.ok(g.includes("Permiso concedido"), "concedido")
  assert.ok(!g.includes("Permiso requerido"), "titulo viejo fuera")
  assert.ok(g.includes('Sesión: &quot;X&quot;'), "resto intacto")
  const r = permOutcomeText(orig, "rejected")
  assert.ok(r.includes("Permiso rechazado"), "rechazado")
  const e = permOutcomeText(orig, "expired")
  assert.ok(e.includes("no vigente o ya respondido"), "expirado")
  // Sin marcador (labels personalizados): antepone el resultado
  const fb = permOutcomeText("otro formato", "granted")
  assert.ok(fb.startsWith("Permiso concedido") || fb.includes("Permiso concedido"), "fallback antepone")
  assert.ok(fb.includes("otro formato"), "fallback conserva")
}

// ── isFinalAlreadyDelivered (tardío: borrar, no duplicar) ───────────────
{
  const now = Date.now()
  assert.equal(isFinalAlreadyDelivered({ time: now - 1000 }, now - 5000), true, "final del turno: entregada")
  assert.equal(isFinalAlreadyDelivered({ time: now - 6000 }, now - 5000), false, "final vieja: no es de este turno")
  assert.equal(isFinalAlreadyDelivered(undefined, now - 5000), false, "sin final")
}

// ── repliedInfoFromEvent (conciliación de resueltos fuera de Telegram) ──
{
  assert.deepEqual(repliedInfoFromEvent({ sessionID: "s", requestID: "p1", reply: "always" }), { permID: "p1", kind: "granted" }, "v2 always")
  assert.deepEqual(repliedInfoFromEvent({ sessionID: "s", requestID: "p1", reply: "once" }), { permID: "p1", kind: "granted" }, "v2 once")
  assert.deepEqual(repliedInfoFromEvent({ sessionID: "s", requestID: "p1", reply: "reject" }), { permID: "p1", kind: "rejected" }, "v2 reject")
  assert.deepEqual(repliedInfoFromEvent({ sessionID: "s", permissionID: "p2", response: "once" }), { permID: "p2", kind: "granted" }, "v1 plano")
  assert.deepEqual(
    repliedInfoFromEvent({ data: { sessionID: "s", requestID: "p3", reply: "reject" } }),
    { permID: "p3", kind: "rejected" },
    "v2 anidado",
  )
  assert.equal(repliedInfoFromEvent({ sessionID: "s", reply: "once" }), null, "sin id")
  assert.equal(repliedInfoFromEvent({ sessionID: "s", requestID: "p4", reply: "maybe" }), null, "respuesta desconocida")
  assert.equal(repliedInfoFromEvent({}), null, "vacio")
}

console.log("OK: todos los tests pasaron")