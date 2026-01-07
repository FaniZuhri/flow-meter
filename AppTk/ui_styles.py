import tkinter as tk
from tkinter import ttk


## @brief Configures application-wide colors and styles.
def apply_app_theme(root: tk.Tk) -> None:
    style: ttk.Style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except:
        pass

    # Colors
    C_BG: str = "#FFFFFF"
    C_SIDE: str = "#F0F2F5"
    C_ACCENT: str = "#007BFF"
    C_ACC_HOV: str = "#0056b3"
    C_TEXT: str = "#212529"
    C_BORDER: str = "#CED4DA"
    C_DAN: str = "#DC3545"
    C_DAN_HOV: str = "#bd2130"

    root.configure(bg=C_BG)
    style.configure(".", background=C_BG, foreground=C_TEXT, font=("Segoe UI", 10))

    # Frames
    style.configure("TFrame", background=C_BG, relief="flat")
    style.configure("Sidebar.TFrame", background=C_SIDE, relief="flat")
    style.configure(
        "Card.TFrame",
        background=C_BG,
        relief="solid",
        borderwidth=1,
        bordercolor=C_BORDER,
    )

    # Labels
    style.configure("TLabel", background=C_BG, foreground=C_TEXT)
    style.configure("Sidebar.TLabel", background=C_SIDE, foreground=C_TEXT)
    style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
    style.configure("Status.TLabel", font=("Segoe UI", 9))

    # Treeview
    style.configure(
        "Treeview",
        background="white",
        fieldbackground="white",
        rowheight=25,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background="#e9ecef",
        foreground=C_TEXT,
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", C_ACCENT)],
        foreground=[("selected", "white")],
    )

    # Buttons
    style.configure(
        "Primary.TButton",
        background=C_ACCENT,
        foreground="white",
        borderwidth=0,
        focuscolor="none",
        padding=(10, 5),
    )
    style.map(
        "Primary.TButton", background=[("active", C_ACC_HOV), ("disabled", "#cccccc")]
    )

    style.configure(
        "Nav.TButton",
        background=C_SIDE,
        foreground=C_TEXT,
        borderwidth=0,
        anchor="w",
        font=("Segoe UI", 11),
        padding=(15, 8),
    )
    style.map(
        "Nav.TButton",
        background=[("active", "#E2E6EA")],
        foreground=[("active", C_ACCENT)],
    )

    style.configure(
        "Danger.TButton",
        background=C_DAN,
        foreground="white",
        borderwidth=0,
        padding=(10, 5),
    )
    style.map("Danger.TButton", background=[("active", C_DAN_HOV)])

    # Inputs
    style.configure("TEntry", fieldbackground="white", bordercolor=C_BORDER, padding=5)
    style.configure("TCombobox", fieldbackground="white", arrowcolor=C_TEXT)
    style.configure("TLabelframe", background=C_BG, bordercolor=C_BORDER, borderwidth=1)
    style.configure(
        "TLabelframe.Label",
        background=C_BG,
        foreground="#6c757d",
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "Horizontal.TProgressbar",
        background=C_ACCENT,
        troughcolor="#e9ecef",
        borderwidth=0,
    )
