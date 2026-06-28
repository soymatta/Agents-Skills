---
name: academic-source-search
description: Busca fuentes cientificas verificadas en bases de datos academicas. Filtra por calidad, extrae metadatos y genera citas preliminares.
---

# Academic Source Search

Busqueda sistematica de literatura cientifica para respaldar trabajos academicos.

---

## Bases de Datos por Prioridad

| Prioridad | Base | Acceso | URL |
|-----------|------|--------|-----|
| 1 | Google Scholar | Gratuito | https://scholar.google.com |
| 2 | arXiv | Gratuito Open Access | https://arxiv.org |
| 3 | PubMed / PMC | Gratuito | https://pubmed.ncbi.nlm.nih.gov |
| 4 | SciELO | Gratuito LatAm | https://scielo.org |
| 5 | Redalyc | Gratuito LatAm | https://www.redalyc.org |
| 6 | Dialnet | Gratuito | https://dialnet.unirioja.es |
| 7 | IEEE Xplore | Abstracts gratis | https://ieeexplore.ieee.org |
| 8 | Scopus | Abstracts gratis | https://www.scopus.com |
| 9 | Web of Science | Abstracts gratis | https://www.webofscience.com |
| 10 | JSTOR | Lectura limitada gratis | https://www.jstor.org |
| 11 | DOAJ | Gratuito Open Access | https://doaj.org |
| 12 | Open Access Theses | Tesis gratis | https://oatd.org |
| 13 | PubMed Books | Libros academicos gratis | https://www.ncbi.nlm.nih.gov/books |
| 14 | Google Books Preview | Fragmentos | https://books.google.com |

---

## Formulacion de Busquedas

### Operadores booleanos (funcionan en Scholar, Scopus, WoS)
```
"cambio climatico" AND "energia renovable"          → ambos terminos exactos
("machine learning" OR "deep learning") AND "ERP"   → cualquiera de los dos + ERP
"climate change" -"climate change denial"           → excluir termino
intitle:"neural networks"                            → solo en titulo
author:"name"                                        → por autor
source:"Nature"                                      → por revista
```

### Filtros recomendados
- Rango de anos: `2019..2026`
- Tipo: `review`, `journal article`, `conference`
- Ordenar por: relevancia, citaciones, fecha

### Estrategia
1. Busqueda amplia con terminos clave → identificar 10-20 candidatos
2. Leer abstract de cada uno → seleccionar 5-10 relevantes
3. Buscar articulos citados por y que citan a los seleccionados (bola de nieve)
4. Extraer DOI, autores, ano, journal, abstract, keywords, citacion

---

## Extraccion de Metadatos

Para cada fuente seleccionada, extraer:

```yaml
title: "Titulo completo"
authors: ["Apellido, N.; Apellido, N."]
year: 2024
journal: "Nombre de Revista"
volume: "12"
issue: "3"
pages: "45-67"
doi: "10.xxxx/xxxxx"
url: "https://doi.org/10.xxxx/xxxxx"
type: "journal" | "conference" | "book" | "thesis" | "preprint"
abstract: "Texto del resumen"
keywords: ["word1", "word2"]
citations_count: 150
```

---

## Verificacion

- DOI: verificar que resuelve en https://doi.org/XXXX
- Acceso: intentar descargar PDF o leer abstract via `webfetch`
- Fecha: confirmar que coincide con la publicacion real
- Autores: verificar afiliacion institucional cuando sea posible
- Journal: verificar indexacion (JCR, Scopus, Latindex)

---

## Output Esperado

Al final de la busqueda, entregar una tabla resumen:

| # | Autores | Ano | Titulo | Fuente | DOI/URL | Tier | Verificado |
|---|---------|-----|--------|--------|---------|------|------------|
| 1 | Perez, J. | 2024 | "Title" | Nature | doi:... | 1 | [x] |
| 2 | ... | ... | ... | ... | ... | ... | ... |

---

## Restricciones
- NO usar fuentes sin DOI o URL verificable
- NO inventar metadatos
- NO incluir fuentes sin leer al menos el abstract
- NO priorizar cantidad sobre calidad
