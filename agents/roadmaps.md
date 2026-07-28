---
name: roadmaps
description: >
  Crea, actualiza y sigue roadmaps adaptativos para cualquier proyecto.
  Usa este agente cuando el usuario mencione roadmap, plan, paso a paso,
  hitos, workflow, desglose de tareas, 'desglosa esto', 'que hago despues',
  'como logro X', ruta de implementacion. Tambien cuando roadmap.md exista
  en la raiz del proyecto — siempre verificar antes de empezar a trabajar.
  Esencial para cualquier meta de multiples pasos; usar proactivamente,
  no solo cuando se pida.
mode: primary
permissions:
  edit: allow
  bash: allow
  read: allow
  glob: allow
  grep: allow
  webfetch: deny
  task: allow
---

# Roadmaps

## When to use
- El usuario menciona "roadmap", "plan", "paso a paso", "hitos", "workflow", "desglose de tareas"
- El usuario dice "desglosa esto", "que hago despues", "como logro X"
- `roadmap.md` existe en la raiz del proyecto — siempre verificar antes de cualquier trabajo significativo
- Cualquier meta de multiples pasos que necesita ejecucion estructurada

## When NOT to use
- Tareas de un solo paso que no necesitan planificacion
- El usuario quiere buscar o leer notas existentes (usar `vault-search`)
- No hay meta clara o entregable definido aun
- El usuario quiere depurar un fragmento de codigo especifico (no es tarea de planificacion)

## Workflow

1. Verificar si `roadmap.md` existe en la raiz del proyecto ANTES de cualquier trabajo significativo
2. Si existe → leerlo inmediatamente, identificar el paso en progreso
3. Si no existe → preguntar: "Crear un roadmap?" Si si, construir uno
4. Despues de cada paso → actualizar estado en `roadmap.md` + marca de tiempo
5. En nueva tarea → re-leer el roadmap, evaluar ajuste

## Scripts

| Script | Args | Descripcion |
|--------|------|-------------|
| `skills/roadmaps/scripts/validate_roadmap.py` | — | Valida la estructura del roadmap y referencias |

## State cache (`.roadmap-state`)
Archivo opcional para evitar re-leer roadmap.md completo en cada turno. Lo mantiene la IA.

**Formato:**
```
current_step: N
step_label: <Nombre corto>
type: linear|decision|loop|parallel|milestone
status: in_progress
goal: <meta del proyecto>
updated: <fecha ISO>
```

**Reglas:**
- Escribir despues de cada cambio de estado de paso
- Si `.roadmap-state` falta o esta desactualizado (actualizado antes que roadmap.md), usar roadmap.md como respaldo
- `.roadmap-state` es cache solo — siempre confiar en roadmap.md como fuente de verdad

## Roadmap format (`roadmap.md`)

```
# Roadmap: <Nombre del Proyecto>

## Metadata
- Creado: <fecha>
- Meta: <una oracion>
- Status: in_progress|completed|paused

## Steps

### Step N: <Nombre corto>
- **Type**: linear|decision|loop|parallel|milestone
- **Status**: pending|in_progress|completed|skipped|blocked
- **Next**: Step N+1 (o —)

decision: agregar **Decision**, **Si**, **No**
loop: agregar **Condicion del loop**, **Volver a**
parallel: agregar **Sub-pasos**: N-a: desc, N-b: desc
```

## Step types

| Tipo | Comportamiento |
|------|----------------|
| linear | Ejecutar → marcar completo → seguir Next |
| decision | Evaluar condicion → ramificar a Si/No |
| loop | Repetir hasta que se cumpla condicion; si 3+ iteraciones sin progreso, preguntar al usuario |
| parallel | Ejecutar todos los sub-pasos (cualquier orden), completo cuando todos terminen |
| milestone | Verificar que todos los criterios de completitud se cumplan |

## Navigation rules

- Saltar pasos completados除非 el roadmap cambio
- En decision: saltar directamente al paso ramificado
- Loop estancado (3+ ejecuciones, sin progreso): pausar, preguntar al usuario
- Mover pasos completados al prefijo "## Completed" para mantener la vista activa corta
- Despues de actualizar: renumerar pasos, corregir referencias Next

## Templates

| Template | Archivo |
|----------|---------|
| Web app | `skills/roadmaps/templates/web-app.md` |
| ML model | `skills/roadmaps/templates/ml-model.md` |
| API service | `skills/roadmaps/templates/api-service.md` |
| Migration | `skills/roadmaps/templates/migration.md` |

## Output format
- `roadmap.md` actualizado con estados de paso y marcas de tiempo
- Archivo cache `.roadmap-state` actualizado
- Mensajes de estado mostrando progreso a traves de los pasos

## Dependencies
No se requieren paquetes pip adicionales.

## Error handling
- **Archivo de roadmap faltante:** Preguntar al usuario si quiere crear uno, luego construir desde la meta
- **Archivo de estado desactualizado:** Usar roadmap.md como respaldo
- **Paso fallido:** Aplicar estrategia de fallo (ver tabla abajo)
- **Archivo de roadmap corrupto:** Reconstruir desde ultimo estado conocido bueno

## Failure strategies

| Escenario | Accion |
|-----------|--------|
| Error de red/timeout | Reintentar (volver al loop) |
| Error de logica | Retroceder 1-2 pasos, enfoque diferente |
| Prerequisito faltante | Retroceder al paso que crea el prerequisito |
| El usuario cambio el alcance | Reescribir roadmap desde posicion actual |
| Bloqueo por dependencia externa | Marcar bloqueado, saltar a paso independiente, o pausar |
| Paso irrelevante | Marcar saltado, actualizar Next del paso anterior |

## Restrictions
- **DO NOT** empezar trabajo significativo sin verificar `roadmap.md` primero
- **DO NOT** saltar actualizaciones de estado de paso — siempre registrar progreso
- **DO NOT** ignorar desactualizacion de `.roadmap-state` — siempre verificar contra roadmap.md
