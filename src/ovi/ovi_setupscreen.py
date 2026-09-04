import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, PhotoImage
from PIL import ImageTk
from datetime import datetime
import subprocess

from ovi.ovi_logger import logger

class SetupScreen:
    def __init__(self, sys_obj):
        self.sys_obj = sys_obj
        self.sys_cfg = self.sys_obj.sys_cfg
        self.logo = self.sys_obj.sys_pn_lg2
        self.icon = self.sys_obj.sys_pn_ico

        self.c_vlts  = self.sys_obj.cur_vlts  # make pointer, for easier reference
        self.v_list  = list(self.c_vlts.keys())
        self.last_vault_name   = self.sys_obj.vault_name

        self.root = tk.Tk()
        self.root.title("Obsidian Insights")

        self.root.geometry("780x620")
        self.root.resizable(True, False)
        self.root.attributes('-topmost', 1)
        self.root.iconbitmap(self.icon)
        self.frame_image = PhotoImage(file=self.logo, master=self.root)

        # Tkinter variables
        self.vault_name_var        = tk.StringVar(value=self.sys_obj.vault_name)
        self.dir_vault_var         = tk.StringVar(value=self.sys_obj.dir_vault)
        self.sys_pn_wb_exec_var    = tk.StringVar(value=self.sys_obj.sys_pn_wb_exec)
        self.skip_rel_str_var      = tk.StringVar(value=self.sys_obj.skip_rel_str)
        self.bool_shw_notes_var    = tk.BooleanVar(value=self.sys_obj.bool_shw_notes)
        self.bool_rel_paths_var    = tk.BooleanVar(value=self.sys_obj.bool_rel_paths)
        self.bool_summ_rows_var    = tk.BooleanVar(value=self.sys_obj.bool_summ_rows)
        self.bool_unused_1_var     = tk.BooleanVar(value=self.sys_obj.bool_unused_1)
        self.bool_unused_2_var     = tk.BooleanVar(value=self.sys_obj.bool_unused_2)
        self.bool_unused_3_var     = tk.BooleanVar(value=self.sys_obj.bool_unused_3)
        self.link_lim_vals_var     = tk.StringVar(value=str(self.sys_obj.link_lim_vals))
        self.link_lim_tags_var     = tk.StringVar(value=str(self.sys_obj.link_lim_tags))

        # self.vault_name_status = None
        self.combx_vault_name = None
        self.dir_vault_status = None
        self.vault_warn_label = None
        self.wb_exec_status = None
        self.skip_rel_str_status = None
        self.skip_rel_str_valid = None
        self.skip_rel_str_msg = 'X'
        self.link_lim_vals_label = None
        self.link_lim_tags_label = None
        self.link_lim_vals_help = None
        self.link_lim_tags_help = None
        self.save_button = None
        # Whether the user committed. show() returns this, so a caller can tell
        # "Save & Run" apart from Cancel or closing the window -- previously it
        # could not, and carried on building a workbook either way.
        self.saved = False
        self.wb_col_max = 16300
        self.wb_col_help = f"0=Unlimited"
        # The screen's colour vocabulary is red and green, and red means "Save
        # is disabled". A missing .obsidian folder must not say that, so it
        # needs a third colour of its own.
        self.warn_clr = "#B36B00"
        logger.debug(f"setupscreen - {self.vault_name_var.get().strip()}")

    # End of __init__ ==========================================================================================
    def upd_all_sys_objs_with_tk_vars(self, vk: str) -> None:
        """
        Get "_vars" values from tkinter variables and store in sys_obj and cur_vaults
        :param vk:
        :return: None
        """
        logger.debug(f"setupscreen-upd_all<-tk_vars - {self.vault_name_var.get().strip()}")

        self.c_vlts[vk]['skip_rel_str']      = self.sys_obj.skip_rel_str      = self.skip_rel_str_var.get().strip()
        self.c_vlts[vk]['bool_shw_notes']    = self.sys_obj.bool_shw_notes    = self.bool_shw_notes_var.get()
        self.c_vlts[vk]['bool_rel_paths']    = self.sys_obj.bool_rel_paths    = self.bool_rel_paths_var.get()
        self.c_vlts[vk]['bool_summ_rows']    = self.sys_obj.bool_summ_rows    = self.bool_summ_rows_var.get()
        self.c_vlts[vk]['bool_unused_1']     = self.sys_obj.bool_unused_1     = self.bool_unused_1_var.get()
        self.c_vlts[vk]['bool_unused_2']     = self.sys_obj.bool_unused_2     = self.bool_unused_2_var.get()
        self.c_vlts[vk]['bool_unused_3']     = self.sys_obj.bool_unused_3     = self.bool_unused_3_var.get()
        self.c_vlts[vk]['link_lim_vals']     = self.sys_obj.link_lim_vals     = int(self.link_lim_vals_var.get())
        self.c_vlts[vk]['link_lim_tags']     = self.sys_obj.link_lim_tags     = int(self.link_lim_tags_var.get())

        self.sys_obj.sys_pn_wb_exec     = self.sys_pn_wb_exec_var.get().strip()
        self.sys_obj.vault_id           = self.c_vlts[vk]['vault_id']
        self.sys_obj.dir_vault          = self.c_vlts[vk]['dir_vault']

    def upd_sys_objs_with_vaults(self, vk: str) -> None:
        """
        Update sys_obj with vaults.
        :param vk:
        :return:
        """
        self.sys_obj.vault_id           = self.c_vlts[vk]['vault_id']
        self.sys_obj.dir_vault          = self.c_vlts[vk]['dir_vault']

        self.sys_obj.vault_name         = self.c_vlts[vk]['vault_name']
        self.sys_obj.skip_rel_str       = self.c_vlts[vk]['skip_rel_str']
        self.sys_obj.bool_shw_notes     = self.c_vlts[vk]['bool_shw_notes']
        self.sys_obj.bool_rel_paths     = self.c_vlts[vk]['bool_rel_paths']
        self.sys_obj.bool_summ_rows     = self.c_vlts[vk]['bool_summ_rows']
        self.sys_obj.bool_unused_1      = self.c_vlts[vk]['bool_unused_1']
        self.sys_obj.bool_unused_2      = self.c_vlts[vk]['bool_unused_2']
        self.sys_obj.bool_unused_3      = self.c_vlts[vk]['bool_unused_3']
        self.sys_obj.link_lim_vals      = self.c_vlts[vk]['link_lim_vals']
        self.sys_obj.link_lim_tags      = self.c_vlts[vk]['link_lim_tags']

    def upd_tk_vars_with_sys_obj(self) -> None:
        """
        Set tk "vars" variables for tkinter from sys_obj

        These must ``set()`` the existing variables, never rebind ``self.*_var``
        to a fresh StringVar/BooleanVar. A widget and a trace both hold the
        variable *object*, so replacing it orphans every widget built from it
        and every callback attached to it. That is why switching vaults used to
        re-``configure`` each widget and re-add each trace afterwards -- and
        because the old variables were still alive and still traced, every
        switch left one more copy of validate_all_fields() and
        update_links_help() registered, for the life of the window.

        Setting them instead updates the screen directly and fires the traces
        that are already there, so the caller has nothing to re-wire.
        :return: None
        """
        logger.debug(f"setupscreen-upd_tk_vars<-sys_obj - {self.sys_obj.vault_name}  TO:")
        logger.debug(f"setupscreen-upd_tk_vars<-sys_obj - {self.vault_name_var.get().strip()}")

        self.vault_name_var.set(self.sys_obj.vault_name)
        self.dir_vault_var.set(self.sys_obj.dir_vault)
        self.skip_rel_str_var.set(self.sys_obj.skip_rel_str)
        self.bool_shw_notes_var.set(self.sys_obj.bool_shw_notes)
        self.bool_rel_paths_var.set(self.sys_obj.bool_rel_paths)
        self.bool_summ_rows_var.set(self.sys_obj.bool_summ_rows)
        self.bool_unused_1_var.set(self.sys_obj.bool_unused_1)
        self.bool_unused_2_var.set(self.sys_obj.bool_unused_2)
        self.bool_unused_3_var.set(self.sys_obj.bool_unused_3)
        self.link_lim_vals_var.set(str(self.sys_obj.link_lim_vals))
        self.link_lim_tags_var.set(str(self.sys_obj.link_lim_tags))

    def show(self) -> bool:
        """Run the setup screen. True if the user saved, False if they cancelled."""
        def upd_log() -> None:
            logger.debug(f"setupscreen:show:upd_log \n")
            logger.debug(f"sys_obj:\n"
                 f"last_vault_name      {self.last_vault_name}\n"
                 f"vault_name           {self.sys_obj.vault_name}\n\n"
                 f"skip_rel_str         {self.sys_obj.skip_rel_str}\n"
                 f"bool_shw_notes       {self.sys_obj.bool_shw_notes}\n"
                 f"bool_rel_paths       {self.sys_obj.bool_rel_paths}\n"
                 f"bool_summ_rows       {self.sys_obj.bool_summ_rows}\n"
                 f"bool_unused_1        {self.sys_obj.bool_unused_1}\n"
                 f"bool_unused_2        {self.sys_obj.bool_unused_2}\n"
                 f"bool_unused_3        {self.sys_obj.bool_unused_3}\n"
                 f"link_lim_vals        {self.sys_obj.link_lim_vals}\n"
                 f"link_lim_tags        {self.sys_obj.link_lim_tags}\n\n"
                 f"vault_id             {self.sys_obj.vault_id}\n"
                 f"dir_vault            {self.sys_obj.dir_vault}\n"
                 f"sys_pn_wb_exec       {self.sys_obj.sys_pn_wb_exec}\n"
                 f"------------------------------------------\n"
            )

        # noinspection PyUnusedLocal
        def vault_name_changed(*args) -> None:
            """
            handle the vault_name combobox changed event
             At this point, the only thing that has changed is the vault_name, so we start swapping...

             First, update cur_vaults (using the last_vault_name) w/the tk (screen) vars
             Next, update sys_obj w/cur_vaults (using the newly selected vault_name)
                   (NB: I know this overwrites sys_obj updates from step one, but that's ok)
             Finally, update the tk (screen) vars w/sys_objs

             NB: Step one will need to be re-done (using the current vault_name) at Save&Run
            """

            logger.debug(f"setupscreen:show:vault_name_chgd =========================================================== vault_name event")
            logger.debug(f"setupscreen:show:vault_name_chgd pre-swaps state")
            upd_log()

            logger.debug(f"setupscreen:show:vault_name_chgd  pre-step1 tk         -> cur_vaults")
            self.upd_all_sys_objs_with_tk_vars(self.last_vault_name)
            upd_log()

            logger.debug(f"setupscreen:show:vault_name_chgd  pre-step2 cur_vaults -> sys_obj")
            self.sys_obj.vault_name = self.vault_name_var.get().strip()
            self.upd_sys_objs_with_vaults(self.sys_obj.vault_name)
            upd_log()

            logger.debug(f"setupscreen:show:vault_name_chgd  pre-step3 sys_objs   -> tk")
            self.upd_tk_vars_with_sys_obj()
            upd_log()

            self.last_vault_name = self.sys_obj.vault_name

            # Nothing is re-configured, re-bound or re-traced here. Step three
            # sets the same variable objects the widgets were built from, so the
            # screen has already followed and the existing traces have already
            # fired. Re-adding them is what made every callback run one extra
            # time per vault switch; recreating the help labels also leaked a
            # Label per switch, stacked over its predecessor in the same cell.
            # These two are called directly only because a value that happens to
            # be unchanged still needs its status re-checked against the new
            # vault's dir_vault.
            self.validate_all_fields()
            update_links_help()

            logger.debug(f"setupscreen:show:vault_name_chgd  ------------------------------------------------------\n\n")

        # noinspection PyUnusedLocal
        def update_links_help(*args) -> None:
            try:
                vals = int(self.link_lim_vals_var.get())
                self.link_lim_vals_help.config(text="(Unlimited)    " if vals == 0 else self.wb_col_help)
            except ValueError:
                self.link_lim_vals_help.config(text=" Invalid!!!")
            try:
                tags = int(self.link_lim_tags_var.get())
                self.link_lim_tags_help.config(text="(Unlimited)    " if tags == 0 else self.wb_col_help)
            except ValueError:
                self.link_lim_tags_help.config(text=" Invalid!!!")

# ============ end of show() function defs - on with the show! ===================================================
        # Main App Frame ---------------------------------------------------------------------
        main_frame = ttk.Frame(self.root, padding="1", borderwidth=1, relief="ridge")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        # main_frame.columnconfigure(1, weight=2)
        mf_row = 0
        f1_1st_col = 0

        # Obsidian Frame ---------------------------------------------------------------------
        f1_row = 0  # f1 denotes frame nesting level one; re-used for each frame
        f1_col = f1_1st_col

        # Obsidian Vault Details Frame ---------------------------------------------------------------------
        obs_frame = ttk.LabelFrame(main_frame, text="Obsidian Vault Details ",
                                   padding="20", borderwidth=1, relief="ridge")
        obs_frame.grid(row=mf_row, column=0, sticky="nsew", pady=5, padx=(10, 10))
        obs_frame.columnconfigure(1, weight=1)

        # label
        ttk.Label(obs_frame, text="Vault Name:", width=15).grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # vault name entry
        f1_col += 1
        logger.debug(f"setupscreen:show:COMBOBOX Set - vault_name_var:{self.vault_name_var.get().strip()}")

        combx_vault_name = ttk.Combobox(obs_frame, textvariable=self.vault_name_var, width=50)
        combx_vault_name['values'] = self.v_list
        combx_vault_name['state'] = 'readonly'
        logger.debug(f"setupscreen:show: v_list:{self.v_list}")

        # combx_vault_name.current(0)
        combx_vault_name.columnconfigure(f1_col, minsize=30, weight=2)
        combx_vault_name.grid(row=f1_row, column=f1_col, sticky="ew", padx=(0, 5))

        # The combobox is the only thing that can present a newly registered
        # vault, and v_list is a snapshot taken in __init__, so commit_vault_dir()
        # needs a handle on it. It was a local until now.
        self.combx_vault_name = combx_vault_name

        # Vault Folder (dir_vault) -- any directory, whether or not Obsidian has
        # ever opened it. Same shape as the Workbook Executable row below:
        # label, entry, status marker, Browse.
        # label
        f1_row += 1
        f1_col = f1_1st_col
        ttk.Label(obs_frame, text="Vault Folder:", width=15).grid(row=f1_row, column=f1_col,
                            sticky="w", padx=5, pady=5)

        # entry Vault Folder (dir_vault)
        f1_col += 1
        # Narrower than the combobox's 50 so the status marker and the Browse
        # button fit beside it: obs_frame sits in main_frame column 0 and cannot
        # span past the logo, so this row only ever has that column to share.
        # It is the weighted column, so the entry takes any width the user adds.
        entry_dir_vault = ttk.Entry(obs_frame, textvariable=self.dir_vault_var, width=38)
        entry_dir_vault.grid(row=f1_row, column=f1_col, sticky="ew", padx=(0, 5))

        # status Vault Folder (dir_vault)
        f1_col += 3
        self.dir_vault_status = ttk.Label(obs_frame, text="", foreground="red")
        self.dir_vault_status.grid(row=f1_row, column=f1_col, sticky="w", padx=10)

        # browse button
        ttk.Button(obs_frame, text="Browse", command=self.browse_vault_dir).grid(
                            row=f1_row, column=6, padx=(15, 0))

        # A missing .obsidian folder is a warning, not an error -- the folder is
        # still scanned and Save stays enabled -- so it cannot be a red marker
        # beside the field, and it needs a line of its own to say what is lost.
        f1_row += 1
        self.vault_warn_label = ttk.Label(obs_frame, text="", foreground=self.warn_clr,
                                          justify="left")
        self.vault_warn_label.grid(row=f1_row, column=0, columnspan=7, sticky="w",
                                   padx=5, pady=(2, 0))

        # Ignore Directories (dir_skip_rel)
        # label
        f1_row += 1
        f1_col = f1_1st_col
        ttk.Label(obs_frame, text="Directories to Ignore:\n(comma separated)").grid(row=f1_row,
                            column=0, sticky="w", padx=5, pady=(20, 5))

        # entry Ignore Directories (dir_skip_rel)
        f1_col += 1
        entry_skip_rel_str = ttk.Entry(obs_frame, textvariable=self.skip_rel_str_var, width=50)
        entry_skip_rel_str.columnconfigure((f1_col, f1_col + 1), minsize=30, weight=2)
        entry_skip_rel_str.grid(row=f1_row, column=f1_col, sticky="ew", padx=(0, 5))

        # status Ignore Directories (dir_skip_rel)
        f1_col += 3
        self.skip_rel_str_status = ttk.Label(obs_frame, text="", foreground="red")
        self.skip_rel_str_status.columnconfigure(f1_col, weight=1)
        self.skip_rel_str_status.grid(row=f1_row, column=f1_col, sticky="w", padx=10)

        # Options Frame ---------------------------------------------------------------------
        mf_row = 4
        # opts_frame = ttk.Frame(main_frame)
        # opts_frame.grid(row=mf_row, column=mf_col, sticky="ew", pady=5, padx=(10, 0))

        opts_frame = ttk.LabelFrame(main_frame, text="Workbook Options  ", padding="20", borderwidth=1, relief="ridge")
        opts_frame.grid(row=mf_row, column=0, sticky="nsew", pady=5, padx=(10, 10)) # padx=(0, 0))
        opts_frame.columnconfigure(1, weight=1)
        # opts_frame.columnconfigure(1, weight=1)

        chekbx_notes = ttk.Checkbutton(opts_frame, text="Show Notes", variable=self.bool_shw_notes_var)
        chekbx_notes.grid(row=0, column=0, sticky="w", pady=5)
        ck_open1 = ttk.Checkbutton(opts_frame, text="For Future Use-1",
                                   variable=self.bool_unused_1_var, state='disabled')
        ck_open1.grid(row=0, column=1, sticky="w", pady=5)
        chekbx_fullp = ttk.Checkbutton(opts_frame, text="Use Full Paths in Links", variable=self.bool_rel_paths_var)
        chekbx_fullp.grid(row=1, column=0, sticky="w", pady=5)
        ck_open2 = ttk.Checkbutton(opts_frame, text="For Future Use-2",
                                   variable=self.bool_unused_2_var, state='disabled')
        ck_open2.grid(row=1, column=1, sticky="w", pady=5)

        mf_row += 1

        # Links Frame ---------------------------------------------------------------------
        # Displayed Links Maximums
        lnks_frame = ttk.LabelFrame(main_frame, text="Workbook Link Columns",
                                    padding="20", borderwidth=1, relief="ridge")
        lnks_frame.grid(row=mf_row, column=0, sticky="nsew", pady=5, padx=(10, 10))
        lnks_frame.columnconfigure(1, weight=1)

        # Label
        ttk.Label(lnks_frame, text="Values Tab Maximum Links:").grid(row=0
                                                                     , column=0
                                                                     , sticky="w"
                                                                     , pady=5
                                                                     , padx=(0, 10))

        spinbx_vals = ttk.Spinbox(lnks_frame, from_=0, to=self.wb_col_max
                                   , textvariable=self.link_lim_vals_var, width=8)
        spinbx_vals.grid(row=0, column=1, sticky="w", pady=5)

        self.link_lim_vals_help = ttk.Label(lnks_frame
                                        , text="(Unlimited)    " if self.sys_obj.link_lim_vals == 0 else self.wb_col_help)
        self.link_lim_vals_help.grid(row=0, column=1, sticky="w", pady=5, padx=(80,0))


        ttk.Label(lnks_frame, text="Tags Tab Maximum Links:").grid(row=1
                                                                   , column=0
                                                                   , sticky="w"
                                                                   , pady=5
                                                                   , padx=(0, 10))
        spinbx_tags = ttk.Spinbox(lnks_frame, from_=0, to=self.wb_col_max
                                   , textvariable=self.link_lim_tags_var, width=8)
        spinbx_tags.grid(row=1, column=1, sticky="w", pady=5)

        self.link_lim_tags_help = ttk.Label(lnks_frame
                                        , text="(Unlimited)    " if self.sys_obj.link_lim_tags == 0 else self.wb_col_help)
        self.link_lim_tags_help.grid(row=1, column=1, sticky="w", pady=5, padx=(80,0))

        self.link_lim_vals_var.trace('w', update_links_help)
        self.link_lim_tags_var.trace('w', update_links_help)
        mf_row += 1

        # Executable Path Frame ---------------------------------------------------------------------
        wbex_frame = ttk.LabelFrame(main_frame, text="Workbook Executable ",
                                    padding="20", borderwidth=1, relief="ridge")
        # columnspan=3 puts this frame across the logo/button column as well, which
        # is the whole point: the Full Path entry sits in the frame's only weighted
        # column, so every pixel gained here goes to the entry. It was 268px wide
        # and could not show the executable it held. Nothing may share row mf_row
        # in another column now -- see the button frame below.
        wbex_frame.grid(row=mf_row, column=0, columnspan=3, sticky="nsew", pady=5, padx=(10, 10))
        wbex_frame.columnconfigure(1, weight=1)

        # label
        ttk.Label(wbex_frame, text="Full Path:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # entry
        wb_exec_entry = ttk.Entry(wbex_frame, textvariable=self.sys_pn_wb_exec_var)
        wb_exec_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))

        # browse  button
        ttk.Button(wbex_frame, text="Browse", command=self.browse_exec_path).grid(row=0, column=6, padx=(15, 0))

        # status
        self.wb_exec_status = ttk.Label(wbex_frame, text="", foreground="red")
        self.wb_exec_status.grid(row=0, column=2, sticky="nw", padx=(5, 0))
        mf_row += 1

        # logo
        mf_col = 2 # = 1
        logo_frame = ttk.Frame(main_frame)
        logo_frame.grid(row=0, column=mf_col, rowspan=5, sticky="new", pady=5, padx=(0, 0))
        # noinspection PyTypeChecker
        logo_label = ttk.Label(logo_frame, image=self.frame_image)
        logo_label.grid(row=0, column=mf_col, sticky="ne", pady=1, padx=1)
        logo_label.columnconfigure(mf_col, weight=1)

        # s = ttk.Separator(main_frame, orient="horizontal").grid(row=6, column=mf_col, sticky="new", padx=10, pady=5)

        # Buttons - Save & Run, Cancel
        button_frame = ttk.Frame(main_frame)
        # Row 5 -- beside the Link Columns frame, under the logo. This must stay
        # ABOVE the executable frame's row: that frame now spans all three columns,
        # so anything left down there would sit on top of it. rowspan is gone for
        # the same reason (it used to reach into row 6). These row numbers are
        # literals rather than mf_row, so the two are coupled by hand.
        button_frame.grid(row=5, column=mf_col, sticky="n", pady=(5, 0))
        self.save_button = ttk.Button(button_frame, text="Save & Run", command=self.on_save_and_run)
        self.save_button.pack(side="top", pady=(5, 10))
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side="top")
        # clear_hist_button = ttk.Button(button_frame, text="Clear History", command=self.on_clear_hist)
        # clear_hist_button.pack(side="top")
        # button_frame.pack(side=tk.TOP, pady=(5, 30))

        # Bind validation
        combx_vault_name.bind('<<ComboboxSelected>>', lambda event: vault_name_changed())
        # Committing on every keystroke would register half-typed paths, and
        # upd_tk_vars_with_sys_obj() setting dir_vault_var would re-enter the
        # swap. The trace only repaints the status labels, which changes no
        # state, so there is nothing to guard against.
        entry_dir_vault.bind('<Return>', self.commit_vault_dir)
        entry_dir_vault.bind('<FocusOut>', self.commit_vault_dir)
        self.dir_vault_var.trace('w', lambda *args: self.validate_all_fields())
        self.skip_rel_str_var.trace('w', lambda *args: self.validate_all_fields())
        self.sys_pn_wb_exec_var.trace('w', lambda *args: self.validate_all_fields())
        self.validate_all_fields()

        # The window's close button must mean the same thing as Cancel. Without
        # this, closing the window destroyed it without a word and the run
        # carried on as though setup had been completed.
        self.root.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Center window
        self.root.update_idletasks()
        logger.debug(f"setupscreen:show:pre-mainloop - vault_name_var:{self.vault_name_var.get().strip()}")
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        self.root.mainloop()

        return self.saved

    def browse_vault_dir(self) -> None:
        """Pick a vault folder. Any directory will do, Obsidian's or not."""
        dir_path = filedialog.askdirectory(
            title="Select Vault Folder",
            initialdir=self.dir_vault_var.get() or "/",
            mustexist=True
        )
        if dir_path:
            self.dir_vault_var.set(dir_path)
            self.commit_vault_dir()

    def commit_vault_dir(self, *_args) -> None:
        """Point the screen at the folder now in the Vault Folder field.

        The folder is registered first if Obsidian has never opened it, so that
        a record exists under the name being displayed: on_save_and_run() calls
        upd_all_sys_objs_with_tk_vars(), which indexes cur_vlts[vault_name] and
        would otherwise raise KeyError.

        Bound to <Return> and <FocusOut> rather than to a trace, so it only ever
        sees whole paths. Idempotent, so the <FocusOut> that fires on the way to
        Browse or to Save is harmless whichever order Tk delivers it in.
        """
        raw = self.dir_vault_var.get().strip()
        if not self.sys_obj.validate_dir_vault(raw)[0]:
            return                          # the status label already says why

        vault_name = self.sys_obj.register_vault_dir(raw)

        # find_vault_by_path() searches sys_vlts, which can hold vaults that
        # cur_vlts does not; the screen only ever indexes cur_vlts.
        if vault_name not in self.c_vlts:
            self.c_vlts[vault_name] = self.sys_obj.sys_vlts[vault_name]

        if vault_name == self.last_vault_name:
            # The same vault. Show the stored spelling anyway -- the folder
            # picker hands back forward slashes on Windows.
            self.dir_vault_var.set(self.c_vlts[vault_name]['dir_vault'])
            return

        # The same three-step swap the combobox does; see vault_name_changed().
        self.upd_all_sys_objs_with_tk_vars(self.last_vault_name)
        self.sys_obj.vault_name = vault_name
        self.upd_sys_objs_with_vaults(vault_name)
        self.upd_tk_vars_with_sys_obj()
        self.last_vault_name = vault_name

        logger.debug(f"setupscreen:commit_vault_dir - now on {vault_name}")

        self.v_list = list(self.c_vlts.keys())
        self.combx_vault_name['values'] = self.v_list

        self.validate_all_fields()

    def browse_exec_path(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Spreadsheet Executable",
            initialdir=os.path.dirname(self.sys_pn_wb_exec_var.get()) if self.sys_pn_wb_exec_var.get() else "/",
            filetypes=[
                ("Executable files", "*.exe" if self.sys_obj.sys_cfg_os == "Windows" else "*"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.sys_pn_wb_exec_var.set(file_path)
            self.validate_all_fields()

    def validate_all_fields(self) -> bool:
        dir_vault_valid, dir_vault_msg = self.sys_obj.validate_dir_vault(self.dir_vault_var.get())
        wb_exec_valid, wb_exec_msg = self.sys_obj.validate_sys_pn_wb_exec(self.sys_pn_wb_exec_var.get())

        # Checked against the committed vault, not against the text sitting in
        # the folder field: this validator walks the whole tree and this method
        # runs on every keystroke, so a half-typed "C:/" would walk the drive.
        self.skip_rel_str_valid, self.skip_rel_str_msg = self.sys_obj.validate_skip_rel_str(
                                                      self.skip_rel_str_var.get()
                                                    , self.sys_obj.dir_vault
                                                    )
        self.dir_vault_status.config(
            text=dir_vault_msg if not dir_vault_valid else "✓",
            foreground="red" if not dir_vault_valid else "green"
            )
        # Never joins all_valid: a folder with no .obsidian is scannable, and
        # the user is allowed to go ahead. Cleared when the path itself is bad,
        # because the red message above has already said so.
        _, obs_warn_msg = self.sys_obj.check_obsidian_dir(self.dir_vault_var.get())
        self.vault_warn_label.config(text=obs_warn_msg if dir_vault_valid else "")

        self.wb_exec_status.config(
            text=wb_exec_msg if not wb_exec_valid else "✓",
            foreground="red" if not wb_exec_valid else "green"
            )
        self.skip_rel_str_status.config(
            text=self.skip_rel_str_msg if not self.skip_rel_str_valid else
                                        "✓" if self.skip_rel_str_var.get().strip() else "",
            foreground="red" if not self.skip_rel_str_valid else "green"
            )
        all_valid = dir_vault_valid and wb_exec_valid and self.skip_rel_str_valid
        self.save_button.config(state="normal" if all_valid else "disabled")
        return all_valid

    def on_save_and_run(self) -> None:
        if self.validate_all_fields():
            self.upd_all_sys_objs_with_tk_vars(self.sys_obj.vault_name)
            self.sys_obj.ovi_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # save_config() takes no arguments -- it writes to sys_pn_cfg
            # itself. Passing one raised TypeError the moment the button was
            # pressed, which is what made --setup unusable.
            if self.sys_obj.save_config():
                self.saved = True
                self.root.quit()
                self.root.destroy()
            else:
                messagebox.showerror("Error", "Failed to save configuration")

    def on_cancel(self) -> None:
        """Cancel, or the window's close button. Leaves self.saved False."""
        logger.info("setupscreen: setup cancelled by the user")
        self.root.quit()
        self.root.destroy()

def main() -> None:
    pass

if __name__ == '__main__':
    main()


