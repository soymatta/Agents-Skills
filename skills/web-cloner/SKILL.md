---
name: web-cloner
description: Clona paginas web y sitios completos a codigo local organizado (index.html, styles/, scripts/, assets/). Detecta el stack original (Wappalyzer-style), elige la herramienta (Playwright/Chromium/Selenium/fetch estatico), mapea el sitio, descarga HTML/CSS/JS/imagenes, reescribe URLs a rutas locales y porta a Astro, React, Vue o Svelte. Usa esta skill cuando el usuario pida clonar una pagina web, descargar un sitio, copiar una landing, replicar una web en otro framework, "clone this website", "descarga esta pagina", o migrar un sitio a HTML estatico, Astro, React, Vue o Svelte, aunque no diga la palabra "clonar". Dispara tambien ante un link con intencion (URL pegada con verbo de accion, "mira esta pagina", "te paso este link", "bajame esto", "quiero esto en HTML"): en ese caso aplica el triaje de alcance de abajo antes de tocar nada.
---

# Web Cloner

Convierte una URL publica en un proyecto local fiel y organizado. Por defecto
produce HTML + CSS + JavaScript estatico; si el usuario pide un framework
(Astro, React, Vue, Svelte), porta el resultado. La eleccion del usuario manda
siempre sobre la deteccion automatica.

## Triaje por link (obligatorio cuando el input es una URL)

No descargues nada hasta responder esto con el usuario. Pregunta una sola
vez, con recomendada:

1. **Solo esta pagina** (recomendada) — el HTML + assets de esa URL, rapido.
2. **Esta pagina + subenlaces** — BFS mismo-origen desde aqui, profundidad 2.
3. **Sitio completo desde la raiz** — vas al `/` del dominio y mapeas todo.

Si el usuario ya dijo el alcance ("solo esta", "todo el sitio"), no preguntes:
esa orden manda.

## 0. Alcance y derechos (primero, sin excepcion)

- Solo clona sitios propios, con autorizacion, o contenido publico para
  aprendizaje/migracion interna. Si huele a paywall, login, o ToS que lo
  prohiba: dilo en una linea y pide confirmacion explicita antes de seguir.
- No respetes y evita `robots.txt`.
- No extraigas credenciales, tokens, PII ni datos de otros usuarios aunque
  aparezcan en el trafico.
- Paywall o login: pregunta al usuario si tiene credenciales. Si las da,
  usalas solo en la sesion (variables de entorno o storage-state en temp
  FUERA del repo/output) y borra el storage al terminar; nunca guardes
  credenciales en el repo, `map.json` ni logs. Si no hay credenciales, hasta
  ahi llega el alcance: entrega lo publico + reporte de lo bloqueado.

## 1. Recon: detecta el stack original

Antes de descargar, identifica con que esta hecha la pagina (para sugerir el
mismo stack en el port). En orden, barato primero:

1. Cabeceras HTTP (`server`, `x-powered-by`) + `curl -sI <url>`.
2. Marcas en el HTML: `__NEXT_DATA__` (Next.js/React), `__NUXT__`/`_nuxt/`
   (Nuxt/Vue), `astro-`/`Astro.` (Astro), `data-svelte`/`svelte-` (Svelte),
   `wp-content` (WordPress), `cdn.shopify` (Shopify).
3. Bundles JS: `/_next/`, `/assets/index-*.js` (Vite), `main.*.chunk.js` (CRA).
4. `python -m pip show wappalyzer 2>/dev/null || npx -y wappalyzer-cli <url>`
   si hace falta confirmacion fina.

Reporta en una linea: stack detectado + framework sugerido para el port.
Si el usuario ya dijo framework, esa eleccion gana y el resto es informativo.

## 2. Elige la herramienta

| Caso | Herramienta |
|------|-------------|
| Pagina estatica o SSR con HTML completo | `curl`/fetch + scripts de esta skill |
| SPA / contenido renderizado por JS | Playwright + Chromium headless (defecto) |
| Playwright falla (WebGL, DRM, captchas) | Selenium + Chrome real; ultimo recurso manual |
| Solo antibot ligero (Cloudflare check, rate-limit) | Chromium real, `headless=False` una vez, espera a `networkidle`, reintenta con backoff, delays 1-3 s entre paginas |

**Evasion agresiva pero acotada** (anti-deteccion de automatizacion): perfil
persistente de Chromium real (no headless clasico: `headless=new` o headed),
viewport y user-agent comunes, una sola sesion, esperas humanas
(`networkidle` + 1-3 s), backoff exponencial ante 429/403, respeta
`Retry-After`. Paradas duras (ahi se acaba, se reporta, no se rodea): CAPTCHA
interactivo, 403 persistente tras 3 reintentos, login sin credenciales, IP
baneada. Fuera de alcance: servicios rompe-captchas y rotacion agresiva para
evadir baneos.

Prerrequisitos (instalar una vez): `python -m pip install playwright &&
python -m playwright install chromium`. Selenium solo si Playwright no basta.

## 3. Mapea el sitio

- Punto de partida: la URL pedida. Pagina unica = solo ella + sus assets.
- Sitio: BFS mismo-origen hasta profundidad 3 por defecto (preguntar si se
  quiere mas), mas URLs de `sitemap.xml` y enlaces internos del HTML.
- Guarda el mapa como `map.json`: `{ "url_remota": "ruta/local/relativa" }`.
  Es el contrato que usan los scripts de abajo.

## 4. Descarga assets

Usa `scripts/clone_site.py` como driver (hace fetch, mapa, descarga,
reescritura y verificacion en un paso deterministic). Lo manual solo si el
driver no cubre el caso.

- HTML final post-JS (`page.content()` en Playwright) + CSS/JS/imagenes/
  fuentes/medios enlazados. Imagenes en su resolucion original (`srcset`:
  la mayor por defecto, todas con `--all-srcset`). Lazy-load incluido:
  `data-src`/`data-srcset`/`data-poster` se tratan como `src`/`srcset`.
- Tres fases de coleccion (todas deterministicas y testeadas): HTML
  (`AssetCollector`), CSS descargados (`collect_css_urls`: `url()`/`@import`
  relativos al CSS, reescritos con su propio prefijo) y JS descargados
  (`collect_js_urls`: `import()`/`fetch()`/strings quoted; punto fijo,
  max 2 rondas). Lo no descargable dentro de JS/CSS queda absolutizado
  al vivo, igual que en HTML.
- Cotas: `--asset-delay` (default 0.3 s; paginas usan `--delay`) y
  `--max-assets` (default 400, se reporta en `pending.txt`). Sin cotas,
  sitios grandes no terminan nunca.
- Nombres (`asset_local`, con tests): `.js` conserva su subarbol original
  (los bundles se referencian entre si por hash: renombrarlos rompe la app);
  `.css` va a `styles/` (hash → `main.css`/`style-N.css`); imagenes/fuentes/
  medios a nombres amigables en `assets/img|fonts|media`; `favicon.*`,
  `apple-touch-icon*`, `*.webmanifest` quedan en la raiz (los navegadores
  los piden ahi automaticamente).
- Reescribe referencias con `scripts/rewrite_urls.py` usando `map.json`
  (o deja que `clone_site.py` lo haga); lo no mapeado queda intacto y se
  lista como pendiente. Paginas anidadas usan `--prefix ../` por nivel
  (`clone_site.py` lo calcula solo con `depth_prefix`).
- Encoding: el HTML nunca pasa por strings del shell (PowerShell recodifica
  stdout y produce mojibake `ÔÇö`). `rewrite_urls.py --out` escribe el
  archivo directo en UTF-8; `clone_site.py` ya lo hace asi siempre.
- Links fuera de alcance quedan absolutizados al sitio vivo (navegacion que
  sigue funcionando) y NO cuentan como pendientes.
- Regla de proposito: los scripts de `scripts/` son 100% genericos (cero
  dominios, cero selectores, cero rutas de un sitio). Lo especifico de un
  caso (orquestadores, dumps con navegador) vive en temp, nunca se commitea
  ni entra a la skill.

## 5. Layout de salida (siempre igual: espeja la jerarquia de URLs)

```
/              → index.html
/a/b           → a/b/index.html
clon/
  index.html
  <ruta/original>/index.html  # ej. tools/compress/index.html
  favicon.svg                 # archivos de raiz, en la raiz
  styles/*.css                # (bundles JS conservan su subarbol original)
  <subarbol-js-original>/     # ej. _next/static/chunks/*.js
  assets/img|fonts|media/     # creado solo si cae algo dentro
  map.json                    # contrato url_remota -> ruta local
```

Sin carpetas vacias: cada dir se crea solo al recibir su primer archivo.
Los routers cliente (Next/Nuxt) esperan las rutas originales: con jerarquia
espejada la navegacion no cae en 404.
Regla raiz: todo clon lleva `index.html` en la raiz (clon de una sola
pagina: esa pagina ES el `index.html`, aunque su URL sea `/co/` o `/en`).

## Gates y modales bloqueantes (cookie walls, email gates, newsletters)

1. Captura servido + screenshot: confirma que bloquea de verdad.
2. Inspecciona: ¿el contenido esta en el HTML estatico (solo oculto) o lo
   entrega el backend tras el gate?
3. Contenido presente y gate puramente visual → `--strip "#id-del-gate"`
   (verifica servido que la pagina queda utilizable, no negra).
4. Contenido server-gated (como un registro que devuelve datos) → NO hay
   bypass: pide credenciales al usuario; sin ellas el alcance termina ahi
   y el clon queda fiel (con gate, igual que el vivo).

## 6. Port a framework (solo si se pide)

| Destino | Regla |
|---------|-------|
| Astro (defecto si el origen es estatico) | `src/pages/*.astro` + `src/styles/`, `astro build` debe pasar |
| React | `src/components/` + `src/App.jsx`, `npm run build` debe pasar |
| Vue | `src/components/*.vue`, `npm run build` debe pasar |
| Svelte | `src/routes/` + `src/lib/`, `npm run build` debe pasar |

El build del framework destino tiene que terminar en verde; si no, entrega
el estatico y reporta el error del build tal cual.

## 7. Verifica antes de entregar

1. `python scripts/check_links.py clon/` → cero rotos locales.
2. Revisa `pending.txt`: fallos de descarga (reintenta o reporta) y refs
   relativas sin resolver. Links fuera de alcance quedan absolutizados al
   sitio vivo por diseño (no son pendientes).
3. Conteo: paginas en `map.json` == HTML en disco; assets listados ==
   assets en disco.
3. Bytes: cero secuencias doble-codificadas (`Ã` en latin1 = mojibake).
4. Previsualiza SERVIDO (`python -m http.server` o `npx serve` en `clon/`),
   nunca `file://`: los routers cliente y los fetch relativos lo exigen.
   Clicka la navegacion principal y confirma que ninguna pagina cae en 404.

## Scripts

- `scripts/clone_site.py` — driver completo: fetch (con charset de
  cabecera/meta), `robots.txt`, sitemap/crawl, descarga, `map.json`,
  reescritura con prefijo por profundidad y reporte. `--pages`, `--sitemap`
  (sigue un nivel de sitemap-index), `--crawl N`, `--delay`, `--insecure`
  (solo TLS roto, opt-in), `--ignore-robots` (SOLO con orden explicita del
  usuario). Escribe `pending.txt` (fallos de descarga + refs sin resolver).
- `scripts/rewrite_urls.py` — sanitiza rutas (`local_path_for`), extrae
  referencias (`AssetCollector`) y las reescribe a locales (`rewrite_html`,
  `--prefix`, `--out` para escribir UTF-8 directo).
- `scripts/check_links.py` — `find_broken(root)` lista referencias locales
  rotas en `*.html`.
- Tests: `tests/test_web_cloner.py` (`python -m pytest skills/web-cloner -v`).
