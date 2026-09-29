import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const dist = "app/static/dist";

if (!existsSync(join(dist, "index.html"))) {
  throw new Error("Frontend smoke test failed: dist/index.html is missing.");
}

const index = readFileSync(join(dist, "index.html"), "utf8");

if (!index.toLowerCase().includes("<!doctype html>")) {
  throw new Error("Frontend smoke test failed: index.html is not a valid HTML document.");
}

const assetRefs = [...index.matchAll(/(?:src|href)="([^"]+\.(?:js|css))"/g)].map((m) => m[1]);
if (assetRefs.length === 0) {
  throw new Error("Frontend smoke test failed: no JS/CSS build assets referenced by index.html.");
}

for (const ref of assetRefs) {
  const normalized = ref.replace(/^\//, "");
  if (!existsSync(join(dist, normalized))) {
    throw new Error(`Frontend smoke test failed: referenced asset is missing: ${ref}`);
  }
}

const files = readdirSync(dist, { recursive: true });
const jsCount = files.filter((file) => String(file).endsWith(".js")).length;

if (jsCount === 0) {
  throw new Error("Frontend smoke test failed: production JavaScript bundle was not emitted.");
}

console.log(`Frontend smoke test passed: ${jsCount} JS bundle(s), ${assetRefs.length} referenced asset(s).`);
