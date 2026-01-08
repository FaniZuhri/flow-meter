import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Callable


## @class TouchNumpad
#  @brief Modal numeric keypad for touchscreens.
class TouchNumpad(tk.Toplevel):
    def __init__(self, parent: tk.Tk, target: ttk.Entry, title: str = "Input") -> None:
        super().__init__(parent)
        self.target_widget: ttk.Entry = target
        self.title(title)

        self.withdraw()

        self.geometry("300x400")
        self.resizable(False, False)
        self.transient(parent)

        # Center window
        if parent.winfo_viewable():
            x: int = parent.winfo_x() + (parent.winfo_width() // 2) - 150
            y: int = parent.winfo_y() + (parent.winfo_height() // 2) - 200
            self.geometry(f"+{x}+{y}")

        self.val_buffer: tk.StringVar = tk.StringVar(value=target.get())
        self._setup_layout()

        self.deiconify()

        self.update_idletasks()
        self.wait_visibility()

        self.grab_set()
        self.focus_set()

    def _setup_layout(self) -> None:
        # Display
        disp_f: ttk.Frame = ttk.Frame(self, padding=10)
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
        pad_f: ttk.Frame = ttk.Frame(self, padding=5)
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

        s: ttk.Style = ttk.Style()
        s.configure("Num.TButton", font=("Segoe UI", 14, "bold"), padding=10)

        for txt, r, c in keys:
            sp: int = 2 if txt == "OK" else 1
            cmd: Callable = lambda t=txt: self._handle_press(t)
            btn: ttk.Button = ttk.Button(
                pad_f, text=txt, style="Num.TButton", command=cmd
            )
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
