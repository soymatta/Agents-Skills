# Citaflex — mapa y trampas de QA

Proyecto: **Citaflex**. Léelo SOLO cuando el target sea Citaflex antes de correr QA.

## Rutas y entorno

- **QA E2E**: correr desde `D:\Files\Citaflex\qa` con
  `.\node_modules\.bin\playwright.cmd` (NO `npx playwright`). Lee `qa/.env.local`
  (target: `https://citaflex.vercel.app/` o `http://localhost:5173`;
  `QA_REAL_BACKEND=1`). `qa/` y `qa-results/` están gitignored. Proyectos:
  `setup` (auth), `smoke`, `full`.
- Al apuntar a localhost, `qa/.env.local` NO debe quedar apuntando a producción
  durante una válida CI local: stalkéalo con backup (`qa/.env.local.prod.bak`)
  y restóralo al terminar.
- **Chromium cacheado**: el config autodetecta
  `C:\Users\yasse\AppData\Local\ms-playwright\chromium-<rev>\chrome-win64\chrome.exe`
  o `QA_CHROMIUM_PATH`. **No corras `npx playwright install`** (descarga otra rev
  y rompe).
- **Lighthouse**: `chrome.exe --version` cuelga; lanza Chromium manual con
  `--headless=new --remote-debugging-port=9333 --user-data-dir=<temp>` y usa
  `lighthouse <url> --port=9333 --output=json/--output-path=...`. KPI actual:
  Perf 82, A11y 100, BP 100, SEO 91.
- **Gates**: `npx tsc --noEmit` + `npm run lint` (0 errores; 8 warnings
  react-refresh de shadcn/cva son preexistentes y aceptados) + `npm run build`
  (aviso de chunk >500 kB es informativo; no corregir sin pedir refactor lazy).

## Trampas de la app (si un test falla, sospecha de estas)

- **PostgREST limita a 1000 filas sin `.range()`**: `appointments.tsx` pagina en
  bucles; nunca vuelvas a una consulta única sin tope.
- `time` de Postgres llega como `"HH:MM:SS"` — se normaliza con `slice(0,5)`.
- Login demo directo a `public.users` (`localStorage citaflex.session`); sin
  Supabase Auth. Re-ejecutar `supabase/database.sql` tras deploy.
- Crear notificaciones SIEMPRE por RPC `create_notification`/`notify_roles`,
  nunca insert directo. Borrado individual `delete().eq("id")`; "todas"
  `.eq("user_id")`.
- **Notificaciones citas vinculadas**: desde sept 2026 el click en una
  notificación navega a la cita (`/app/appointments?cita=<id>`) SOLO si la BD
  tiene `notifications.appointment_id` (re-ejecutar database.sql) y los RPC de
  6 args. Si la DB no está migrada, `createNotification`/`notifyRoles` con
  `appointmentId` fallan en silencio (console.warn). Los specs que dependen del
  vínculo se gatean con `CITAFLEX_DB_LINKED=1` (ver booking.spec.ts la división
  y admin-tools.spec.ts el bloque "DB migrada").
- `count()` en Playwright NO auto-espera: ante un grid asíncrono primero
  `await expect(locator.first()).toBeVisible()` y luego cuenta.
- Los validators de búsqueda de ruta hacen `search` REQUERIDO en navegaciones:
  al navegar con `navigate`/`Link` a rutas con validator, pasa siempre
  `search: { … }`.
- Guard anti-doble-envío (doble-clic duplica): `disabled={saving}` por estado NO
  basta — `dblclick` dispara los 2 clics antes de que React re-renderice. El
  guard debe ser síncrono con `useRef` (`if (savingRef.current) return;
  savingRef.current = true; … finally { savingRef.current = false }`). Aplicado
  en `services.tsx` y `appointments.tsx`.