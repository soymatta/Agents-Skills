# Análisis y Mejoras — Agents & Skills

Análisis read-only de los 5 agentes, las skills de primer parte, el instalador (`setup.py`), el pipeline CI y el frontend web (`web/`). Código verificado contra la realidad de los scripts (no solo contra lo que dice la documentación).

---

## 0. Hallazgos transversales (los más impactantes)

Estos problemas se repiten en casi todas las skills y son los que más valor desbloquean si se atacan primero.

### 0.1 No hay contrato de datos entre skills (el "pipeline" es un apretón de manos, no una API)
Cada skill se autodescribe como parte de una cadena, pero **ninguna emite un artefacto estructurado que la siguiente consuma**:
- `academic-source-search` → `citation-formatter`: la búsqueda produce una **tabla Markdown legible** (y un template YAML que nunca se ordena guardar); `citation-formatter` no define qué input recibe. Si se pierde el contexto, la cadena se rompe en silencio.
- `backtest-run` → `backtest-validate`: `backtest-run` no genera ningún `results.json`; `backtest-validate` consume **flags CLI escritos a mano** (`--win-rate`, `--total-trades`…). Cualquier error de transcripción cambia el veredicto.
- `research-pipeline` → `telegram-notify`: la notificación es un ejemplo copiado, no un helper compartido.

**Mejora sugerida:** definir un `results.json` / `sources.yaml` autodescriptivo por pipeline y un `NotificationBroker` único (un import, un check de credenciales, una plantilla de mensaje). Un solo cambio arregla todos los handoffs rotos y la duplicación de credenciales.

### 0.2 Descriptions de frontmatter desproporcionadas vs. beneficio
Varias skills (especialmente `metric-optimizer`, `telegram-notify`, `research-pipeline`, `osint`, y los agentes `jobfinder`, `vault`, `paper-researcher`) tienen decenas de líneas de triggers. La guía de `skill-creator` recomienda ~100 palabras. Descripciones largas reducen la fidelidad de disparo de **todas** las skills (compiten por contexto). **Sugerencia transversal:** podar a 1-2 líneas de contexto + disparadores clave; mover la lista exhaustiva a una sección del cuerpo.

### 0.3 Estados de persistencia inconsistentes
- `metric-optimizer` → `.opencode/decisions/goal_state.json`
- `roadmaps` → `.roadmap-state` + `roadmap.md` (único con regla de obsolescencia buena)
- `agent-self-improver` → **ninguno** (no puede "detectar patrones entre sesiones")
- `project-analyzer` → **ninguno** (no puede reportar deltas)

**Sugerencia:** convención única `.opencode/state/<skill>.json` con una regla de staleness compartida (copiar la de roadmaps).

### 0.4 Esquema de evals roto
`roadmaps/evals/evals.json` usa `"expectations"`, pero el tooling de `skill-creator` espera `assertions` → los evals de roadmaps son peso muerto bajo el propio framework de gradación del repo. **Sugerencia:** `expectations` → `assertions`.

### 0.5 Números mágicos contradictorios y lógica unidireccional
- `metric-optimizer`: "switch paradigm after **3** failures" (frontmatter y tabla) vs "**5** flat iterations" (reglas). Tres números distintos en un mismo archivo.
- `backtest-run` dice "win rate > 80% → check look-ahead"; `backtest-validate` dispara red flag solo a `> 90%`. Contradictorios entre sí.
- `metric-optimizer` solo maximiza (`current >= target`, `best = max(...)`), pero sus triggers incluyen "minimize error", "reduce error rate". **Bug de lógica real**, no un detalle de estilo.

### 0.6 Autonomía sin red de seguridad
`metric-optimizer`, `backtest-run` y `research-pipeline` se declaran "nunca preguntan / nunca se detienen" sin presupuesto de iteraciones, de coste ni de tiempo, y sin checkpoint reversible. Para tareas donde universo/fuente de datos/métrica importan, la autonomía total produce resultados *incorrectos pero convincentes*. **Sugerencia:** pedir 1-2 preguntas de scoping upfront o fallar duro si falta input, y añadir `max_iterations` / `max_cost` / checkpoint del diff por iteración.

### 0.7 Ausencia de límites de alcance / presupuesto de tokens
`project-analyzer` lee "broadly" sin excluir `node_modules`/build dirs ni límite de archivos; en un repo grande quema decenas de miles de tokens. `academic-source-search` puede lanzar una búsqueda de 14 bases con un prompt vago. **Sugerencia:** excludores por defecto, cap de archivos y 1 pregunta de scoping opcional.

### 0.8 Restos de español en docs en inglés
`backtest-run:22`, `backtest-validate:60,69` tienen frases sin traducir. Señal de edición truncada y de "limpieza" pendiente. Además, `content-humanizer` tiene su tabla de frases IA **solo en inglés** aunque el repo es bilingüe.

---

## 1. Agentes

### 1.1 `constructor`
**Qué es:** clon del `build` de opencode, full-access, integra 4 meta-skills (roadmaps, metric-optimizer, skill-creator, agent-self-improver).

**Fortalezas:** buena sección de comunicación orientada a economía de tokens; orquestación de skills bien descrita.

**Debilidades / mejoras:**
- **Sin ruta de error.** No dice qué hacer si un trabajo "colisiona" entre skills (p.ej. roadmap pide un loop que metric-optimizer debería delegar, o una sesión invoca metric-optimizer y roadmaps a la vez sobre el mismo `goal_state.json` → contención/sobreescritura).
- **`doom_loop: ask` sin guía** sobre qué responder cuando se dispara.
- **Falta "verify before declare success" con criterio:** dice "run tests/lint/typecheck" pero no define cómo decidir que la verificación es suficiente frente a trabajo no determinista.
- **Sugerencia:** añadir un bloque "Skill handoff & conflict resolution" (quién es dueño del estado, cómo encadenar roadmaps→metric-optimizer→skill-creator), y una regla de presupuesto/aborto que herede de 0.6.

### 1.2 `planner`
**Qué es:** clon read-only de `plan`.

**Debilidades / mejoras:**
- **Bien acotado.** El principal gap es de integración: produce un plan pero no formaliza cómo `constructor` lo consume (¿archivo en `.opencode/plans/`? ¿formato de pasos estándar?). Define el patrón manualmente dos veces.
- **Sugerencia:** acordar un formato de plan mínimo compartido (nº de paso, archivos clave, riesgos, pasos de verificación) que `constructor` sepa leer; y un enlace a `roadmaps` para tareas multi-paso grandes en vez de planes ad-hoc.

### 1.3 `vault`
**Qué es:** gestor de bóveda Obsidian con 10 workflows, bilingüe.

**Debilidades / mejoras:**
- **Índice solo-en-memoria por sesión** (Auto-Index "Store the index for the session"). Re-indexa cada sesión desde cero en bóvedas de cientos de notas → coste recurrente y resultados no persistentes. **Sugerencia:** cache el índice a disco (con regla de obsolescencia, como roadmaps) — es el único agente sin persistencia pese a ser el más "de estado".
- **"Bash: deny" pero los workflows invocan `grep`/`glob`** — consistente, pero los comandos de ejemplo (`grep -r ... --include="*.md"`) están copiados de Linux; en Windows/PowerShell no funcionan igual. Revisar portabilidad (estás en win32).
- **Fuzzy search depende de herramientas:** el agente propone buscar "grep -i" para fuzzy, pero el Levenshtein/typos/sinónimos descritos (líneas 148-153) no están implementados en ningún script — son instrucciones que el modelo debe improvisar. **Sugerencia:** un `scripts/vault_index.py` + `vault_search.py` reales (como hacen jobfinder/osint) en vez de grep ad-hoc.
- **Riesgo de escalado:** "grep -r" sobre toda la bóveda en cada búsqueda no escala con índice en memoria.
- **Descripción masiva** (25+ líneas de triggers) → podar (0.2).

### 1.4 `paper-researcher`
**Qué es:** escritor de papers académicos bilingüe, integra academic-source-search + citation-formatter.

**Debilidades / mejoras:**
- **No tiene paso de búsqueda obligatoria de aclaración** antes de formatear/consultar: si el usuario da un tema vago, lanza la cadena completa. Añadir un paso DEFINE reforzado (tema preciso, estilo, auditoría, idioma, extensión objetivo) con confirmación.
- **Contrato con las skills sin formalizar** (0.1): debe escribir `sources.yaml` que `citation-formatter` consume.
- **Doble fuente de verdad de formatos:** el agente re-imprime el esquema de frontmatter (`TITLE/NORM/FONT/...`) que también vive en `citation-formatter`. Referenciar, no duplicar.
- **"webfetch para verificar cada fuente"** es correcto, pero no hay límite de fuentes/tiempo → añadir cuota por claim (p.ej. 5-10 por sección).

### 1.5 `jobfinder` (agente) vs `skills/jobfinder` (skill) vs `ai-job-search` (tercero)
**El problema de duplicación más grave del repo:**
- El agente re-pastea el **mismo** cuestionario de 18 preguntas, la misma tabla 5D, umbrales y gates que la skill (agent:54-87 = skill:46-79). Dos artefactos idénticos que ya han empezado a divergir → drift garantizado.
- **Triplicación del conocimiento de scoring:** la tabla 5D + umbrales existen en 3 sitios (ai-job-search/ref-04, skill, agente).

**Errores verificados:**
- **Portales sobre-prometidos:** el agente lista 12 portales + 4 ATS (line 127-130), pero `search_jobs.py` implementa **solo 5 scrapers** (`indeed, linkedin, computrabajo, glassdoor, remoteok`) y **cero ATS** (no existe greenhouse/lever/ashby). El modelo invocará handlers inexistentes o devolverá vacío.
- **Deps inconsistentes:** skill omite `pdfplumber`/`python-docx` que `parse_cv.py` necesita.
- **`generate_report.py` requiere `projects.json`** que nada upstream produce → crash probable.

**Mejoras sugeridas:**
1. **Convertir el agente en un delegador delgado (~40 líneas):** "ejecuta la skill jobfinder; aquí está el handle del perfil", y borrar el workflow pegado.
2. **Hacer que la skill referencie** los archivos de ai-job-search (07-interview-prep ya se referencia) en vez de re-pastear la 5D.
3. **Corregir `search_jobs.py`** (implementar ATS o recortar la lista) y añadir dedup por título+empresa normalizado antes de puntuar.
4. **Perfil progresivo** en vez de 18 preguntas upfront: 3 core + resto opcional (contrasta con `/setup` → `/expand` de ai-job-search).
5. Adoptar el **PDF-verification loop** de ai-job-search tras `generate_cv_pdf.py`.

---

## 2. Skills del pipeline académico

### 2.1 `academic-source-search`
**Fortalezas:** tabla de tiers ética (Tier 5 nunca como soporte directo), manejo de errores realista (paywall→preprint), reglas anti-alucinación duras, estrategia snowball.

**Debilidades / mejoras:**
- **Contrato de salida contradictorio:** emite tabla Markdown pero el template YAML (metadata machine-readable) nunca se persiste; `citation-formatter` lo necesita. → **P1:** "escribe `sources.yaml` (template YAML) para cada fuente seleccionada; la tabla solo como resumen humano".
- **Google Scholar es Prioridad 1 pero no es scrapeable** (CAPTCHA). → **P1:** preferir APIs gratuitas (CrossRef REST, arXiv API, PubMed E-utilities) y tratar Scholar como verificación manual.
- **Sin paso de dedup por DOI** tras el snowball, y **sin cuota de fuentes por claim.**
- **Sin paso de aclaración obligatorio** → añadir preámbulo: (a) pregunta exacta, (b) sección objetivo, (c) rango de años, (d) idioma, (e) tier mínimo.

### 2.2 `citation-formatter`
**El hallazgo más grave del repo verificado en código:**
`generate_outputs.py::main()` **solo** parsea frontmatter y o imprime la HTML de la portada (`--html`) o vuelca el frontmatter como JSON. **Nunca llama a `generate_toc_html()` ni a `generate_docx_titlepage_xml()`**, nunca lee la clave `TOC`, ignora `--norm`. La feature estrella (PDF/DOCX completo + TOC automático) **no existe**: está documentada pero es código muerto.

**Debilidades / mejoras:**
- **P1 — o se cablea el generador completo, o se recortan las afirmaciones** de la descripción. Documentar PDF/DOCX que el script no produce es engañoso (el agente puede alucinar el output).
- **P1 — Reescribir los ejemplos de referencias en notación `_text_`** (`_Journal Name_`, `_Título_`) — la línea 374 prohíbe `*text*` y manda `_text_`, pero cada ejemplo renderiza el nombre de la revista plano. Inconsistente consigo mismo.
- **P1 — Paso de flujo inicial:** "confirma estilo (APA/IEEE/Vancouver) y destino (markdown vs PDF/DOCX) *antes* de formatear" (hoy solo está en "Error handling").
- **P2 —** cobrar la recolección de campos de portada **solo si `NORM: "APA 7th"`** (IEEE/Vancouver no necesitan portada), y validar campos faltantes con error duro en vez de sustituir `"Untitled"` (contradice "ask, never fabricate").
- **P2 —** usar `yaml.safe_load` en vez del parser naive que rompe con listas/valores con `:` (pyyaml ya está en deps).

### 2.3 `math-notation`
**Fortalezas:** el mejor escrito de los cuatro; tablas correcto/incorrecto, blacklist Unicode, regla de escape de guiones bajos, snippet de verificación que coincide con el parser real.

**Debilidades / mejoras:**
- **Dependencia de ruta no resuelta:** la Scripts table lo lista como propio pero el script vive en `citation-formatter/scripts/`; "in the path or at project root" solo funciona por accidente. → **P1:** fijar el comando exacto + corregir la tabla en las 3 secciones.
- **Es pasivo:** nunca instruye escanear un documento buscando violaciones (`*text*`, `²`, `r₀`) y corregirlas. → **P2:** añadir paso de lint (`grep -nE '\*[^*]+\*|[²³¹]' doc.md`) y reemplazar según las tablas.
- **Contrato a aguas abajo:** `content-humanizer` podría "limpiar" `_r_{0}` → `r₀` rompiendo el parser. → **P2:** cláusula "no tocar `_…_`, `^{…}`, `_{…}`" para downstream.
- Documentar la ambigüedad de `_..._` con espacios y el mismatch `gcd`/`mcd` entre su self-check y el del script.

### 2.4 `content-humanizer`
**Fortalezas:** el mejor diseño operativo (objetivos medibles SD>12, ≤20% pasiva, loop acotado a 3 iteraciones, script local + verificación), tests reales, restricciones éticas fuertes.

**Debilidades / mejoras:**
- **P1 — Doc/script no coinciden:** la doc muestra `Verdict: PASS` y bandas EN; el script imprime español (`PASA`/`DETECTADO`) y solo expone `--threshold` (0.5), que la doc nunca documenta.
- **P1 — El fallback web es inejecutable:** "enviar a zerogpt.com / gptzero.me vía `webfetch`" no funciona (son POST interactivos anti-bot). Sustituir por "pedir al usuario que corra el checker online y pegue el resultado" o eliminar la rama.
- **P1 — Faltan protección de tokens del pipeline:** debe preservar `_text_`, `^{...}`, `_{...}` (notación generate_outputs.py) y no convertir `_`→`*`.
- **P2 — Falta tabla de frases IA en español** (el repo es bilingüe).
- **P2 — Calibrar expectativas:** el `detect_ai.py` usa un detector roberta de 2019 con alta tasa de falsos positivos; tratar su PASS como "listo para enviar" contra Turnitin/GPTZero no está fundamentado.
- **P2 — Burstiness mal contado:** parte solo por `.` → infla SD con decimales/abreviaturas ("i.e.", "$1.5").

---

## 3. Skills de meta/desarrollo

### 3.1 `metric-optimizer`
**Fortalezas:** loop tight, escalada ordenada por coste, estado con historial, "When NOT to use".

**Debilidades / mejoras:**
- **P0 — Bug de dirección:** solo maximiza; falla para "minimize/reduce". Añadir `mode: maximize|minimize|exact` al esquema y hacer EVALUATE/`best_metric` dirección-conscientes.
- **P0 — Unificar umbrales** (3 vs 5) en un único "3 fallos/planos consecutivos → switch paradigm".
- **P1 — Presupuesto y terminación:** `max_iterations`/`max_cost`/`deadline`; en agotamiento `STOP` + reporte. Hoy "nunca se detiene" es un footgun con APIs de pago.
- **P1 — Checkpoints reales para "revert":** `history` solo guarda `{iteration, metric, action}`; no hay hash de commit ni snapshot → un revert no tiene a qué volver. Persistir diff/commit por iteración.
- **P2 — Una pregunta upfront** (objetivo + dirección + presupuesto) en vez de "nunca pregunta", y podar la descripción.

### 3.2 `roadmaps`
**Fortalezas:** modelo de 5 tipos de paso, disciplina de cache (source of truth = roadmap.md), tabla de fallo, templates.

**Debilidades / mejoras:**
- **P0 — Evals schema roto** (`expectations` → `assertions`).
- **P1 — El validador no valida lo que promete:** `validate_roadmap.py` no comprueba `Next`, `Sub-steps` paralelos ni `Criteria` de milestones, y rechazaría la sección `## Completed` que la skill manda mover. Alinear.
- **P1 — Gatear el "¿creas un roadmap?"** con la excepción de tarea simple (hoy pregunta incondicionalmente, contrario a su propio "When NOT to use").
- **P2 — Dejar de nombrar agentes concretos** (`explore`/`general`/`build`) en "agent assignment" — si el proyecto consumidor no los tiene configurados, apunta a subagentes inexistentes.

### 3.3 `agent-self-improver`
**Fortalezas:** la mejor postura de seguridad (human-in-the-loop, backups, reversibilidad, test-first), sugerencias concretas con before/after y confianza.

**Debilidades / mejoras:**
- **P0 — Crisis de identidad:** ~70% del cuerpo es un cheatsheet de python-docx (`JUSTIFY`, `w:anchor`, `qn()`), inutilizable como "self-improver" genérico fuera de documentos. Mover eso a `references/docx-generation.md` y dejar el flujo genérico.
- **P0 — No tiene estado persistente** → "detect patterns across sessions" **no funciona de verdad** (es single-session). Definir `feedback/` con `sessions.jsonl` append-only + `improvement-log.json` derivado.
- **P0 — Cuatro vocabularios de categoría superpuestos** (`error_type` enum, `format_compliance`, `"format-compliance"`, `category: format|bug|xml...`) que `analyze_feedback.py` agrupa y por tanto fragmenta. Unificar en un enum.
- **P1 — Umbral proactivo agresivo:** "after 3+ tool calls" interrumpe casi cada sesión → entrena al usuario a ignorarlo. Elevar a "retry_count ≥ 2 o fallo fijo".
- **P1 — Cerrar el loop:** tras N cambios aprobados, re-ejecutar el análisis y reportar el delta de frecuencia de patrones.

### 3.4 `project-analyzer`
**Fortalezas:** mandato read-only inequívoco, taxonomía de severidad clara, directrices de cita/impacto buenas ("user sees blank page", no "error not handled").

**Debilidades / mejoras:**
- **P1 — Sin control de alcance:** añadir excludores `.git/node_modules/.venv/build`, cap de archivos y 1 pregunta opcional "¿auditar todo o enfocar X?" (la única pregunta que debería hacer y no hace).
- **P1 — Sin baseline/delta:** escribir `reports/audit-<iso>.json` y en re-ejecución comparar → "recién corregido / recién introducido".
- **P2 — Priorización ad-hoc ("top 3-5"):** puntuar severidad × probabilidad × esfuerzo (préstamo de backtest-validate).
- **P2 — Lista de grep de seguridad genera falsos positivos** (`password=`); dar reglas de triage por lotes.
- **P3 — `init_review.md` duplica el cuerpo del SKILL** → colapsarlo a un puntero delgado.

---

## 4. Skills de trading / notificación

### 4.1 `telegram-notify`
**Fortalezas:** utilidad bien separada (solo envía), filosofía no-bloqueante con retry, superficie de método completa, honestidad de seguridad.

**Debilidades / mejoras:**
- **P1 — PELIGRO: "auto-crear `.env` con placeholders"** (líneas 128/170) → las skills aguas abajo escribirán credenciales falsas que fallan cada envío. Reemplazar por: detectar credenciales faltantes → mensaje claro de setup + return de fallo. **Nunca** escribir tokens falsos.
- **P1 — Truncado sin definir:** regla "max 4000 chars, use send_document" no dice qué truncar. Definir "notify() trunca a 4000 y añade '…'".
- **P1 — Ruta de import inconsistente** para consumidores (`from telegram_notify.scripts...` requiere que el repo sea importable; documentar `pip install -e .` o nota de `sys.path`).
- **P2 — Podar duplicación** de triggers/descripción.

### 4.2 `backtest-run`
**Fortalezas:** fases claras, defaults concretos (90 días, split 60/20/20, slippage min(0.5%,1 tick), 80% fill), guardas anti-overfitting.

**Debilidades / mejoras:**
- **P1 — Cloud path roto (verificado):** `cloud.py:49` ejecuta `python3 -m backtest_runner` en remoto, pero **`backtest_runner` no está definido en ningún sitio del repo** → fallará siempre salvo instalación manual. Documentar el módulo o hacer cloud.py autocontenido.
- **P1 — Fuente de datos no especificada:** "min 90 days" sin decir de dónde sacar OHLCV = bloqueo de autonomía. Añadir paso DATA explícito con proveedor + fallback "si no hay, preguntar".
- **P1 — Stubs de 1 línea** para los pasos (SPEC/METRICS) sin formato de spec de ejemplo ni lenguaje de estrategia → under-specified para autonomía real.
- **P2 — Pedir 1 confirmación upfront** (universo, rango de fechas, fuente) en vez de "nunca pregunta".
- **P2 — Alinear umbrales de overfitting** con backtest-validate (win rate >80 vs >90; parámetros >3 vs ≥7).
- **P2 — Emitir `reports/` JSON** de spec+métricas para cerrar el handoff con backtest-validate y telegram.
- Menor: quitar el español sobrante (línea 22).

### 4.3 `backtest-validate`
**Fortalezas:** script con input validation y red flags verificados con tests (única de las 4 con tests), "trust red flags over score", filosofía diferenciada ("break the least, not profit the most").

**Debilidades / mejoras:**
- **P1 — Dependencia de transcripción manual:** validación depende de 8 flags escritos a mano. Añadir modo `--input results.json` que lea el output de backtest-run.
- **P1 — Reclamaciones de detección de sesgo deshonestas:** el script **no** puede detectar look-ahead/survivorship bias (solo infiere de un heurístico `win_rate > 90`). O añadir checks reales (relación IS/OOS, pase walk-forward) o rebajar el wording.
- **P2 — "Trust red flags over score"** debería ser un override duro (forzar Abandon) no solo una directriz.
- P2 — Restos de español y path ambiguo `scripts/evaluate_backtest.py` (vive en `skills/backtest-validate/scripts/`).

### 4.4 `research-pipeline`
**Fortalezas:** la estructura más limpia (7 pasos justificados), reproducibilidad (LOG), guardas de scoping (no saltar SCOPE/DECIDE), nota de disambiguación vs academic-source-search.

**Debilidades / mejoras:**
- **P1 — LITERATURE under-specified:** lista 9 fuentes pero no *cómo* buscar (API vs webfetch, nº de fuentes, verificación). **Sugerencia fuerte:** delegar a `academic-source-search` cuando esté presente (hoy solo lo referencia *negativamente* para decir "no uses esto para búsqueda de solo-fuentes").
- **P1 — Sin cap de iteraciones en DECIDE** ("Ambiguous > refine hypothesis" puede loopear infinito). Añadir "máx 3 refinamientos, luego log + stop" (tomar el modelo de metric-optimizer).
- **P1 — "Nunca pregunta" es arriesgado:** pedir 1-2 preguntas de scoping (métrica de interés, disponibilidad de datos/credenciales) antes de ser autónomo, o fallar duro si falta el SCOPE.
- **P2 — Manejo de API keys / rate limits** para "market data / prediction markets" (deuda con telegram-notify).
- **P2 — Recortar la descripción** y eliminar frases que pueden robar triggers a academic-source-search ("literature review").

---

## 5. Skills de dominios especiales (según lo pedido, con foco)

### 5.1 `osint`
**Fortalezas:** scripts reales (gen_report 240 líneas, phone_parser 13 países, generate_plan, scrape_directories con aislamiento de error por scraper), tests, insistencia en que websearch es el método primario y curl el fallback, guardas legales/éticas.

**Debilidades / mejoras:**
- **P1 — Contradicción de ejecución:** "NO ejecutar nada sin aprobación" (línea 33) pero los pasos 2, 5 y 7 corren scripts (`phone_parser`, `scrape_directories`, `gen_commands`) antes de la verja del paso 8. Mover la verja o acotar la restricción a comandos *investigativos*.
- **P1 — los comandos generados no corren:** `generate_plan.py:19` emite `search "..."` como `command`, y `gen_commands.py` lo mete en `commands.sh` y dice "To execute: bash commands.sh". `search "..."` **no es un comando shell** — el script falla en la primera línea. Mezcla herramientas reales (`whois`, `dig`, `holehe`) con pseudo-comandos (`search`, `namechk`) sin marcarlos.
- **P1 — `run_investigation.py` es código muerto** y además ejecutaría `subprocess.run(shlex.split(cmd))` de esos comandos no ejecutables. O cablearlo tras aprobación o eliminarlo.
- **P2 — APIs/sitios obsoletos o frágiles:** scrape regex de TrueCaller/Whitepages (JS, anti-bot), `country_code = "57"` hardcodeado, deps no instalables (`whatsmyname`/`whatweb`), endpoint DeBank/OpenSea v2 no públicos. Marcar cada comando como "verificado" vs "posiblemente obsoleto, prefiere websearch".
- **P2 — Contradicción nmap:** "nmap = probe pasivo" en deps vs `nmap -sV -sC -p-` (escaneo activo) en domain_osint que requeriría autorización del host. Acotarlo como activo.
- **P2 — Huecos metodológicos:** sin regla de corroboración (hallazgos de fuente única deben cross-chequearse antes del reporte), sin guía de nivel de confianza, sin manejo "sin datos", sin limpieza de archivos intermedios (`findings.json`, `commands.sh`), y `tools_check.py` nunca se invoca (falta un "Step 0: verificar herramientas").
- **P2 — Ética/contexto:** sin check de consentimiento/rol (¿eres tú, un cliente o un tercero?), ni de proporcionalidad, ni de retención/eliminación. Para due diligence, añadir verja de "propósito legítimo + proporcionalidad" antes del plan.
- Menor: typo "Red Freuds" → "Red Flags".

### 5.2 `jobfinder` (skill) — ver 1.5. Lo central: eliminar duplicación agente/skill/ai-job-search, corregir `search_jobs.py` (5 scrapers reales, 0 ATS), dedup, deps, contrato de `projects.json`, perfil progresivo y PDF-verification.

---

## 6. Instalador, CI y web

### 6.1 `setup.py`
**Fortalezas:** TUI con navegación por flechas y propagación de dependencias, detección de plataforma/modo, copia + limpieza determinista.

**Hallazgos / mejoras:**
- **Bug sutil en el menú:** `_build_display_order()` ordena por label, e `idx = items.index(it)` en `_render_menu` recalcula el índice por igualdad de dict — con dos items de la misma label o duplicados rompería, pero hoy es estable. No crítico.
- **`--all` coincide con dependencias**, bien.
- **`agents.json` (opencode) no es el mecanismo real** de registro de agentes de opencode (opencode usa `.opencode/agent/*.md`), pero eso depende del objetivo del repo (también apunta a Claude/Cursor/Windsurf). **Sugerencia:** documentar explícitamente que opencode registra agentes leyendo el directorio `agent/` y, si aplica, instalar también ahí.
- **Falta deps de scripts con imports cross-skill:** `math-notation` depende del script de `citation-formatter`; el installer no copia dependencias de scripts sueltos (solo `bundles` del jobfinder). El ITEMS de `math-notation` debería `bundle: skills/citation-formatter/scripts` o documentarse.

### 6.2 `ci.yml`
**Fortalezas:** matrix 3.11/3.12, bandit, validación de estructura, pytest por skill.

**Mejoras sugeridas:**
- **Verificación de coherencia doc-vs-código** (el hallazgo 2.2 no se detectaría hoy): un test que confirme que los comandos documentados en SKILL.md existen (`scripts/evaluate_backtest.py`, `cloud.py`/`backtest_runner`, portal claims de `search_jobs.py`).
- `bandit -r skills/` escanea scripts de terceros (impeccable/skill-creator) y es `|| true` (no hace fallar el build) — considerar scope solo a primer parte y hacerlo bloqueante en severidad alta.
- Añadir un test que verifique que todos los nombres de workflow/scripts citados en agentes y skills existen (caza los sobre-promises como los 12 portales de jobfinder).

### 6.3 `web/` (Astro)
Frontend de documentación Astro 7.x. Hay un `dist/` y `node_modules/` **versionados** — `.gitignore` debería excluirlos (o confirmar que el commit de `dist` es intencional, que suele ser anti-patrón). El `CLAUDE.md` local es un buen touch. `web/src` está vacío salvo el layout/componentes que se hayan descrito; no lo profundizo más porque no es el foco.

---

## 7. Resumen de mejoras de más alto impacto (prioridad)

| Área | Acción | Esfuerzo | Impacto |
|---|---|---|---|
| Across | Definir artefactos compartidos (`sources.yaml`, `results.json`, `NotificationBroker`) | Alto | Crítico — arregla la cadena |
| citation-formatter | Cablear `generate_outputs.py` completo o recortar claims; ejemplos en `_text_` | Medio | Elimina la mayor doc-vs-código |
| jobfinder | Des-duplicar agente/skill; corregir `search_jobs.py` (5 scrapers, 0 ATS) | Alto | Correctitud |
| metric-optimizer | Fix dirección max/min; 1 presupuesto; unificar umbrales | Bajo | Seguridad + correctitud |
| agent-self-improver | State store + vocabulario único + mover docx a references | Medio | Lo hace funcionar realmente |
| telegram-notify | Quitar auto-create `.env` con placeholders | Bajo | Seguridad |
| roadmaps | Fix evals schema (`assertions`); validador real | Bajo | QA medible |
| osint | Arreglar `gen_commands.py`; verja de aprobación; corroboración | Medio | Correctitud + ética |
| content-humanizer | Doc/script coherentes; protección de tokens; tabla ES | Medio | Confianza del gate final |
| acad-source-search | Persistir `sources.yaml`; paso de aclaración; APIs CrossRef/arXiv | Bajo | Define la cadena |
| Todos | Podar descriptions; quitar español sobrante; presupuestos/abortos | Bajo | Fidelidad + seguridad |
| CI | Test de coherencia doc-vs-código | Medio | Atrapa los over-promises |

---

## 8. Preguntas que el usuario debería decidir

1. **Modalidad del repo:** ¿`constructor`/`planner` deben seguir siendo "clones de opencode" o evolucionar hacia agentes propios (con handoffs formales a `roadmaps`/`metric-optimizer`)? Esto define cuánta profundidad de integración vale la pena.
2. **¿Quiénes son realmente los usuarios?** El repo es bilingüe (EN/ES) y multi-plataforma (opencode/claude/cursor/windsurf). ¿Priorizar opencode (tu setup real) o mantener la portabilidad multi-IA? Afecta el installer y los comandos.
3. **Skills de terceros** (skill-creator, impeccable, ai-job-search): el README dice "no modifiques". ¿Mantener sync upstream, o estás abierto a forks propios con las mejoras de este análisis (p.ej. ai-job-search ya está duplicado con el jobfinder nativo)?
4. **¿Hay intención de monetizar/publicar?** El `web/` Astro sugiere documentación pública. Si es así, la auditoría de coherencia doc-vs-código (6.2) sube de prioridad.
5. **Autonomía:** ¿hasta qué punto quieres loops autónomos sin preguntas (metric-optimizer, research-pipeline) vs. verja humana? Este análisis recomienda 1-2 preguntas de scoping + presupuesto. Tu umbral de confort define el diseño.
6. **¿Quieres que aplique estos cambios?** El análisis es read-only. Puedo empezar por los P0 de mayor impacto (2.2 citation-formatter, 1.5 jobfinder, 3.1 metric-optimizer, 3.3 agent-self-improver, 4.1 telegram-notify) implementándolos con el flujo de test/review de `skill-creator`.
