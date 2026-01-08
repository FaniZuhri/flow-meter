import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Callable


## @class TouchNumpad
#  @brief A modal, borderless numeric keypad optimized for Raspberry Pi touchscreens.
#  @details Uses 'overrideredirect' and 'topmost' to ensure visibility over the main application.
class TouchNumpad(tk.Toplevel):

    ## @brief Constructor.
    #  @param parent The main application window.
    #  @param target_widget The Entry widget to update.
    #  @param title The title (unused in borderless mode, but kept for compatibility).
    def __init__(
        self, parent: tk.Tk, target_widget: ttk.Entry, title: str = "Input"
    ) -> None:
        super().__init__(parent)
        self.target_widget: ttk.Entry = target_widget

        # 1. Configuration for Kiosk Mode
        # Remove OS borders/title bar (Crucial for Pi stability)
        self.overrideredirect(True)
        # Force window to stay on top of everything
        self.attributes("-topmost", True)

        self.configure(bg="#e1e1e1")  # Slight border color effect
        self.geometry("300x400")

        # 2. Geometry Calculation (Center on Screen)
        # We use screen dimensions because update_idletasks on parent can be flaky on Pi
        screen_w: int = self.winfo_screenwidth()
        screen_h: int = self.winfo_screenheight()

        win_w: int = 300
        win_h: int = 400

        pos_x: int = (screen_w // 2) - (win_w // 2)
        pos_y: int = (screen_h // 2) - (win_h // 2)

        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        # Internal buffer
        self.val_buffer: tk.StringVar = tk.StringVar(value=target_widget.get())

        self._setup_layout()

        # 3. Activation Sequence (Strict Order)
        # Ensure the OS draws it before we lock the UI
        self.update_idletasks()
        self.deiconify()
        self.lift()

        # 4. Input Grabbing
        # We try-catch the grab because sometimes on fast clicks it can race condition
        try:
            self.wait_visibility()
            self.grab_set()
            self.focus_force()  # Force keyboard focus to this window
        except tk.TclError:
            pass  # Window might have been closed instantly or race condition

    def _setup_layout(self) -> None:
        # Main Container with padding (simulates a border since we removed OS border)
        main_frame: ttk.Frame = ttk.Frame(self, padding=2, style="Card.TFrame")
        main_frame.pack(fill="both", expand=True)

        # Header (Custom Title Bar since we removed the OS one)
        header_frame: ttk.Frame = ttk.Frame(main_frame, style="Sidebar.TFrame")
        header_frame.pack(fill="x", pady=(0, 5))

        lbl_title: ttk.Label = ttk.Label(
            header_frame,
            text="Input Value",
            font=("Segoe UI", 10, "bold"),
            style="Sidebar.TLabel",
        )
        lbl_title.pack(side="left", padx=10, pady=5)

        # Close 'X' button
        btn_close: ttk.Button = ttk.Button(
            header_frame,
            text="X",
            width=3,
            style="Danger.TButton",
            command=self.destroy,
        )
        btn_close.pack(side="right", padx=2, pady=2)

        # Display Area
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

        # Buttons
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

        # Use existing styles
        for txt, r, c in keys:
            sp: int = 2 if txt == "OK" else 1

            # Special styling for action buttons
            style_key: str = "Primary.TButton" if txt == "OK" else "TButton"
            if txt in ["ESC", "CLR", "BS"]:
                style_key = "Danger.TButton"

            # Simple wrapper to create a slightly larger font style dynamically if needed
            # or rely on ui_styles.py defaults. We will stick to standard TButton for digits
            # but maybe increase font manually if ui_styles doesn't cover specific "Num" style.

            cmd: Callable = lambda t=txt: self._handle_press(t)
            btn: ttk.Button = ttk.Button(pad_f, text=txt, style=style_key, command=cmd)
            btn.grid(row=r, column=c, columnspan=sp, sticky="nsew", padx=2, pady=2)

    def _handle_press(self, key: str) -> None:
        curr: str = self.val_buffer.get()

        if key == "OK":
            self.target_widget.delete(0, tk.END)
            self.target_widget.insert(0, curr)
            self.destroy()
        elif key == "ESC":
            self.destroy()
        elif key == "CLR":
            self.val_buffer.set("")
        elif key == "BS":
            self.val_buffer.set(curr[:-1])
        elif key == ".":
            if "." not in curr:
                self.val_buffer.set(curr + ".")
        else:
            if curr == "0" and key != ".":
                self.val_buffer.set(key)
            else:
                self.val_buffer.set(curr + key)
