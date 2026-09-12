// The plugin's version is stated in three files that Obsidian and npm each
// read; CI runs this so they cannot drift. Exit 1 with the mismatch named.

import { readFileSync } from "fs";

const read = (name) => JSON.parse(readFileSync(name, "utf8"));
const manifest = read("manifest.json");
const pkg = read("package.json");
const versions = read("versions.json");

const problems = [];
if (pkg.version !== manifest.version) {
	problems.push(`package.json says ${pkg.version}, manifest.json says ${manifest.version}`);
}
if (versions[manifest.version] !== manifest.minAppVersion) {
	problems.push(`versions.json has no entry mapping ${manifest.version} to minAppVersion ${manifest.minAppVersion}`);
}
if (!manifest.isDesktopOnly) {
	problems.push("manifest.json must declare isDesktopOnly: the plugin spawns a process");
}

if (problems.length) {
	for (const p of problems) console.error(p);
	process.exit(1);
}
console.log(`plugin ${manifest.version} (min app ${manifest.minAppVersion}): versions agree`);
