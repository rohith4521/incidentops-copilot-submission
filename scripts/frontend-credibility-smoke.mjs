import { readFileSync } from "node:fs";

const source = readFileSync("src/App.tsx", "utf8");

const forbiddenPatterns = [
  { pattern: /\.catch\(\(\)\s*=>\s*null\)/, message: "swallowed API failures are forbidden" },
  { pattern: /\/api\/runbooks\/\$\{runbookId\}\/execute/, message: "frontend must not claim production execution; use the guarded simulation endpoint" },
  { pattern: /retention_hash\s*:/, message: "frontend must not invent cryptographic retention hashes" },
  { pattern: /cryptographic hash sealed/i, message: "frontend must not claim cryptographic sealing without measured backend evidence" },
];

for (const { pattern, message } of forbiddenPatterns) {
  if (pattern.test(source)) throw new Error(`Frontend credibility contract failed: ${message}`);
}

for (const required of [
  "/api/runbooks/${runbookId}/simulate",
  "/api/postmortems/commit",
  "response.ok",
]) {
  if (!source.includes(required)) throw new Error(`Frontend credibility contract failed: missing ${required}`);
}

console.log("Frontend credibility contract passed.");