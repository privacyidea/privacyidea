/**
 * Reports Angular Material component tokens that the stylesheets set but Material never reads.
 *
 * Setting `--mat-button-outlined-label-text-color` only changes anything because Material's own rule
 * contains `var(--mat-button-outlined-label-text-color, ...)`. A name Material does not read (for
 * example a renamed or removed token such as `--mat-stroked-button-ripple-color`) is silently dead:
 * nothing fails, the declaration just has no effect. This compares every `--mat-*` declaration in
 * the stylesheets against the installed @angular/material sources.
 *
 * `--mat-sys-*` (theme system tokens) are defined by the app theme and are skipped.
 *
 * Usage: node tools/check-material-tokens.mjs
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("../src", import.meta.url).pathname;
const MATERIAL = new URL("../node_modules/@angular/material/fesm2022", import.meta.url).pathname;

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) yield* walk(path);
    else if (path.endsWith(".scss") || path.endsWith(".css")) yield path;
  }
}

// A token counts as read when Material uses it in a var() or defines it in its own token sets.
const materialSource = readdirSync(MATERIAL)
  .filter((file) => file.endsWith(".mjs"))
  .map((file) => readFileSync(join(MATERIAL, file), "utf8"))
  .join("\n");

const DECLARATION = /^\s*(--mat-(?!sys-)[a-z0-9-]+)\s*:/gm;
const dead = [];
for (const file of walk(ROOT)) {
  const text = readFileSync(file, "utf8");
  for (const match of text.matchAll(DECLARATION)) {
    if (!materialSource.includes(match[1])) {
      const line = text.slice(0, match.index).split("\n").length + (match[0].startsWith("\n") ? 1 : 0);
      dead.push(`${relative(ROOT, file)}:${line}  ${match[1]}`);
    }
  }
}

if (dead.length) {
  console.error(
    `${dead.length} --mat-* token(s) set but never read by the installed @angular/material:\n${dead.join("\n")}`
  );
  process.exit(1);
}
console.log("All --mat-* tokens set in src are read by @angular/material.");
