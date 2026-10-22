# opencode-auto-session

Plugin de **OpenCode 2** (`@opencode/cli@2.0.31`). Guarda el historial cuando el
proveedor corta por limite de uso, avisa con un script **del sistema operativo**
(`limit-notify.ps1` en Windows, `limit-notify.sh` en Linux/macOS) que imprime
`LIMITE GRATIS ALCANZADO`, y da contexto de las sesiones anteriores al abrir una
sesion nueva.

## Formato del plugin

OpenCode 2 exige un default export con `id` y `setup` (o `effect`):

```js
export default { id: "opencode-auto-session", setup: async (ctx) => { /* ... */ } }
```

El `setup` recibe el `Context` de la v2 (`ctx.session`, `ctx.event`,
`ctx.command`, `ctx.location`, `ctx.options`) y devuelve una funcion de limpieza.
El SDK v1 (`Plugin = (input) => Hooks`) ya no carga: el validador del binario lo
rechaza con `Plugin must export a default definition with an id and an effect or
setup function.`

El plugin no importa `@opencode/*` en runtime (solo `import type`), asi que la
copia instalada en `~/.config/opencode/plugins/` funciona sin `node_modules`.

## Automatico

1. **Limite alcanzado** (`session.execution.failed`, `session.retry.scheduled` o
   `session.compaction.failed` con un error de cuota, `429` o `402`): escribe un
   dump **por sesion** (`.opencode_session_dump-<sesion>.md`, con id unico; los
   antiguos se podan a `dumpKeep`, por defecto 20) con el historial completo
   (`ctx.session.context`), lanza el script de aviso del SO y deja el aviso
   tambien dentro de la sesion (`ctx.session.synthetic`). Una vez por sesion
   (`dumpDebounceMs` evita repetir cuando el proveedor emite varios eventos del
   mismo fallo). Un archivo por sesion: dos sesiones ya no se sobrescriben.
2. **Sesion nueva** (`ctx.session.hook("context")`): mientras la sesion no tenga
   todavia respuesta del asistente, adjunta los archivos de sesion del repo
   (`.opencode_session_dump*.md`) como `SystemPart` del primer request. Sin gastar
   un turno de generacion y sin escribir en el historial visible. En cuanto hay
   respuesta del asistente deja de inyectar.

## Aviso por sistema operativo

El plugin detecta el SO (`process.platform`) y elige script + lanzador:

| SO | Script | Lanzador |
|---|---|---|
| `win32` | `limit-notify.ps1` | `cmd.exe /c start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -File <ps1> ...` |
| `linux` / `darwin` | `limit-notify.sh` | `/bin/sh <sh> <SessionID> <DumpFile>` |

Detalles que importan:

- **Windows:** el `cmd /c start` es lo que abre una consola propia. Antes se
  lanzaba `powershell.exe` en segundo plano (`stdio: ignore`) y el `Write-Output`
  del ps1 se imprimia a la nada: por eso "no salia ningun aviso en PowerShell".
- **Linux/macOS:** no se asume `pwsh` instalado (era el lanzador anterior y
  fallaba sin dejar rastro). El `.sh` corre con `/bin/sh`, escribe
  `limit-notify.log` junto al dump y, si no tiene terminal (lo normal al
  lanzarlo el servidor), abre una ventana con el primer emulador disponible
  (`$TERMINAL`, `x-terminal-emulator`, `gnome-terminal`, `konsole`, `xterm`, ...)
  y se re-ejecuta dentro. Si no hay ningun emulador, el log sigue siendo la
  prueba de que el limite se detecto.
- Los dos scripts aceptan parametros/argumentos y las variables
  `OPENCODE_LIMIT_SESSION`, `OPENCODE_LIMIT_DUMP`, `OPENCODE_LIMIT_KEEP_OPEN`,
  `OPENCODE_LIMIT_RECOVER`, `OPENCODE_LIMIT_WINDOW`, `OPENCODE_LIMIT_COOLDOWN`,
  `OPENCODE_LIMIT_KILL_WAIT` y `OPENCODE_LIMIT_KILL_NODE`.

## Recuperacion (opt-in, desactivada)

Por defecto (`OPENCODE_LIMIT_RECOVER=0`) el script **solo avisa**: imprime la
sesion, la ruta del dump y donde quedo el log, y nunca cierra nada. Ese default
es deliberado: el limite salta a diario y cerrarte las sesiones solo te quita el
trabajo en curso.

Con `OPENCODE_LIMIT_RECOVER=1` completa la recuperacion: rota la VPN, cierra los
procesos de OpenCode (de los Node solo los que mencionan opencode en su linea de
comandos) y limpia caches con una allowlist de rutas (nunca config ni datos). Un
enfriamiento (`OPENCODE_LIMIT_COOLDOWN`, 90s por defecto) evita repetir la accion
cuando el proveedor emite varios eventos del mismo fallo, y cada corrida deja una
linea en el log: `recuperacion sesion=<id> cerrados=N vpn=<cli> cache=<rutas>`.

Antes de activarlo, dos hechos comprobados: el limite gratuito es **de cuenta**,
no de IP, asi que rotar la VPN no lo reinicia; y cerrar procesos termina **todas**
tus sesiones de OpenCode, incluida la que estas usando.
- `spawn` falla de forma asincrona (ENOENT): el plugin escucha `child.on("error")`
  y lo escribe en el log de opencode.

## Comandos

```
/autosession            # estado (dump, archivos de sesion, inyeccion armada, script del SO)
/autosession dump       # guardar el historial actual
/autosession files      # listar los archivos de sesion del repo
/autosession inject     # forzar la inyeccion en el proximo request
/autosession simulate   # simular el limite: dump + aviso, sin gastar cuota
/autosession reset      # borrar los dumps e invalidar la cache de inyeccion
```

Se registran con `ctx.command.transform` y responden con
`ctx.session.synthetic({ resume: false })`, que aparece en la sesion sin disparar
un turno de generacion.

### Probar el limite sin gastar cuota

```
/autosession simulate
```

Recorre el camino real completo (el mismo `handleFailure` de los eventos): pasa
el error sintetico de `CONFIG.simulatedError` por `isLimitError`, escribe el dump
y lanza el script de aviso del SO. Despues usa **`/autosession reset`** para
borrar la simulacion: deja el dump con un `Motivo` de limite real y no hace falta
que siga en el repo.

Con texto propio decide solo el texto, sin status, asi que sirve para comprobar
si el mensaje real de tu proveedor entra en `LIMIT_PATTERNS`:

```
/autosession simulate Free usage exceeded, subscribe to continue
/autosession simulate Error 400: credit balance too low     # si no matchea, lo dice y no toca el dump
```

### Si el limite se queda "pegado" en todas las sesiones

Sintoma: tras simular (o tras un limite real), **todas** las sesiones del
proyecto, incluidas las nuevas y despues de reiniciar el PC, "parecen" con rate
limit.

Causa: el plugin escribe un dump por sesion (`.opencode_session_dump-<sesion>.md`)
y reinyecta los que encuentra en el repo en el primer turno de **cada sesion
nueva** de ese proyecto. El dump incluye su cabecera (`- Motivo: ... 429 ...`),
asi que el error viejo vuelve a entrar en el prompt una y otra vez. Los archivos
viven en disco, por eso sobreviven al reinicio.

Solucion:

1. `/autosession reset` (borra los dumps y limpia la cache), o a mano:
   `rm .opencode_session_dump*.md` en la raiz del proyecto.
2. Desde esta version la inyeccion pasa por `scrubInjectedContext`: la cabecera
   del dump y cualquier linea que case con `LIMIT_PATTERNS` no llegan al prompt.
3. Si despues de borrar los dumps la sesion sigue limitada, ya no es del plugin:
   es la cuota de la cuenta/modelo gratuito (`dialog.usageExceeded.freeTier`).
   Cambia de modelo o espera la ventana de cuota.

## Configuracion

Todo en el objeto `CONFIG` de `autosession.ts`:

| Clave | Default | Para que |
|---|---|---|
| `injectRepoContext` | `true` | adjuntar los archivos de sesion al primer turno |
| `runNotifyScript` | `true` | ejecutar el script de aviso del SO al detectar el limite |
| `notifyInSession` | `true` | mostrar el aviso tambien dentro de la sesion (`synthetic`) |
| `notifyKeepOpenSeconds` | `20` | segundos que la ventana del aviso permanece visible |
| `stripLimitFromInjection` | `true` | quitar el `Motivo`/429 del dump antes de inyectarlo |
| `sessionFilePatterns` | `[/^\.opencode_session_dump.*\.md$/i]` | que cuenta como archivo de sesion |
| `skipDirs` | `node_modules`, `.git`, `dist`, ... | directorios no recorridos |
| `maxFiles` | `5` | tope de archivos leidos |
| `maxCharsPerFile` | `20000` | tope por archivo |
| `maxTotalChars` | `60000` | tope del dump |
| `maxInjectChars` | `12000` | tope del bloque inyectado en el prompt |
| `dumpDebounceMs` | `5000` | ventana anti-repeticion del dump |
| `simulatedError` | `{ type: "provider-error", message: "Free usage limit exceeded (simulado)", status: 429 }` | error que dispara `/autosession simulate` |

El dump y el log quedan ignorados en git (`.opencode_session_dump*.md` y `*.log`).

## Instalar

```
python setup.py --only opencode-auto-session --global --platform opencode
```

Copia `autosession.ts` a `~/.config/opencode/plugins/opencode-auto-session.ts` y
`limit-notify.ps1` + `limit-notify.sh` a
`~/.config/opencode/plugins/opencode-auto-session/`, y reinicia OpenCode.
Verificacion: `opencode plugin list` debe mostrar `opencode-auto-session` (antes
salia como `-`, que es como el cargador marca un plugin que no valida).

## Tests

```
npm run typecheck   # tsc contra los tipos reales de @opencode/plugin@2.0.31
npm test            # smoke.mjs (JS) + notify-sh.mjs (script POSIX)
```

`test/smoke.mjs` cubre: forma del default export, deteccion de limite (texto y
status), resolucion del script segun SO, lanzador y argumentos por plataforma, el
log de aviso, el recorrido de archivos de sesion, los topes de recorte, el ciclo
completo limite -> dump -> inyeccion en sesion nueva, el scrub de la cabecera del
dump y los comandos (incluido `reset`). `CONFIG.runNotifyScript = false` en el
test para no abrir una ventana.

`test/notify-sh.mjs` ejecuta `limit-notify.sh` de verdad: `sh -n`, la delegacion
en un emulador de terminal falso, el caso sin terminal (imprime y escribe el log)
y el paso de variables de entorno. Se salta en Windows.
