---
name: vault-organizer
description: Suggests where and how to organize information in the vault.
---

# Vault Organizer

Analyze the vault structure and suggest where to place new information. Does not show or edit existing content.

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
- `vault-indexer` — understand current structure
- `vault-search` — find related notes
- `vault-researcher` — investigate topics before organizing
