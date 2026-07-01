---
name: vault-organizer
description: Use when the user asks where to place, organize, move, or structure information in their Obsidian vault / markdown notes. Also use when the user says "organizar", "donde pongo", "categorizar", "estructurar", "folder", "carpeta", or wants to create new notes in the right location. This skill analyzes vault structure and suggests placement without showing or editing content. Use AFTER vault-search (to avoid duplicating existing notes) and BEFORE creating new files.
compatibility: Requires vault-indexer agent for structure understanding, and vault-search to find related existing notes. Does not make sense without vault-indexer.
---

# Vault Organizer

Analyze the vault structure and suggest where to place new information. Requires `vault-indexer` agent — this skill is a supplement to the main vault agent. Does not show or edit existing content. Una buena organizacion hace que el vault sea sostenible a largo plazo: un nota mal ubicada es una nota perdida. El objetivo es que cualquier nota nueva sea encontrable por ti mismo semanas o meses despues.

## Procedure
1. Index the folder structure with `glob` (skip system folders)
2. Identify categories, naming patterns, and note relationships
3. When user asks where to place a topic:
   - Indicate the most appropriate folder
   - Suggest new note or append to existing
   - Recommend note name and related links
4. If insufficient context: ask for more info, suggest `vault-researcher` or `vault-search`

## Restrictions
- **DO NOT** show file content
- **DO NOT** edit or modify files
- **DO NOT** invent information

## Integration
- `vault-indexer` — required parent agent
- `vault-search` — find related notes
- `vault-researcher` — investigate topics before organizing
