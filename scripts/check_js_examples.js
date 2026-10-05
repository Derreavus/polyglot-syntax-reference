#!/usr/bin/env node
/*
 * Optional check for the JavaScript version data (not part of CI, because it needs a package install):
 *
 *   npm install --no-save acorn
 *   node scripts/check_js_examples.js
 *
 * For every JavaScript feature with a before/after example it verifies that
 *   - both snippets parse as current JavaScript,
 *   - for syntax features, the newer snippet parses in the edition that added the feature
 *     and does NOT parse in the edition before it,
 *   - snippets for removals that only apply in strict mode parse in sloppy mode, and fail to parse in
 *     strict mode when the data describes the restriction as a SyntaxError (a run-time TypeError cannot be
 *     detected by parsing).
 * Library features (new functions and methods) cannot be checked by parsing, so only the first rule applies.
 *
 * It also parses every code block in the JavaScript reference topics, as module code, so a typo in a
 * published example is caught before it ships.
 */
const fs = require("fs");
const path = require("path");
const acorn = require("acorn");

const data = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "site_data.json"), "utf8"));
const ECMA = { es3: 3, es5: 5 };
for (let year = 2015; year <= 2027; year += 1) ECMA["es" + year] = year;
const NOT_PARSEABLE = new Set(["explicit-resource-management"]); // acorn has no support for `using` yet
const MODULE_ONLY = new Set(["top-level-await", "export-star-as"]);
const NON_JS_TOPICS = new Set(["ecosystem"]); // its code block is a package.json file

function parses(code, ecmaVersion, sourceType, strict) {
  try {
    acorn.parse(strict ? '"use strict";\n' + code : code, { ecmaVersion, sourceType });
    return true;
  } catch (error) {
    return error.message;
  }
}

let problems = 0;
let checked = 0;
const report = (message) => { problems += 1; console.log("PROBLEM: " + message); };

for (const feature of data.features.filter((f) => f.language === "javascript" && f.migration && f.history.ecmascript)) {
  if (NOT_PARSEABLE.has(feature.slug)) { console.log("skipped (parser limitation): " + feature.slug); continue; }
  const sourceType = MODULE_ONLY.has(feature.slug) ? "module" : "script";
  const edition = ECMA[feature.history.ecmascript[0].version];
  const scopedRemoval = feature.history.ecmascript.some((e) => e.kind === "removed" && e.scope);
  // Only removals described as a SyntaxError can be checked by parsing; a TypeError happens at run time.
  const syntaxErrorInStrict = feature.history.ecmascript.some((e) => e.kind === "removed" && e.scope && /SyntaxError/.test(e.note || ""));
  checked += 1;

  if (scopedRemoval) {
    const sloppy = parses(feature.migration.legacy, 5, sourceType, false);
    const strict = parses(feature.migration.legacy, 5, sourceType, true);
    if (sloppy !== true) report(`${feature.slug}: older code should parse in sloppy mode (${sloppy})`);
    if (syntaxErrorInStrict && strict === true) report(`${feature.slug}: older code should be rejected in strict mode`);
  } else {
    const legacy = parses(feature.migration.legacy, "latest", sourceType, false);
    if (legacy !== true) report(`${feature.slug}: older code does not parse (${legacy})`);
  }
  const modern = parses(feature.migration.modern, "latest", sourceType, false);
  if (modern !== true) report(`${feature.slug}: newer code does not parse (${modern})`);

  if (feature.category === "syntax" && edition >= 2015) {
    const before = edition === 2015 ? 5 : edition - 1;
    const atEdition = parses(feature.migration.modern, edition, sourceType, false);
    if (atEdition !== true) report(`${feature.slug}: newer code should parse in ES${edition} (${atEdition})`);
    if (parses(feature.migration.modern, before, sourceType, false) === true) {
      report(`${feature.slug}: newer code already parses in ES${before}, so the feature was not new in ES${edition}`);
    }
  }
}
// ---- Node.js-only features: their before/after snippets must be valid JavaScript (as a script or a module)
let nodeOnly = 0;
for (const feature of data.features.filter((f) => f.language === "javascript" && f.migration && !f.history.ecmascript)) {
  nodeOnly += 1;
  for (const key of ["legacy", "modern"]) {
    const asScript = parses(feature.migration[key], "latest", "script", false);
    const asModule = asScript === true ? true : parses(feature.migration[key], "latest", "module", false);
    // acorn does not parse the removed `assert { type }` import syntax
    if (asModule !== true && feature.slug !== "import-assertions") report(`${feature.slug}: ${key} code does not parse (${asModule})`);
  }
}

// ---- Reference topics: every code block must parse as current JavaScript (module code allows top-level await)
const unescape = (text) =>
  text.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, "&");
let blocks = 0;
for (const topic of data.topics.filter((t) => t.language === "javascript" && !NON_JS_TOPICS.has(t.slug))) {
  const found = topic.content_html.match(/<pre><code>[\s\S]*?<\/code><\/pre>/g) || [];
  for (const block of found) {
    blocks += 1;
    const source = unescape(block.replace(/^<pre><code>/, "").replace(/<\/code><\/pre>$/, ""));
    const result = parses(source, "latest", "module", false);
    if (result !== true) report(`topic ${topic.slug}: code block does not parse (${result})`);
  }
}

console.log(`Checked ${checked} ECMAScript examples, ${nodeOnly} Node.js-only examples and ${blocks} reference code blocks, ${problems} problem(s).`);
process.exit(problems ? 1 : 0);
