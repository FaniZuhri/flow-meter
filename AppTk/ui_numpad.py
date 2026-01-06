import tkinter as tk
from tkinter import ttk


class TouchNumpad(tk.Toplevel):
    def __init__(self, parent, target_widget, title="Input"):
        super().__init__(parent)
        self.target_widget = target_widget
        self.title(title)

        # Window Configuration
        self.geometry("300x400")
        self.resizable(False, False)
        self.transient(parent)  # Keep on top of parent
        self.grab_set()  # Modal (disable main window interactions)

        # Center the keypad relative to parent
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 150
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 200
        self.geometry(f"+{x}+{y}")

        # Internal buffer
        self.current_text = tk.StringVar(value=target_widget.get())

        self._build_ui()

    def _build_ui(self):
        # Display Area
        disp_frame = ttk.Frame(self, padding=10)
        disp_frame.pack(fill="x")

        lbl_display = ttk.Label(
            disp_frame,
            textvariable=self.current_text,
            font=("Consolas", 24, "bold"),
            anchor="e",
            background="white",
            relief="sunken",
        )
        lbl_display.pack(fill="x", ipady=10)

        # Buttons Frame
        btn_frame = ttk.Frame(self, padding=5)
        btn_frame.pack(fill="both", expand=True)

        # Grid Configuration
        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)
        for i in range(4):
            btn_frame.rowconfigure(i, weight=1)

        # Button Layout
        keys = [
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
        style.configure("Numpad.TButton", font=("Segoe UI", 14, "bold"), padding=10)
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 12, "bold"),
            background="#007BFF",
            foreground="black",
        )

        for text, row, col in keys:
            # Span logic for OK button
            colspan = 2 if text == "OK" else 1

            # Styling logic
            s = "Numpad.TButton"
            cmd = lambda t=text: self._on_key(t)

            btn = ttk.Button(btn_frame, text=text, style=s, command=cmd)
            btn.grid(
                row=row, column=col, columnspan=colspan, sticky="nsew", padx=2, pady=2
            )

    def _on_key(self, key):
        val = self.current_text.get()

        if key == "OK":
            # Save to target widget and close
            self.target_widget.delete(0, tk.END)
            self.target_widget.insert(0, val)
            self.destroy()

        elif key == "ESC":
            self.destroy()

        elif key == "CLR":
            self.current_text.set("")

        elif key == "BS":
            self.current_text.set(val[:-1])

        elif key == ".":
            if "." not in val:
                self.current_text.set(val + ".")

        else:  # Numbers
            if val == "0" and key != ".":  # Prevent 01, 05 etc
                self.current_text.set(key)
            else:
                self.current_text.set(val + key)
