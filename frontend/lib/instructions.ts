/**
 * `instructions_vi` / `instructions_en` arrive from GET /api/challenge as two
 * lines: the setup, then the mission. The mission is the whole game, so the UI
 * sets it as the headline and demotes the setup.
 *
 * Nothing here is hardcoded game text — if `challenge.yaml` is rewritten to a
 * single line, that line becomes the mission.
 */
export function splitInstructions(text: string): {
  setup: string | null;
  mission: string;
} {
  const lines = text
    .trim()
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length <= 1) return { setup: null, mission: lines[0] ?? "" };
  return { setup: lines[0], mission: lines.slice(1).join(" ") };
}
