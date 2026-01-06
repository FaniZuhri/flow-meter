from tkinter import ttk


def apply_theme(root):
    """
    Configures the Tkinter style to match a flat, Modern, Qt-like theme.
    """
    style = ttk.Style(root)

    # Try to use 'clam' theme as base
    try:
        style.theme_use("clam")
    except:
        pass

    # -- Palette --
    BG_MAIN = "#FFFFFF"
    BG_SIDE = "#F0F2F5"
    ACCENT = "#007BFF"
    ACCENT_HOVER = "#0056b3"
    TEXT_COLOR = "#212529"
    BORDER_COLOR = "#CED4DA"

    # -- General Defaults --
    root.configure(bg=BG_MAIN)
    style.configure(
        ".", background=BG_MAIN, foreground=TEXT_COLOR, font=("Segoe UI", 10)
    )

    # -- Frames --
    style.configure("TFrame", background=BG_MAIN, relief="flat")
    style.configure("Sidebar.TFrame", background=BG_SIDE, relief="flat")
    style.configure(
        "Card.TFrame",
        background=BG_MAIN,
        relief="solid",
        borderwidth=1,
        bordercolor=BORDER_COLOR,
    )

    # -- Labels --
    style.configure("TLabel", background=BG_MAIN, foreground=TEXT_COLOR)
    style.configure("Sidebar.TLabel", background=BG_SIDE, foreground=TEXT_COLOR)
    style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
    style.configure("Status.TLabel", font=("Segoe UI", 9))

    # -- Treeview (Tables) --
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
        foreground=TEXT_COLOR,
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", "white")],
    )

    # -- Buttons --
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="white",
        borderwidth=0,
        focuscolor="none",
        padding=(10, 5),
    )
    style.map(
        "Primary.TButton",
        background=[("active", ACCENT_HOVER), ("disabled", "#cccccc")],
    )

    style.configure(
        "Nav.TButton",
        background=BG_SIDE,
        foreground=TEXT_COLOR,
        borderwidth=0,
        anchor="w",
        font=("Segoe UI", 11),
        padding=(15, 8),
    )
    style.map(
        "Nav.TButton",
        background=[("active", "#E2E6EA")],
        foreground=[("active", ACCENT)],
    )

    style.configure(
        "Danger.TButton",
        background="#DC3545",
        foreground="white",
        borderwidth=0,
        padding=(10, 5),
    )
    style.map("Danger.TButton", background=[("active", "#bd2130")])

    # -- Inputs & Others --
    style.configure(
        "TEntry", fieldbackground="white", bordercolor=BORDER_COLOR, padding=5
    )
    style.configure("TCombobox", fieldbackground="white", arrowcolor=TEXT_COLOR)
    style.configure(
        "TLabelframe", background=BG_MAIN, bordercolor=BORDER_COLOR, borderwidth=1
    )
    style.configure(
        "TLabelframe.Label",
        background=BG_MAIN,
        foreground="#6c757d",
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "Horizontal.TProgressbar",
        background=ACCENT,
        troughcolor="#e9ecef",
        borderwidth=0,
    )
