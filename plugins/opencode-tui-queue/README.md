# opencode-tui-queue

Encola los prompts escritos en el TUI mientras la sesión está ocupada y los
envía de uno en uno cuando queda libre. Nada se pierde: escribir mientras se
trabaja se acumula y se procesa al terminar.

## Comportamiento

- **Mientras la sesión está ocupada**, lo que escribas se **encola por defecto**
  en lugar de interrumpir el turno (captura automática `CONFIG.captureAllBusy`).
  Se muestra un toast de acuse y el mensaje queda guardado en
  `~/.config/opencode/.opencode-queue.json`. El sufijo `texto /queue` sigue
  válido (se limpia al encolar) y con `CONFIG.captureAllBusy: false` vuelve al
  modo sufijo explícito.
- **Al quedar la sesión libre** (idle), se envía **uno** de la cola por idle.
  Si escribes varios, se turnan sin pisarse.
- **`/queue list | front | now <texto> | stop | start | flush [all]`**:
  gestiona la cola con toasts en el TUI. Funciona como slash command
  (registrado por `commands/queue.md`) y, si no llegara a registrarse, también
  como texto plano reconocido por el plugin.
- Los mensajes encolados se **persisten**: sobreviven a reinicios de OpenCode.
- La captura se puede pausar con `/queue stop` (no encola ni envía).

### Detalles del envío

- El hook `chat.message` muta `output.parts` a un placeholder
  `{synthetic: true, ignored: true}`: el mensaje NO llega al modelo ni se
  muestra en el TUI como turno consumido (patrón validado en el motor de
  eventos de OpenCode).
- Se saltea sesiones subagente (parentID) y mensajes procedentes del plugin
  `opencode-telegram-answers` (que ya pasaron por SU cola): nunca se duplica.
- Un mensaje cuya reinyección falló vuelve al frente de la cola y se reintenta
  en el próximo idle: no se pierde nada.

## Estructura

```
opencode-tui-queue/
├── queue.ts                ← EL plugin (CONFIG al inicio, funciones puras exportadas)
├── commands/queue.md       ← registro del slash command /queue
├── test/smoke.mjs          ← tests de la lógica pura (sin red ni TUI)
├── docs/ARQUITECTURA.md    ← cómo funciona por dentro
├── install.ps1             ← copia el .ts plano a ~/.config/opencode/plugins/
├── package.json
└── tsconfig.json
```

## Instalación

Desde el repo:

```
python setup.py --all --platform opencode --global
```

Esto copia `queue.ts` a `~/.config/opencode/plugins/tui-queue.ts` y
`commands/queue.md` a `~/.config/opencode/commands/`. En ese momento OpenCode
lo autoload en el próximo arranque.

## Verificación

```
npm run typecheck   # tsc (nodenext, strict)
npm test            # smoke (lógica pura) + integration (hooks con cliente falso)
```

Cosas que se pueden ver en `opencode log` (service `tui-queue`): `encolado
(trailing /queue)`, toasts caídos a log si el TUI no las muestra, y errores de
reinyección.