import { App, FileSystemAdapter, Modal, Notice, Plugin } from "obsidian";
import { existsSync } from "fs";
import { basename } from "path";
import { INSTALL_HINT, detectEngine } from "./detect";
import {
	EngineError, MIN_ENGINE_VERSION, RunHandle, compareVersions, killTree, logPath,
	probeVersion, runEngine, workbooksDir,
} from "./engine";
import { DEFAULT_SETTINGS, OviSettingTab, OviSettings } from "./settings";

// Electron's shell is the cross-platform "open this with whatever handles it".
// It is an external in the bundle; the desktop-only manifest guarantees it.
const electron = require("electron") as { shell: { openPath(path: string): Promise<string> } };

export default class OviPlugin extends Plugin {
	settings: OviSettings = { ...DEFAULT_SETTINGS };
	private running: RunHandle | null = null;
	private engineChecked = false;

	async onload(): Promise<void> {
		await this.loadSettings();
		this.addSettingTab(new OviSettingTab(this.app, this));

		this.addRibbonIcon("table", "Build Obsidian Insights workbook", () => {
			void this.build();
		});

		this.addCommand({
			id: "build-workbook",
			name: "Build workbook for this vault",
			checkCallback: (checking) => {
				if (this.running) return false;
				if (!checking) void this.build();
				return true;
			},
		});

		this.addCommand({
			id: "open-last-workbook",
			name: "Open last workbook",
			checkCallback: (checking) => {
				const last = this.settings.lastWorkbook;
				if (!last || !existsSync(last)) return false;
				if (!checking) void this.openPath(last);
				return true;
			},
		});

		this.addCommand({
			id: "open-output-folder",
			name: "Open output folder",
			callback: () => {
				const dir = workbooksDir(this.settings);
				if (!existsSync(dir)) {
					new Notice("No workbook has been built yet, so the output folder does not exist.");
					return;
				}
				void this.openPath(dir);
			},
		});
	}

	onunload(): void {
		if (this.running) killTree(this.running.child);
	}

	async loadSettings(): Promise<void> {
		this.settings = { ...DEFAULT_SETTINGS, ...((await this.loadData()) as Partial<OviSettings> | null) };
	}

	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);
	}

	/** The settings tab calls this when the engine path changes. */
	forgetEngineCheck(): void {
		this.engineChecked = false;
	}

	private vaultPath(): string | null {
		const adapter = this.app.vault.adapter;
		return adapter instanceof FileSystemAdapter ? adapter.getBasePath() : null;
	}

	private async openPath(path: string): Promise<void> {
		const problem = await electron.shell.openPath(path);
		if (problem) new Notice(`Could not open ${path}: ${problem}`);
	}

	async build(): Promise<void> {
		if (this.running) {
			new Notice("Obsidian Insights is already building a workbook.");
			return;
		}
		const vaultPath = this.vaultPath();
		if (!vaultPath) {
			new Notice("Obsidian Insights needs a vault on this computer's file system.");
			return;
		}
		const exe = detectEngine(this.settings.enginePath);
		if (!exe) {
			this.showError(new EngineError("NotFound",
				"The Obsidian Insights engine (ovi) was not found. Set its path in the plugin "
				+ "settings, or press Detect there after installing it."));
			return;
		}

		if (!this.engineChecked) {
			try {
				const version = await probeVersion(exe);
				if (compareVersions(version, MIN_ENGINE_VERSION) < 0) {
					new Notice(`Obsidian Insights engine ${version} is older than ${MIN_ENGINE_VERSION}. `
						+ "Upgrade it with: uv tool upgrade obsidian-insights", 12000);
				}
				this.engineChecked = true;
			} catch (err) {
				this.showError(err as Error);
				return;
			}
		}

		const notice = new Notice("Obsidian Insights: starting the engine...", 0);
		const handle = runEngine(exe, this.settings, vaultPath, (percent, text) => {
			notice.setMessage(`Obsidian Insights ${percent}%: ${text}`);
		});
		this.running = handle;

		try {
			const done = await handle.result;
			this.settings.lastWorkbook = done.workbook;
			await this.saveSettings();
			notice.hide();
			const outcome = done.opened === null ? ""
				: done.opened ? ", and opened"
				: ", but it could not be opened (the engine log says why)";
			new Notice(`Workbook written${outcome}: ${basename(done.workbook)}`, 8000);
		} catch (err) {
			notice.hide();
			this.showError(err as Error);
		} finally {
			this.running = null;
		}
	}

	private showError(err: Error): void {
		const engineErr = err instanceof EngineError ? err : new EngineError("Unexpected", err.message);
		new Notice(`Obsidian Insights: ${engineErr.message.split("\n")[0]}`, 8000);
		new ErrorModal(this.app, engineErr, logPath(this.settings)).open();
	}
}

const HINTS: Record<string, string> = {
	WorkbookLocked: "Close the previous workbook in your spreadsheet application and build again. "
		+ "The number is not reused; the next build writes the next one.",
	NotFound: INSTALL_HINT + " -- then press Detect in the plugin settings. If it is installed "
		+ "somewhere else, give the full path there.",
	NotEngine: "The path in the plugin settings does not point at the Obsidian Insights engine.",
	Usage: "The installed engine may predate this plugin. Upgrade it with: uv tool upgrade obsidian-insights",
	Timeout: "Raise the timeout in the plugin settings, or add large folders that do not need "
		+ "scanning to \"Folders to ignore\".",
	ConfigIncomplete: "The engine could not complete its configuration. The message above says what "
		+ "was wrong; the spreadsheet application path is the usual cause.",
};

class ErrorModal extends Modal {
	constructor(app: App, private readonly error: EngineError, private readonly log: string) {
		super(app);
	}

	onOpen(): void {
		const { contentEl } = this;
		contentEl.addClass("ovi-error-modal");
		contentEl.createEl("h2", { text: "Obsidian Insights could not build the workbook" });
		contentEl.createDiv({ cls: "ovi-kind", text: this.error.kind });
		contentEl.createEl("p", { cls: "ovi-message", text: this.error.message });

		const hint = HINTS[this.error.kind];
		if (hint) contentEl.createEl("p", { cls: "ovi-hint", text: hint });

		if (this.error.stderr) {
			contentEl.createEl("p", { text: "What the engine reported:" });
			contentEl.createEl("pre", { text: this.error.stderr });
		}
		contentEl.createDiv({ cls: "ovi-log-path", text: `Engine log: ${this.log}` });

		const buttons = contentEl.createDiv({ cls: "ovi-buttons" });
		buttons.createEl("button", { text: "Copy details" }).addEventListener("click", () => {
			const details = [
				`kind: ${this.error.kind}`, this.error.message, "",
				this.error.stderr, "", `log: ${this.log}`,
			].join("\n");
			void navigator.clipboard.writeText(details).then(() => new Notice("Copied."));
		});
		const close = buttons.createEl("button", { text: "Close", cls: "mod-cta" });
		close.addEventListener("click", () => this.close());
	}

	onClose(): void {
		this.contentEl.empty();
	}
}
