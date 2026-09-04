import tkinter as tk
from tkinter import ttk, PhotoImage

from ovi import __version__
from ovi.ovi_logger import logger

SPLASH_Test = False

class SplashScreen(tk.Tk):

    # noinspection DuplicatedCode
    def __init__(self, logo_path, splash_bg='#800000', title="Obsidian Insights", version=f"v{__version__}"):
        super().__init__()
        self.logo_path = logo_path
        # Not ``self.title``: that is Tk's own method, and assigning a str over
        # it turns every later ``self.title(...)`` into a TypeError.
        self.app_title = title
        self.version = version
        self.overrideredirect(True) # Remove window decorations for splash effect
        self.configure(bg=splash_bg)
        self.logo_img = PhotoImage(file=self.logo_path, master=self)
        # noinspection PyTypeChecker
        self.logo_label = tk.Label(self, image=self.logo_img, bg=splash_bg)
        self.logo_label.pack(expand=True)

        # Title and version
        title_label = tk.Label(self, text=self.app_title,
                               font=('Arial', 16, 'bold'),
                               fg='white', bg=splash_bg)
        title_label.pack(pady=(10, 5))

        version_label = tk.Label(self, text=self.version,
                                 font=('Arial', 10),
                                 fg='white', bg=splash_bg)
        version_label.pack()

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self, textvariable=self.status_var, anchor="sw",
                                     bg=splash_bg, fg="white", font=("Arial", 9))
        self.status_label.pack(side="bottom", anchor="sw", padx=10, pady=10, fill="x")

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=300)
        self.progress.pack(side="bottom", pady=10)
        self.progress["value"] = 0
        self.progress["maximum"] = 100

        self.center_window(400, 330)
        # An override-redirect window is unmanaged by the window manager. On
        # macOS it can come up blank until something forces a paint, and on
        # any platform it may sit under the launching terminal, so raise it
        # and process pending events once before the pipeline starts.
        self.attributes('-topmost', True)
        self.lift()
        self.update()

    def center_window(self, w, h):
        self.update_idletasks()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def update_status(self, text, progress_value=None):
        logger.debug(f"\n\n===================================================================\n{text}")
        self.status_var.set(text)
        if progress_value is not None:
            self.progress["value"] = progress_value
        self.update_idletasks()

def main():
    pass

if __name__ == "__main__":
    main()