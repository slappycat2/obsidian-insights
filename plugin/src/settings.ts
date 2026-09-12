import { App, Notice, PluginSettingTab, Setting, TFolder } from "obsidian";
import type OviPlugin from "./main";
import { INSTALL_HINT, detectEngine } from "./detect";
import { MIN_ENGINE_VERSION, compareVersions, probeVersion } from "./engine";

export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR";

export interface OviSettings {
	/** Path to the ovi command. Blank: search the usual places. */
	enginePath: string;
	/** Where CONFIG.yaml, workbooks, batch files and logs go. ~ is the home folder. */
	dataDir: string;
	/** Folder names to leave out of the scan, comma-separated. */
	skipFolders: string;
	/** Most FileNN link columns on the Values tab; 0 = unlimited. */
	maxValueLinks: number;
	/** Most FileNN link columns on the Tags tab; 0 = unlimited. */
	maxTagLinks: number;
	/** Launch the spreadsheet application when the workbook is written. */
	openAfterBuild: boolean;
	/** Program to open the workbook with. Blank: the system default for .xlsx. */
	spreadsheetApp: string;
	/** The engine's log level (its log file; stderr stays at WARNING). */
	logLevel: LogLevel;
	/** Stop a run that takes longer than this. */
	timeoutSeconds: number;
	/** The workbook the last successful run wrote. */
	lastWorkbook: string;
}

export const DEFAULT_SETTINGS: OviSettings = {
	enginePath: "",
	dataDir: "~/.ovi",
	skipFolders: "",
	maxValueLinks: 0,
	maxTagLinks: 0,
	openAfterBuild: true,
	spreadsheetApp: "",
	logLevel: "INFO",
	timeoutSeconds: 600,
	lastWorkbook: "",
};

const LOG_LEVELS: LogLevel[] = ["DEBUG", "INFO", "WARNING", "ERROR"];

export class OviSettingTab extends PluginSettingTab {
	constructor(app: App, private readonly plugin: OviPlugin) {
		super(app, plugin);
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();
		containerEl.addClass("ovi-settings");

		this.engineSection(containerEl);
		this.scanSection(containerEl);
		this.workbookSection(containerEl);
		this.advancedSection(containerEl);
	}

	private async save(): Promise<void> {
		await this.plugin.saveSettings();
	}

	// -- Engine -------------------------------------------------------------

	private engineSection(containerEl: HTMLElement): void {
		new Setting(containerEl).setName("Engine").setHeading();

		const status = createDiv();
		const setStatus = (text: string, ok: boolean) => {
			status.setText(text);
			status.className = ok ? "ovi-ok" : "ovi-warning";
		};

		const setting = new Setting(containerEl)
			.setName("Engine executable")
			.setDesc("The ovi command. Leave blank to look in the places uv tool install uses, "
				+ "or give the full path. " + INSTALL_HINT)
			.addText((text) => {
				text.setPlaceholder("(search the usual places)")
					.setValue(this.plugin.settings.enginePath)
					.onChange(async (value) => {
						this.plugin.settings.enginePath = value;
						this.plugin.forgetEngineCheck();
						await this.save();
					});
				text.inputEl.addClass("ovi-wide");
				text.inputEl.spellcheck = false;
			})
			.addButton((button) => button
				.setButtonText("Detect")
				.setTooltip("Search the usual places and fill in the path")
				.onClick(async () => {
					const found = detectEngine("");
					if (!found) {
						setStatus("Not found in the usual places. " + INSTALL_HINT, false);
						return;
					}
					this.plugin.settings.enginePath = found;
					this.plugin.forgetEngineCheck();
					await this.save();
					setStatus(`Found ${found}`, true);
					this.display();
				}))
			.addButton((button) => button
				.setButtonText("Test")
				.setTooltip("Run the engine's --version")
				.onClick(async () => {
					const exe = detectEngine(this.plugin.settings.enginePath);
					if (!exe) {
						setStatus("No engine found. " + INSTALL_HINT, false);
						return;
					}
					try {
						const version = await probeVersion(exe);
						if (compareVersions(version, MIN_ENGINE_VERSION) < 0) {
							setStatus(`Engine ${version} at ${exe} is older than ${MIN_ENGINE_VERSION}; `
								+ "upgrade it with: uv tool upgrade obsidian-insights", false);
						} else {
							setStatus(`Engine ${version} at ${exe}`, true);
						}
					} catch (err) {
						setStatus((err as Error).message, false);
					}
				}));
		setting.settingEl.after(status);

		const current = detectEngine(this.plugin.settings.enginePath);
		if (current) setStatus(`Using ${current}`, true);
		else setStatus("No engine found yet. Press Detect after installing it. " + INSTALL_HINT, false);

		new Setting(containerEl)
			.setName("Data folder")
			.setDesc("Where the engine keeps its configuration, the workbooks it writes, the batch "
				+ "files beside them and its log. ~ is your home folder. Never inside the vault.")
			.addText((text) => {
				text.setPlaceholder(DEFAULT_SETTINGS.dataDir)
					.setValue(this.plugin.settings.dataDir)
					.onChange(async (value) => {
						this.plugin.settings.dataDir = value.trim() || DEFAULT_SETTINGS.dataDir;
						await this.save();
					});
				text.inputEl.addClass("ovi-wide");
				text.inputEl.spellcheck = false;
			});
	}

	// -- Scan ---------------------------------------------------------------

	private scanSection(containerEl: HTMLElement): void {
		new Setting(containerEl).setName("Scan").setHeading();

		const warning = createDiv({ cls: "ovi-warning" });
		const checkFolders = (value: string) => {
			const names = value.split(",").map((s) => s.trim()).filter(Boolean);
			const missing = names.filter((name) => !this.folderExists(name));
			warning.setText(missing.length
				? `No folder named ${missing.map((m) => `'${m}'`).join(", ")} at the top of this vault. `
				+ "It will simply not match."
				: "");
		};

		const skip = new Setting(containerEl)
			.setName("Folders to ignore")
			.setDesc("Folder names to leave out of the scan, comma-separated -- the setup screen's "
				+ "\"Directories to Ignore\".")
			.addText((text) => {
				text.setPlaceholder("Archive, Templates")
					.setValue(this.plugin.settings.skipFolders)
					.onChange(async (value) => {
						this.plugin.settings.skipFolders = value;
						checkFolders(value);
						await this.save();
					});
				text.inputEl.addClass("ovi-wide");
			});
		skip.settingEl.after(warning);
		checkFolders(this.plugin.settings.skipFolders);

		this.numberSetting(containerEl, "Values tab: most link columns",
			"How many FileNN columns the Values tab may have. 0 means as many as the vault needs.",
			() => this.plugin.settings.maxValueLinks,
			(n) => { this.plugin.settings.maxValueLinks = n; });
		this.numberSetting(containerEl, "Tags tab: most link columns",
			"The same for the Tags tab.",
			() => this.plugin.settings.maxTagLinks,
			(n) => { this.plugin.settings.maxTagLinks = n; });
	}

	// -- Workbook -----------------------------------------------------------

	private workbookSection(containerEl: HTMLElement): void {
		new Setting(containerEl).setName("Workbook").setHeading();

		new Setting(containerEl)
			.setName("Open the workbook after building")
			.setDesc("Off: the workbook is written and left where it is. "
				+ "The \"Open last workbook\" command opens it later.")
			.addToggle((toggle) => toggle
				.setValue(this.plugin.settings.openAfterBuild)
				.onChange(async (value) => {
					this.plugin.settings.openAfterBuild = value;
					await this.save();
				}));

		new Setting(containerEl)
			.setName("Spreadsheet application")
			.setDesc("The program to open the workbook with. Blank means whatever this computer opens "
				+ ".xlsx files with. On macOS give the application bundle "
				+ "(/Applications/Numbers.app); on Linux a command such as libreoffice also works.")
			.addText((text) => {
				text.setPlaceholder("(system default)")
					.setValue(this.plugin.settings.spreadsheetApp)
					.onChange(async (value) => {
						this.plugin.settings.spreadsheetApp = value;
						await this.save();
					});
				text.inputEl.addClass("ovi-wide");
				text.inputEl.spellcheck = false;
			});
	}

	// -- Advanced -----------------------------------------------------------

	private advancedSection(containerEl: HTMLElement): void {
		new Setting(containerEl).setName("Advanced").setHeading();

		new Setting(containerEl)
			.setName("Engine log level")
			.setDesc("How much the engine writes to its log file (logs/ovi.log under the data folder).")
			.addDropdown((dropdown) => {
				for (const level of LOG_LEVELS) dropdown.addOption(level, level);
				dropdown.setValue(this.plugin.settings.logLevel)
					.onChange(async (value) => {
						this.plugin.settings.logLevel = value as LogLevel;
						await this.save();
					});
			});

		this.numberSetting(containerEl, "Timeout (seconds)",
			"Stop a run that takes longer than this. A large vault on a slow disk may need more.",
			() => this.plugin.settings.timeoutSeconds,
			(n) => { this.plugin.settings.timeoutSeconds = n || DEFAULT_SETTINGS.timeoutSeconds; },
			1);
	}

	// -- helpers ------------------------------------------------------------

	private numberSetting(containerEl: HTMLElement, name: string, desc: string,
	                      get: () => number, set: (n: number) => void, min = 0): void {
		new Setting(containerEl)
			.setName(name)
			.setDesc(desc)
			.addText((text) => {
				text.inputEl.type = "number";
				text.inputEl.min = String(min);
				text.inputEl.step = "1";
				text.setValue(String(get()))
					.onChange(async (value) => {
						const n = Math.trunc(Number(value));
						if (Number.isNaN(n) || n < min) {
							new Notice(`${name}: enter a whole number of ${min} or more.`);
							return;
						}
						set(n);
						await this.save();
					});
			});
	}

	private folderExists(name: string): boolean {
		return this.app.vault.getAbstractFileByPath(name) instanceof TFolder;
	}
}
