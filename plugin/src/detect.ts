// Finding the engine.
//
// Obsidian launched from the Dock, the Start menu or a desktop launcher does
// not inherit the shell's PATH -- on macOS and Linux it is often little more
// than /usr/bin. So the places `uv tool install` puts the command are tried
// by name first, and PATH last.

import { existsSync } from "fs";
import { homedir } from "os";
import { delimiter, join } from "path";

export const INSTALL_HINT =
	"Install the engine with: uv tool install git+https://github.com/slappycat2/obsidian-insights";

/** Expand a leading ~ to the home folder; leave anything else alone. */
export function expandHome(p: string): string {
	const trimmed = p.trim();
	if (trimmed === "~") return homedir();
	if (trimmed.startsWith("~/") || trimmed.startsWith("~\\")) {
		return join(homedir(), trimmed.slice(2));
	}
	return trimmed;
}

/** Every path worth checking, most likely first. The configured one wins. */
export function candidateExecutables(configured: string, platform = process.platform,
                                     env: NodeJS.ProcessEnv = process.env): string[] {
	const home = homedir();
	const list: string[] = [];
	if (configured.trim()) list.push(expandHome(configured));

	if (platform === "win32") {
		list.push(join(home, ".local", "bin", "ovi.exe"));
		if (env.APPDATA) {
			list.push(join(env.APPDATA, "uv", "tools", "obsidian-insights", "Scripts", "ovi.exe"));
		}
	} else {
		list.push(
			join(home, ".local", "bin", "ovi"),
			join(home, ".local", "share", "uv", "tools", "obsidian-insights", "bin", "ovi"),
			"/opt/homebrew/bin/ovi",
			"/usr/local/bin/ovi",
		);
	}

	const exe = platform === "win32" ? "ovi.exe" : "ovi";
	for (const dir of (env.PATH ?? "").split(delimiter)) {
		if (dir) list.push(join(dir, exe));
	}
	return list;
}

/** The first candidate that exists, or null. */
export function detectEngine(configured: string): string | null {
	for (const candidate of candidateExecutables(configured)) {
		if (existsSync(candidate)) return candidate;
	}
	return null;
}
