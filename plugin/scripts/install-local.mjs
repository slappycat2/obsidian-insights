// Copy the built plugin into a vault: npm run install-local -- "<vault path>"
//
// Puts main.js, manifest.json and styles.css under
// <vault>/.obsidian/plugins/obsidian-insights/. Build first (npm run build);
// then enable the plugin under Settings -> Community plugins. Windows needs
// this rather than a symlink, which wants developer mode.

import { copyFileSync, existsSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import process from "process";

const vault = process.argv[2];
if (!vault) {
	console.error('usage: npm run install-local -- "<vault path>"');
	process.exit(2);
}
if (!existsSync(join(vault, ".obsidian"))) {
	console.error(`${vault} has no .obsidian folder; is it a vault?`);
	process.exit(1);
}
if (!existsSync("main.js")) {
	console.error("main.js is not built yet; run: npm run build");
	process.exit(1);
}

const target = resolve(vault, ".obsidian", "plugins", "obsidian-insights");
mkdirSync(target, { recursive: true });
for (const name of ["main.js", "manifest.json", "styles.css"]) {
	copyFileSync(name, join(target, name));
}
console.log(`Installed into ${target}. Reload Obsidian, or toggle the plugin off and on.`);
