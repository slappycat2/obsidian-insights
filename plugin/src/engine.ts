// Running the engine.
//
// The contract this file implements is docs/PLUGIN-CONTRACT.md in the
// engine's repository: `ovi --json` writes one JSON object per line on
// stdout -- progress events, then exactly one done or error event -- and
// keeps its log on stderr. Everything here is Node: it only runs on desktop,
// which manifest.json declares.

import { ChildProcess, spawn } from "child_process";
import { homedir } from "os";
import { delimiter, join } from "path";
import { expandHome } from "./detect";
import type { OviSettings } from "./settings";

/** The first engine version that speaks --json. */
export const MIN_ENGINE_VERSION = "1.4.0";

export interface ProgressEvent {
	event: "progress";
	percent: number;
	text: string;
}

export interface DoneEvent {
	event: "done";
	ok: true;
	workbook: string;
	batch: string;
	vault: string;
	vault_name: string;
	version: string;
	ctot: number[];
	opened: boolean | null;
}

export interface ErrorEvent {
	event: "error";
	ok: false;
	kind: string;
	message: string;
}

type EngineEvent = ProgressEvent | DoneEvent | ErrorEvent | { event: string };

/** Why a run did not end in a done event. `kind` is what the UI switches on. */
export class EngineError extends Error {
	constructor(public kind: string, message: string, public stderr = "") {
		super(message);
		this.name = "EngineError";
	}
}

export interface RunHandle {
	child: ChildProcess;
	result: Promise<DoneEvent>;
}

export function dataDir(settings: OviSettings): string {
	return expandHome(settings.dataDir || "~/.ovi");
}

export function workbooksDir(settings: OviSettings): string {
	return join(dataDir(settings), "data", "workbooks");
}

export function logPath(settings: OviSettings): string {
	return join(dataDir(settings), "logs", "ovi.log");
}

/** The engine's command line for one run of the open vault. */
export function buildArgs(settings: OviSettings, vaultPath: string): string[] {
	const args = ["--json", "--headless", "-d", settings.logLevel];
	if (settings.skipFolders.trim()) args.push("--skip-folders", settings.skipFolders.trim());
	args.push("--max-value-links", String(Math.max(0, Math.trunc(settings.maxValueLinks || 0))));
	args.push("--max-tag-links", String(Math.max(0, Math.trunc(settings.maxTagLinks || 0))));
	// Always passed: a blank value means the system default, and passing it
	// keeps the plugin's setting in charge rather than whatever CONFIG.yaml
	// happens to hold from a command-line setup.
	args.push("--spreadsheet-app", settings.spreadsheetApp.trim());
	if (!settings.openAfterBuild) args.push("--do-not-open");
	args.push(vaultPath);
	return args;
}

/** The environment the engine runs in. */
export function engineEnv(settings: OviSettings, platform = process.platform,
                          base: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
	const env: NodeJS.ProcessEnv = {
		...base,
		OVI_DATA_DIR: dataDir(settings),
		PYTHONIOENCODING: "utf-8",
		PYTHONUTF8: "1",
	};
	if (platform !== "win32") {
		// A GUI-launched Obsidian has a minimal PATH. The engine opens the
		// workbook with `open`, `xdg-open` or a bare command such as
		// `libreoffice`, so the usual places are put in front.
		const extra = [join(homedir(), ".local", "bin"), "/opt/homebrew/bin", "/usr/local/bin"];
		env.PATH = [...extra, base.PATH ?? ""].filter(Boolean).join(delimiter);
	}
	return env;
}

/** Stop the engine and, on Windows, the Python it launched. */
export function killTree(child: ChildProcess, platform = process.platform): void {
	if (!child.pid) return;
	if (platform === "win32") {
		// The uv-installed ovi.exe is a trampoline that runs python as a
		// child; a plain kill() would leave that child scanning.
		spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { windowsHide: true });
	} else {
		child.kill("SIGTERM");
	}
}

/** Split a stream into complete lines, tolerating CRLF and partial chunks. */
export class LineSplitter {
	private pending = "";

	constructor(private readonly onLine: (line: string) => void) {}

	push(chunk: string): void {
		this.pending += chunk;
		let index: number;
		while ((index = this.pending.indexOf("\n")) >= 0) {
			const line = this.pending.slice(0, index).replace(/\r$/, "");
			this.pending = this.pending.slice(index + 1);
			this.onLine(line);
		}
	}

	flush(): void {
		if (this.pending.trim()) this.onLine(this.pending.replace(/\r$/, ""));
		this.pending = "";
	}
}

/** Keep only the last `limit` lines. */
export class TailBuffer {
	private lines: string[] = [];

	constructor(private readonly limit = 200) {}

	push(line: string): void {
		this.lines.push(line);
		if (this.lines.length > this.limit) this.lines.shift();
	}

	text(): string {
		return this.lines.join("\n");
	}
}

/**
 * Spawn the engine on a vault. Progress events are reported as they arrive;
 * the promise resolves with the done event or rejects with an EngineError.
 */
export function runEngine(exe: string, settings: OviSettings, vaultPath: string,
                          onProgress: (percent: number, text: string) => void): RunHandle {
	const args = buildArgs(settings, vaultPath);
	const child = spawn(exe, args, {
		env: engineEnv(settings),
		windowsHide: true,
		stdio: ["ignore", "pipe", "pipe"],
	});

	const stderr = new TailBuffer();
	const stray = new TailBuffer(20);
	let outcome: DoneEvent | ErrorEvent | null = null;
	let timedOut = false;

	const stdoutLines = new LineSplitter((line) => {
		if (!line.trim()) return;
		let event: EngineEvent;
		try {
			event = JSON.parse(line) as EngineEvent;
		} catch {
			stray.push(line);
			return;
		}
		if (event.event === "progress") {
			const p = event as ProgressEvent;
			onProgress(p.percent, p.text);
		} else if (event.event === "done" || event.event === "error") {
			outcome = event as DoneEvent | ErrorEvent;
		}
		// Anything else is a newer engine's business; ignored on purpose.
	});
	const stderrLines = new LineSplitter((line) => stderr.push(line));

	child.stdout?.setEncoding("utf8");
	child.stdout?.on("data", (chunk: string) => stdoutLines.push(chunk));
	child.stderr?.setEncoding("utf8");
	child.stderr?.on("data", (chunk: string) => stderrLines.push(chunk));

	const result = new Promise<DoneEvent>((resolve, reject) => {
		const timer = setTimeout(() => {
			timedOut = true;
			killTree(child);
		}, Math.max(1, settings.timeoutSeconds) * 1000);

		child.on("error", (err: NodeJS.ErrnoException) => {
			clearTimeout(timer);
			const reason = err.code === "ENOENT"
				? `The engine was not found at ${exe}.`
				: `The engine could not be started: ${err.message}`;
			reject(new EngineError("NotFound", reason));
		});

		child.on("close", (code) => {
			clearTimeout(timer);
			stdoutLines.flush();
			stderrLines.flush();
			const tail = [stderr.text(), stray.text()].filter(Boolean).join("\n");

			if (timedOut) {
				reject(new EngineError("Timeout",
					`The engine was stopped after ${settings.timeoutSeconds} seconds. ` +
					"Raise the timeout in the plugin settings if the vault is very large.", tail));
			} else if (outcome && outcome.event === "done") {
				resolve(outcome);
			} else if (outcome && outcome.event === "error") {
				reject(new EngineError(outcome.kind, outcome.message, tail));
			} else if (code === 2) {
				reject(new EngineError("Usage",
					"The engine rejected the command line -- see what it reported. If it predates " +
					`this plugin (older than ${MIN_ENGINE_VERSION}), upgrade it with: uv tool upgrade obsidian-insights`, tail));
			} else {
				reject(new EngineError("Exit",
					`The engine exited with code ${code} without reporting a result.`, tail));
			}
		});
	});

	return { child, result };
}

/** `ovi --version` -> "1.4.0". Rejects when the command cannot run or prints something else. */
export function probeVersion(exe: string): Promise<string> {
	return new Promise((resolve, reject) => {
		let output = "";
		let child: ChildProcess;
		try {
			child = spawn(exe, ["--version"], { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
		} catch (err) {
			reject(new EngineError("NotFound", `The engine could not be started: ${(err as Error).message}`));
			return;
		}
		child.stdout?.setEncoding("utf8");
		child.stdout?.on("data", (chunk: string) => { output += chunk; });
		child.stderr?.setEncoding("utf8");
		child.stderr?.on("data", (chunk: string) => { output += chunk; });
		child.on("error", (err: NodeJS.ErrnoException) => {
			reject(new EngineError("NotFound", err.code === "ENOENT"
				? `The engine was not found at ${exe}.`
				: `The engine could not be started: ${err.message}`));
		});
		child.on("close", () => {
			const version = parseVersion(output);
			if (version) resolve(version);
			else reject(new EngineError("NotEngine",
				`${exe} did not answer --version like the Obsidian Insights engine. It printed: ${output.trim() || "(nothing)"}`));
		});
	});
}

export function parseVersion(text: string): string | null {
	const match = /version (\d+\.\d+\.\d+)/.exec(text);
	return match ? match[1] : null;
}

/** Negative when a < b, zero when equal, positive when a > b. Numeric, dotted. */
export function compareVersions(a: string, b: string): number {
	const pa = a.split(".").map(Number);
	const pb = b.split(".").map(Number);
	for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
		const d = (pa[i] ?? 0) - (pb[i] ?? 0);
		if (d !== 0) return d;
	}
	return 0;
}
