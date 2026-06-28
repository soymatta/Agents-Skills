---
name: vault-search
description: Searches for specific topics within the Obsidian notes vault using glob and grep.
---

# Vault Search

Search for topics within the vault using glob and grep.

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
- For external research, use `vault-researcher`

## Integration
- `vault-indexer` — initial vault index
- `vault-organizer` — where to place new info
- `vault-researcher` — external research if needed
