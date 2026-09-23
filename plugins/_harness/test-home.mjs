// Harness portable para probar plugins de OpenCode sin red ni usuario.
// Aisla el HOME para que los plugins lean/escriban su state en un temporal
// (nunca tocan ~/.config/opencode real). Llamar ANTES de importar el .ts.
import { mkdtempSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

export function setupTestHome(prefix = "plugin-test-") {
  const dir = mkdtempSync(join(tmpdir(), prefix))
  process.env.USERPROFILE = dir // Windows: os.homedir() lo usa
  process.env.HOME = dir // POSIX
  process.env.TELEGRAM_BOT_TOKEN = "test-token"
  process.env.TELEGRAM_CHAT_ID = "12345"
  return dir
}
