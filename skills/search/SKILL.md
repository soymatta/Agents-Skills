---
name: search
description: Searches for specific topics within the Obsidian notes vault.
---

# Notes Search Skill

## Objective
Search for specific topics within the Obsidian notes vault using glob and grep tools.

## Behavior

### 1. Search Execution
- Receive the topic to search from the user
- Use `grep` to find files containing relevant keywords
- Use `glob` to find files by name patterns
- **IMPORTANT**: Exclude irrelevant folders:
  - Folders starting with `.` (e.g., `.git`, `.obsidian`, `.opencode`, `.trash`, `.cache`)
  - `node_modules`, `venv`, `env`, `.venv`, `__pycache__`

### 2. Search Strategies
- Search by keywords in content
- Search by file names
- Search by tags (if they exist in frontmatter)
- Follow internal links `[[note-name]]` related to the topic

### 3. Response
- List all relevant files found
- Extract and show pertinent sections
- Indicate where the information was found
- If no results: inform and suggest reformulating the search

## Restrictions
- **DO NOT** modify files
- **DO NOT** invent information
- Only search within the project vault
- For external research, use `researcher` agent

## Integration
This skill works together with:
- `notes` agent: for the initial vault index
- `organizer` skill: to suggest where to place new information
- `researcher` agent: for external searches if necessary