---
name: vault-search
description: Use when the user asks to find information, notes, topics, or files inside their Obsidian vault / markdown notes directory. Also use when the user says "buscar", "search", "find", "donde esta", "encuentra", "localiza", or asks about something they remember writing but cannot locate. This skill searches note content, filenames, tags, and [[wiki-links]] using grep and glob. Use AFTER vault-indexer (initial index) and BEFORE vault-organizer (to avoid duplicating existing notes).
compatibility: Requires vault-indexer agent for initial indexing and scope. Does not make sense without vault-indexer.
---

# Vault Search

Search for topics within the vault using glob and grep. Requires `vault-indexer` agent — this skill is a supplement to the main vault agent, not a standalone tool. El vault de notas contiene conocimiento previo que debe reutilizarse; la mayoria de las preguntas pueden responderse con informacion ya escrita. Busca primero antes de asumir que no existe.

## When to use
- User asks to find information, notes, topics, or files in their vault
- Keywords: "buscar", "search", "find", "donde esta", "encuentra", "localiza"
- User remembers writing something but cannot locate it
- Before creating new notes (to avoid duplicates)

## When NOT to use
- Organizing or placing new notes (use `vault-organizer`)
- External research (use `vault-indexer` agent)
- Editing or modifying file content

## Procedure
1. Receive the topic from the user
2. Use `grep` to find files with relevant keywords
3. Use `glob` to find files by name patterns
4. Exclude system folders: `.git`, `.obsidian`, `.opencode`, `.trash`, `.cache`, `node_modules`, `venv`, `env`, `__pycache__`
5. Search by keywords, file names, frontmatter tags, and `[[note-name]]` links

## Response
- List all relevant files with pertinent sections
- Indicate where info was found
- If no results: inform and suggest reformulating the search

## Restrictions
- **DO NOT** modify files
- **DO NOT** invent information
- For external research, use the `vault-indexer` agent (it includes a `vault-researcher` sub-agent)

## Integration
- `vault-indexer` — required parent agent (includes `vault-researcher` sub-agent)
- `vault-organizer` — where to place new info

## Dependencies
Requires `vault-indexer` agent for initial indexing and scope.

## Error handling
- **No results found:** Suggest reformulating search with different keywords
- **Too many results:** Narrow search with more specific terms or file patterns
- **vault-indexer not available:** Use glob/grep directly but with limited scope
- **Binary files matched:** Exclude with glob patterns (*.pdf, *.png, etc.)

## File structure
```
vault-search/
└── SKILL.md
```
