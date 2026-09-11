/**
 * Reports custom properties that are read but never defined.
 *
 * A dangling `var(--x)` is not a no-op: an invalid substitution makes the whole declaration
 * compute to `unset`, which is the *initial* value, not the previous cascade winner. So a leftover
 * `max-height: var(--gone)` after `max-height: 100cqh` yields `none` and removes the cap - that is
 * how deleting a token silently broke page scrolling once. This is what a repo-wide grep would
 * catch, made a command so it does not depend on remembering to grep.
 *
 * Names built by interpolation (`var(--elevation-#{$slot})`) cannot be resolved statically: uses
 * are skipped, and an interpolated *definition* registers its literal prefix so the concrete names
 * it generates (`--elevation-3`) still count as defined.
 *
 * Usage: node tools/check-css-vars.mjs [--allow name,name]
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("../src", import.meta.url).pathname;
const EXTENSIONS = [".scss", ".css", ".ts", ".html"];
// Provided by Angular Material / MDC at runtime, so they are never defined in this repo.
const EXTERNAL_PREFIXES = ["--mat-", "--mdc-"];

const allowIndex = process.argv.indexOf("--allow");
const allowed = new Set(allowIndex === -1 ? [] : (process.argv[allowIndex + 1] ?? "").split(",").filter(Boolean));

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) yield* walk(path);
    else if (EXTENSIONS.some((extension) => path.endsWith(extension))) yield path;
  }
}

const defined = new Set();
const definedPrefixes = [];
const uses = new Map(); // name -> Set("file:line")

for (const file of walk(ROOT)) {
  const text = readFileSync(file, "utf8");
  text.split("\n").forEach((line, index) => {
    // Definitions: `--name:` in a declaration, or a name assigned from TS/HTML (setProperty("--name").
    for (const match of line.matchAll(/(--[A-Za-z0-9_-]+)(#\{[^}]*\})?\s*[:'"]/g)) {
      if (match[2]) definedPrefixes.push(match[1]);
      else defined.add(match[1]);
    }
    // Uses: var(--name), skipping interpolated names and any read that supplies a fallback -
    // `var(--x, 100%)` is an intentional override hook, not a dangling reference: the property
    // still gets a usable value when nothing sets --x.
    for (const match of line.matchAll(/var\(\s*(--[A-Za-z0-9_-]+)(#\{)?\s*(,)?/g)) {
      if (match[2] || match[3]) continue;
      const where = `${relative(ROOT, file)}:${index + 1}`;
      uses.set(match[1], (uses.get(match[1]) ?? new Set()).add(where));
    }
  });
}

const dangling = [...uses.entries()]
  .filter(([name]) => !defined.has(name))
  .filter(([name]) => !EXTERNAL_PREFIXES.some((prefix) => name.startsWith(prefix)))
  .filter(([name]) => !definedPrefixes.some((prefix) => name.startsWith(prefix)))
  .filter(([name]) => !allowed.has(name))
  .sort(([a], [b]) => a.localeCompare(b));

if (dangling.length === 0) {
  console.log(`check-css-vars: ${uses.size} custom properties read, all defined.`);
  process.exit(0);
}

console.error("check-css-vars: custom properties read but never defined\n");
for (const [name, places] of dangling) {
  console.error(`  ${name}`);
  for (const place of [...places].sort()) console.error(`      ${place}`);
}
console.error(
  `\n${dangling.length} dangling custom propert${dangling.length === 1 ? "y" : "ies"}. ` +
    `Define it, drop the declaration, or pass --allow <name> if it is deliberately provided elsewhere.`
);
process.exit(1);
