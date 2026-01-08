import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Callable, Optional


## @class TouchNumpad
#  @brief A persistent, borderless numeric keypad.
#  @details Created once and hidden/shown as needed to prevent Window Manager race conditions.
class TouchNumpad(tk.Toplevel):

    ## @brief Constructor.
    #  @param parent The main application window.
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.parent = parent
        self.target_widget: Optional[ttk.Entry] = None

        # 1. Window Configuration
        self.overrideredirect(True)  # Remove OS borders
        self.attributes("-topmost", True)  # Force on top
        self.configure(bg="#e1e1e1")
        self.geometry("300x400")

        # Hide initially
        self.withdraw()

        # Internal buffer
        self.val_buffer: tk.StringVar = tk.StringVar(value="")

        self._setup_layout()

        # Bind close event to physical close just in case
        self.protocol("WM_DELETE_WINDOW", self.hide)

    ## @brief Shows the keypad for a specific target widget.
    #  @param target_widget The Entry widget to edit.
    #  @param title Title to display on the keypad header.
    def show(self, target_widget: ttk.Entry, title: str = "Input") -> None:
        self.target_widget = target_widget
        self.val_buffer.set(target_widget.get())
        self.lbl_title.config(text=title)

        # 1. Position Center Screen
        sw: int = self.winfo_screenwidth()
        sh: int = self.winfo_screenheight()
        w, h = 300, 400
        x: int = (sw // 2) - (w // 2)
        y: int = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # 2. Show Window
        self.deiconify()
        self.lift()

        # 3. Lock Input (Critical Sequence for Pi)
        # We perform an update to ensure the WM recognizes the window exists
        # before we try to grab focus.
        self.update_idletasks()
        try:
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            pass

    ## @brief Hides the keypad and releases input lock.
    def hide(self) -> None:
        # 1. Release Input Lock FIRST
        self.grab_release()

        # 2. Hide Window
        self.withdraw()

        # 3. Return focus to parent
        self.parent.focus_set()

    def _setup_layout(self) -> None:
        # Main Container
        main_frame: ttk.Frame = ttk.Frame(self, padding=2, style="Card.TFrame")
        main_frame.pack(fill="both", expand=True)

        # Header
        header_frame: ttk.Frame = ttk.Frame(main_frame, style="Sidebar.TFrame")
        header_frame.pack(fill="x", pady=(0, 5))

        self.lbl_title = ttk.Label(
            header_frame,
            text="Input",
            font=("Segoe UI", 10, "bold"),
            style="Sidebar.TLabel",
        )
        self.lbl_title.pack(side="left", padx=10, pady=5)

        # Close Button calls hide(), not destroy()
        btn_close: ttk.Button = ttk.Button(
            header_frame, text="X", width=3, style="Danger.TButton", command=self.hide
        )
        btn_close.pack(side="right", padx=2, pady=2)

        # Display
        disp_f: ttk.Frame = ttk.Frame(main_frame, padding=5)
        disp_f.pack(fill="x")

        lbl: ttk.Label = ttk.Label(
            disp_f,
            textvariable=self.val_buffer,
            font=("Consolas", 24, "bold"),
            anchor="e",
            background="white",
            relief="sunken",
        )
        lbl.pack(fill="x", ipady=10)

        # Keypad Grid
        pad_f: ttk.Frame = ttk.Frame(main_frame, padding=5)
        pad_f.pack(fill="both", expand=True)

        for i in range(4):
            pad_f.columnconfigure(i, weight=1)
        for i in range(4):
            pad_f.rowconfigure(i, weight=1)

        keys: List[Tuple[str, int, int]] = [
            ("7", 0, 0),
            ("8", 0, 1),
            ("9", 0, 2),
            ("BS", 0, 3),
            ("4", 1, 0),
            ("5", 1, 1),
            ("6", 1, 2),
            ("CLR", 1, 3),
            ("1", 2, 0),
            ("2", 2, 1),
            ("3", 2, 2),
            ("ESC", 2, 3),
            ("0", 3, 0),
            (".", 3, 1),
            ("OK", 3, 2),
        ]

        style = ttk.Style()
        style.configure("Num.TButton", font=("Segoe UI", 14, "bold"), padding=10)

        for txt, r, c in keys:
            sp: int = 2 if txt == "OK" else 1

            # Button Logic
            cmd: Callable = lambda t=txt: self._handle_press(t)

            # Styling override for numpad specific buttons
            s_key = "Num.TButton"
            if txt in ["OK"]:
                s_key = "Primary.TButton"
            if txt in ["ESC", "BS", "CLR"]:
                s_key = "Danger.TButton"

            btn: ttk.Button = ttk.Button(pad_f, text=txt, style=s_key, command=cmd)
            btn.grid(row=r, column=c, columnspan=sp, sticky="nsew", padx=2, pady=2)

    def _handle_press(self, key: str) -> None:
        curr: str = self.val_buffer.get()

        if key == "OK":
            if self.target_widget:
                self.target_widget.delete(0, tk.END)
                self.target_widget.insert(0, curr)
            self.hide()
        elif key == "ESC":
            self.hide()
        elif key == "CLR":
            self.val_buffer.set("")
        elif key == "BS":
            self.val_buffer.set(curr[:-1])
        elif key == ".":
            if "." not in curr:
                self.val_buffer.set(curr + ".")
        else:  # Numbers
            if curr == "0" and key != ".":
                self.val_buffer.set(key)
            else:
                self.val_buffer.set(curr + key)
