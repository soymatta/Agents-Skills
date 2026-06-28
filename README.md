# Agents-Skills

Personal collection of AI agents and skills for various tasks.

## Agents

| Agent | Description |
|---|---|
| `vault-indexer` | Reads and indexes all .md notes in the vault. Answers exclusively from file contents. |
| `vault-researcher` | Investigates external sources to verify concepts that are incorrect or unclear in the vault. |
| `academic-researcher` | Produce trabajos academicos en Markdown (APA/IEEE/Vancouver). Solo fuentes cientificas. |

## Skills

| Skill | Description |
|---|---|
| `vault-search` | Searches for topics within the vault using glob and grep. |
| `vault-organizer` | Suggests where and how to organize information in the vault. |
| `research-pipeline` | Structured quantitative research process for prediction markets. |
| `goal-pursuit` | Sets a quantitative target and runs an autonomous loop until it is met. |
| `telegram-notify` | Sends Telegram notifications for project events. |
| `backtest-run` | Runs backtests with project-specific configuration. |
| `backtest-validate` | Expert validation of backtest quality with 5-dimension scoring. |
| `academic-source-search` | Busca fuentes cientificas en bases de datos academicas. |
| `citation-style-guide` | Referencia de formato APA / IEEE / Vancouver para citas y referencias. |
| `content-humanizer` | Pase final anti-deteccion IA. Ajusta estructura, lexico y fluidez. |

## Installer

```bash
python scripts/setup.py
```

Detecta el agente AI (OpenCode, Claude Code, VS Code, Kimi), permite seleccionar
que agents/skills instalar, y los copia al directorio del proyecto o global.
