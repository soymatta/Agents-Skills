---
name: content-humanizer
description: >
  Revision final del documento para reducir patrones detectables por IA
  (Turnitin, GPTZero, Originality). Ajusta estructura, lexico y fluidez
  manteniendo el rigor academico. Se ejecuta SOLO al final, cuando el
  contenido esta completo y referenciado. Incluye script de deteccion
  para verificar que el texto pase como humano.
---

# Content Humanizer

Pase final de humanizacion. Ejecutar UNICAMENTE cuando el documento este
completo, revisado y con todas las referencias verificadas.

**No alterar:** datos, citas, referencias, estructura academica, metadatos.

---

## 1. HUMANIZAR — Aplicar tecnicas

### 1.1 Palabras y frases de alta frecuencia IA

| Evitar | Usar en su lugar |
|--------|-----------------|
| "en el ambito de" | "en", "dentro de" |
| "es fundamental destacar" | "cabe senalar", "es relevante" |
| "cabe mencionar que" | eliminarlo, ir directo al punto |
| "en otras palabras" | reformular directamente |
| "en este sentido" | "por ello", "asi", "entonces" |
| "como se menciono anteriormente" | referenciar seccion, no repetir |
| "no solo... sino tambien" | usar max 1 vez por documento |
| "resulta interesante notar" | eliminarlo, no aporta |
| "vale la pena destacar" | solo si es realmente necesario |
| "en relacion con" | "sobre", "respecto a" |
| "a modo de ejemplo" | "por ejemplo", "como" |
| "cabe preguntarse" | pregunta directa sin preambulo |
| "es importante considerar" | eliminarlo o reformular |
| "desde una perspectiva" | "desde", "segun" |
| "en consecuencia" | "por tanto", "asi que" |
| "asimismo" | "tambien", "ademas" (max 1-2 veces) |
| "por otra parte" | "en contraste", "sin embargo" |
| "resulta evidente que" | afirmacion directa |
| "cabe destacar que" | eliminarlo |
| "es preciso senalar" | eliminarlo |
| "con respecto a" | "sobre", "respecto a" |

### 1.2 Romper patrones estructurales

**Paralelismo excesivo:** variar estructura gramatical entre parrafos.
**Transiciones mecanicas:** no iniciar todos los parrafos con conector logico.
**Cierre artificial:** no terminar cada seccion con "En conclusion...".

### 1.3 Variacion de estructura sintactica

```
ANTES (IA):  El estudio analizo 150 pacientes. Los resultados mostraron
             una mejora significativa. La desviacion estandar fue minima.

DESPUES:     En el estudio, 150 pacientes fueron analizados durante seis
             meses. Los resultados, que mostraron una mejora significativa,
             se alinean con investigaciones previas. La desviacion estandar,
             cabe notar, se mantuvo dentro de rangos esperados.
```

Reglas:
- Alternar: SVO / verbo-sujeto / frase introductoria
- No mas de 2 oraciones seguidas con la misma estructura
- Cada parrafo: 1 oracion larga (>25 palabras) por cada 2 cortas (<15)

### 1.4 Variacion de apertura de parrafo

Ningun parrafo debe comenzar igual que los 2 anteriores. Rotar entre:
afirmacion directa, pregunta retorica, conector suave, dato especifico,
referencia temporal, condicion.

### 1.5 Variacion de vocabulario

| Concepto | Alternativas |
|----------|-------------|
| "demuestra" | "sugiere", "indica", "revela", "deja ver", "apunta a", "evidencia" |
| "importante" | "relevante", "significativo", "determinante", "clave" |
| "analiza" | "examina", "evalua", "estudia", "aborda", "revisa", "explora" |
| "resultado" | "hallazgo", "outcome", "desenlace", "producto", "consecuencia" |
| "muestra" | "evidencia", "refleja", "expone", "revela", "presenta" |
| "significativo" | "considerable", "notable", "sustancial", "apreciable" |

No usar la misma palabra mas de 2 veces en 3 parrafos consecutivos.

### 1.6 Puntuacion natural

Los textos de IA evitan `;`, `:`, `()`, `—`. Agregarlos:
- 1-2 puntos y coma por cada 10 oraciones
- 1-2 guiones largos por seccion
- Parentesis para aclaraciones (1-2 por seccion)
- Dos puntos para introducir explicaciones

### 1.7 Burstiness

Mezclar oraciones de 5 a 40+ palabras. Desviacion estandar de longitud >12.

### 1.8 Voz activa > pasiva

Max 20% de oraciones en pasiva (40% en metodologia).

### 1.9 Imperfecciones controladas

1-2 por cada 3 secciones: oracion iniciando con "Y"/"Pero",
parrafo mas corto/largo, anfora, conector no ideal.

---

## 2. DETECTAR — Verificar con detect_ai.py

Una vez humanizado el documento, ejecutar el detector local para confirmar
que el texto pase como humano:

```bash
# Instalar dependencias (1 vez)
pip install transformers torch

# Probar el documento completo
python skills/content-humanizer/detect_ai.py --file documento.md --verbose
```

### Interpretacion de resultados

```
  AI:   12.3%            ← probabilidad de ser IA (debe ser <50%)
  Human: 87.7%           ← probabilidad de ser humano
  Verdict: PASA           ← PASA o DETECTADO
```

| Resultado | Significado | Accion |
|-----------|-------------|--------|
| AI < 30% | Texto humano | Listo. Entregar. |
| AI 30-50% | Texto dudoso | Revisar secciones senaladas, aplicar mas variacion |
| AI > 50% | Texto detectado | Repetir humanizacion en secciones con mayor puntaje |
| AI > 70% | Texto muy detectable | Reescribir desde cero con las tecnicas de este skill |

### Analisis por seccion (--verbose)

El detector senala que secciones tienen mayor probabilidad AI.
Aplicar humanizacion adicional especificamente en esas secciones
y volver a ejecutar el detector.

### Si no se puede instalar transformers

Usar detectores web via `webfetch`:
1. Enviar texto a https://www.zerogpt.com (gratuito, sin API key)
2. Enviar a https://gptzero.me (gratuito limitado)
3. Comparar resultados entre ambos
4. Si ambos dicen "AI", volver al paso 1 con mas tecnicas

---

## 3. ITERAR — Loop de verificacion

```
while True:
    humanizar(documento)
    resultado = detectar(documento)
    if resultado.verdict == "PASA":
        break
    else:
        humanizar(resultado.secciones_problematicas)
```

Maximo 3 iteraciones. Si despues de 3 intentos sigue detectado,
revisar manualmente las secciones mas problematicas.

---

## Checklist Final

- [ ] Escanear y reemplazar frases de la tabla roja
- [ ] Variar apertura de parrafos (ninguno igual a los 2 anteriores)
- [ ] Dividir o unir oraciones para romper uniformidad
- [ ] Insertar 2-3 incisos con guiones o parentesis
- [ ] Convertir pasiva a activa (donde corresponda)
- [ ] Verificar burstiness: desviacion estandar de longitud >12
- [ ] Contar conectores repetidos y reemplazar
- [ ] No hay "como se menciono anteriormente" ni similares
- [ ] Cada seccion termina sin cierre forzado
- [ ] **Ejecutar detect_ai.py → Verdict: PASA**

---

## Restricciones

- **DO NOT** modificar datos, cifras, fechas, nombres
- **DO NOT** alterar citas textuales ni sus comillas o formato
- **DO NOT** eliminar o modificar referencias
- **DO NOT** cambiar estructura academica (secciones, headers)
- **DO NOT** agregar informacion nueva
- **DO NOT** eliminar informacion relevante
- **DO NOT** reducir el rigor academico o la precision tecnica
