import tkinter as tk
from tkinter import ttk, messagebox
import os
import queue
import math
from typing import Dict, Any, Optional, Tuple

from controller import WMTKController
from ui_styles import apply_app_theme
from ui_numpad import TouchNumpad


## @class WaterMeterAppTk
#  @brief Main Application Window (View).
class WaterMeterAppTk(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Portable WMTK Proto")

        self.geometry("800x420")

        self.resizable(False, False)

        self.ctrl: WMTKController = WMTKController()

        apply_app_theme(self)
        self.logo_icon: Optional[tk.PhotoImage] = None
        self._init_assets()

        self._init_ui()
        self._init_logic()

        self.numpad = TouchNumpad(self)

        self.after(100, self._loop_serial)
        self.after(500, self._loop_sensor)

    def _init_assets(self) -> None:
        path: str = os.path.join("assets", "logo.png")
        if os.path.exists(path):
            try:
                src: tk.PhotoImage = tk.PhotoImage(file=path)
                tgt_w: int = 100
                orig_w: int = src.width()

                # Rational Scaling: Width 100px
                div: int = math.gcd(tgt_w, orig_w)
                zoom: int = tgt_w // div
                sub: int = orig_w // div

                if zoom > 10:
                    sf: int = int(orig_w / tgt_w) or 1
                    self.logo_icon = src.subsample(sf)
                else:
                    self.logo_icon = src.zoom(zoom).subsample(sub)

                self.iconphoto(False, self.logo_icon)
            except Exception as e:
                print(f"[UI] Logo Error: {e}")

    # --- UI Building ---
    def _init_ui(self) -> None:
        self.container: ttk.Frame = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        # Sidebar
        self.sb: ttk.Frame = ttk.Frame(
            self.container, style="Sidebar.TFrame", width=160
        )
        self.sb.pack(side="left", fill="y")
        self.sb.pack_propagate(False)

        # Header (Logo + Title)
        hdr: ttk.Frame = ttk.Frame(self.sb, style="Sidebar.TFrame")
        hdr.pack(pady=(2, 1))

        if self.logo_icon:
            ttk.Label(hdr, image=self.logo_icon, style="Sidebar.TLabel").pack(
                side="top", pady=(0, 1)
            )

        ttk.Label(
            hdr,
            text="WMTK Proto",
            style="Sidebar.TLabel",
            font=("Segoe UI", 12, "bold"),
            justify="center",
        ).pack(side="top")

        # Nav
        nav_f: ttk.Frame = ttk.Frame(self.sb, style="Sidebar.TFrame")
        nav_f.pack(fill="x", pady=1)

        menu = [
            ("Test Mode", "test"),
            ("History", "history"),
            ("Temp Calib", "temp"),
            ("Press Calib", "press"),
            ("Flow Calib", "flow"),
        ]

        for txt, key in menu:
            ttk.Button(
                nav_f,
                text=txt,
                style="Nav.TButton",
                command=lambda k=key: self.show_page(k),
            ).pack(fill="x", pady=0)

        # Spacer pushes connection box down
        ttk.Frame(self.sb, style="Sidebar.TFrame").pack(fill="both", expand=True)

        # Connection
        conn: ttk.Frame = ttk.Frame(self.sb, style="Sidebar.TFrame")
        conn.pack(side="bottom", fill="x", padx=10, pady=2)

        ttk.Label(
            conn, text="Port:", style="Sidebar.TLabel", font=("Segoe UI", 8)
        ).pack(anchor="w")
        self.cmb_p: ttk.Combobox = ttk.Combobox(conn, state="readonly", height=4)
        self.cmb_p.pack(fill="x", pady=(0, 1))

        self.btn_conn: ttk.Button = ttk.Button(
            conn, text="Connect", style="Primary.TButton", command=self.do_connect
        )
        self.btn_conn.pack(fill="x", pady=(2, 0))

        self.lbl_stat: ttk.Label = ttk.Label(
            conn,
            text="Disconnected",
            style="Sidebar.TLabel",
            font=("Segoe UI", 8),
            foreground="red",
        )
        self.lbl_stat.pack(pady=(1, 0))

        # Body
        self.body: ttk.Frame = ttk.Frame(self.container, padding=10)
        self.body.pack(side="left", fill="both", expand=True)

        self.pages: Dict[str, ttk.Frame] = {}
        self._build_pg_test()
        self._build_pg_history()
        self._build_pg_calib_generic("temp", "Temperature", "TEMP", "°C")
        self._build_pg_calib_generic("press", "Pressure", "PRESS", "Bar")
        self._build_pg_calib_flow()

        self.show_page("test")

    def _build_pg_test(self) -> None:
        p: ttk.Frame = ttk.Frame(self.body)
        self.pages["test"] = p
        ttk.Label(p, text="Automated Test", style="Header.TLabel").pack(
            anchor="w", pady=(0, 5)
        )

        # Cards
        c_frm: ttk.Frame = ttk.Frame(p)
        c_frm.pack(fill="x")
        self.card_flow: ttk.Label = self._mk_card(c_frm, "Flow (L/h)", "#007BFF")
        self.card_pres: ttk.Label = self._mk_card(c_frm, "Pressure (Bar)", "#28A745")
        self.card_temp: ttk.Label = self._mk_card(c_frm, "Temp (°C)", "#DC3545")

        # Inputs
        f_frm: ttk.Labelframe = ttk.Labelframe(p, text="Parameters", padding=10)
        f_frm.pack(fill="x", pady=10)

        # Row 1
        r1: ttk.Frame = ttk.Frame(f_frm)
        r1.pack(fill="x", pady=(0, 5))
        ttk.Label(r1, text="1. Target (L):", font=("Segoe UI", 10, "bold")).pack(
            side="left"
        )
        self.ent_tgt: ttk.Entry = ttk.Entry(r1, width=12)
        self.ent_tgt.pack(side="left", padx=(5, 25))
        self._bind_numpad(self.ent_tgt, "Target Vol")

        ttk.Label(r1, text="2. Init (m³):").pack(side="left")
        self.ent_ini: ttk.Entry = ttk.Entry(r1, width=12)
        self.ent_ini.pack(side="left", padx=(5, 0))
        self._bind_numpad(self.ent_ini, "Initial Meter")

        ttk.Separator(f_frm, orient="horizontal").pack(fill="x", pady=(0, 5))

        # Row 2
        r2: ttk.Frame = ttk.Frame(f_frm)
        r2.pack(fill="x")
        ttk.Label(r2, text="3. Final (m³):").pack(side="left")
        self.ent_fin: ttk.Entry = ttk.Entry(r2, width=12)
        self.ent_fin.pack(side="left", padx=(5, 10))
        self._bind_numpad(self.ent_fin, "Final Meter")
        ttk.Label(
            r2,
            text="(Post-test input)",
            foreground="gray",
            font=("Segoe UI", 9, "italic"),
        ).pack(side="left")

        # Buttons
        act_f: ttk.Frame = ttk.Frame(p)
        act_f.pack(fill="x", pady=5)
        self.btn_t_start: ttk.Button = ttk.Button(
            act_f, text="Start", style="Primary.TButton", command=self.act_test_start
        )
        self.btn_t_start.pack(side="left", padx=(5, 0))
        self.btn_t_save: ttk.Button = ttk.Button(
            act_f,
            text="Finish & Save",
            style="Primary.TButton",
            state="disabled",
            command=self.act_test_save,
        )
        self.btn_t_save.pack(side="left", padx=5)
        ttk.Button(
            act_f, text="Reset", style="Danger.TButton", command=self.act_test_reset
        ).pack(side="right", padx=5)

        # Progress
        self.prog_bar: ttk.Progressbar = ttk.Progressbar(
            p, style="Horizontal.TProgressbar", orient="horizontal", mode="determinate"
        )
        self.prog_bar.pack(fill="x", pady=(5, 2), padx=5)
        self.lbl_prog: ttk.Label = ttk.Label(
            p, text="0.00 / 0.00 L", font=("Segoe UI", 10, "bold"), foreground="#6c757d"
        )
        self.lbl_prog.pack(pady=(0, 5))

    def _build_pg_history(self) -> None:
        p: ttk.Frame = ttk.Frame(self.body)
        self.pages["history"] = p

        tf: ttk.Frame = ttk.Frame(p)
        tf.pack(fill="x", pady=(0, 10))
        ttk.Label(tf, text="Logs", style="Header.TLabel").pack(side="left")
        ttk.Button(
            tf, text="Del Selected", style="Danger.TButton", command=self.act_hist_del
        ).pack(side="right", padx=5)
        ttk.Button(
            tf, text="Refresh", style="Primary.TButton", command=self.act_hist_ref
        ).pack(side="right", padx=5)

        cols: Tuple[str, ...] = (
            "ts",
            "tgt",
            "ini",
            "fin",
            "meas",
            "real",
            "err",
            "stat",
        )
        self.tree: ttk.Treeview = ttk.Treeview(
            p, columns=cols, show="headings", selectmode="extended"
        )

        hdrs = {
            "ts": ("Date", 140),
            "tgt": ("Tgt(L)", 60),
            "ini": ("Ini", 60),
            "fin": ("Fin", 60),
            "meas": ("Meter(L)", 70),
            "real": ("Real(L)", 70),
            "err": ("Err(%)", 60),
            "stat": ("Stat", 70),
        }
        for c, (t, w) in hdrs.items():
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")

        sb: ttk.Scrollbar = ttk.Scrollbar(p, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_pg_calib_generic(
        self, key: str, title: str, stype: str, unit: str
    ) -> None:
        p: ttk.Frame = ttk.Frame(self.body)
        self.pages[key] = p
        ttk.Label(p, text=title, style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        hf: ttk.Frame = ttk.Frame(p)
        hf.pack(fill="x", pady=5)
        cmb: ttk.Combobox = ttk.Combobox(hf, state="readonly", width=30)
        cmb.pack(side="left", padx=(0, 5))
        l_ref: ttk.Label = ttk.Label(hf, text="Ref: -")
        l_ref.pack(side="left", padx=10)
        l_gain: ttk.Label = ttk.Label(hf, text="Gain: -")
        l_gain.pack(side="left", padx=10)

        self.refs_cal = getattr(self, "refs_cal", {})
        self.refs_cal[stype] = {"c": cmb, "lr": l_ref, "lg": l_gain}
        cmb.bind("<<ComboboxSelected>>", lambda e, s=stype: self.act_cal_sel(s))
        ttk.Button(
            hf,
            text="Delete",
            style="Danger.TButton",
            command=lambda s=stype: self.act_cal_del(s),
        ).pack(side="right")

        frm: ttk.Labelframe = ttk.Labelframe(p, text="New Point", padding=15)
        frm.pack(fill="x", pady=15)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text=f"Sensor ({unit}):").grid(
            row=0, column=0, sticky="e", padx=5
        )
        l_liv: ttk.Label = ttk.Label(frm, text="0.00", font=("Consolas", 14, "bold"))
        l_liv.grid(row=0, column=1, sticky="w", padx=5)
        setattr(self, f"lbl_live_{key}", l_liv)

        ttk.Label(frm, text=f"Reference ({unit}):").grid(
            row=1, column=0, sticky="e", padx=5
        )
        e_ref: ttk.Entry = ttk.Entry(frm, width=15)
        e_ref.grid(row=1, column=1, sticky="w", padx=5)
        self._bind_numpad(e_ref, f"Ref {unit}")
        setattr(self, f"ent_ref_{key}", e_ref)

        ttk.Button(
            frm,
            text="Save",
            style="Primary.TButton",
            command=lambda s=stype, k=key: self.act_cal_save(s, k),
        ).grid(row=2, column=1, sticky="w", pady=15)

    def _build_pg_calib_flow(self) -> None:
        p: ttk.Frame = ttk.Frame(self.body)
        self.pages["flow"] = p
        ttk.Label(p, text="Flow Calibration", style="Header.TLabel").pack(
            anchor="w", pady=(0, 10)
        )

        hf: ttk.Frame = ttk.Frame(p)
        hf.pack(fill="x", pady=5)
        cmb: ttk.Combobox = ttk.Combobox(hf, state="readonly", width=30)
        cmb.pack(side="left", padx=(0, 5))
        lr: ttk.Label = ttk.Label(hf, text="Ref: -")
        lr.pack(side="left", padx=5)
        lg: ttk.Label = ttk.Label(hf, text="Gain: -")
        lg.pack(side="left", padx=5)

        self.refs_cal = getattr(self, "refs_cal", {})
        self.refs_cal["FLOW"] = {"c": cmb, "lr": lr, "lg": lg}
        cmb.bind("<<ComboboxSelected>>", lambda e: self.act_cal_sel("FLOW"))
        ttk.Button(
            hf,
            text="Delete",
            style="Danger.TButton",
            command=lambda: self.act_cal_del("FLOW"),
        ).pack(side="right")

        mf: ttk.Frame = ttk.Frame(p)
        mf.pack(fill="both", expand=True, pady=10)

        # Left: Cap
        cf: ttk.Labelframe = ttk.Labelframe(mf, text="1. Capture", padding=10)
        cf.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.btn_f_start: ttk.Button = ttk.Button(
            cf, text="Start Flow", style="Primary.TButton", command=self.act_f_start
        )
        self.btn_f_start.pack(fill="x", pady=5)
        self.btn_f_stop: ttk.Button = ttk.Button(
            cf, text="Stop Flow", style="Danger.TButton", command=self.act_f_stop
        )
        self.btn_f_stop.pack(fill="x", pady=5)
        ttk.Label(cf, text="Raw Vol:").pack(anchor="w", pady=(10, 0))
        self.l_f_rv: ttk.Label = ttk.Label(
            cf, text="0.00", font=("Consolas", 14, "bold"), foreground="gray"
        )
        self.l_f_rv.pack(anchor="w")
        ttk.Label(cf, text="Avg Flow:").pack(anchor="w", pady=(5, 0))
        self.l_f_ra: ttk.Label = ttk.Label(
            cf, text="0.00", font=("Consolas", 14, "bold"), foreground="#007BFF"
        )
        self.l_f_ra.pack(anchor="w")

        # Right: Ref
        rf: ttk.Labelframe = ttk.Labelframe(mf, text="2. Reference", padding=10)
        rf.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ttk.Label(rf, text="A: Volume (L)").pack(anchor="w")
        self.e_f_rv: ttk.Entry = ttk.Entry(rf)
        self.e_f_rv.pack(fill="x", pady=(0, 5))
        self._bind_numpad(self.e_f_rv, "Ref Vol")
        ttk.Label(rf, text="B: Rate (L/h)").pack(anchor="w")
        self.e_f_rr: ttk.Entry = ttk.Entry(rf)
        self.e_f_rr.pack(fill="x", pady=(0, 10))
        self._bind_numpad(self.e_f_rr, "Ref Rate")
        self.btn_f_save: ttk.Button = ttk.Button(
            rf,
            text="Calc & Save",
            style="Primary.TButton",
            state="disabled",
            command=self.act_f_save,
        )
        self.btn_f_save.pack(fill="x", side="bottom")

    # --- Helpers ---
    def _mk_card(self, p: ttk.Frame, t: str, c: str) -> ttk.Label:
        frm = ttk.Frame(p, style="Card.TFrame", padding=5)
        frm.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Label(frm, text=t, font=("Segoe UI", 9, "bold"), foreground="gray").pack(
            anchor="w"
        )
        l = ttk.Label(frm, text="0.00", font=("Consolas", 18, "bold"), foreground=c)
        l.pack(anchor="w")
        return l

    def _bind_numpad(self, w: ttk.Entry, t: str) -> None:
        w.bind("<Button-1>", lambda e: self._show_numpad(w, t))

    def _show_numpad(self, w: ttk.Entry, t: str) -> str:
        # --- FIX: CALL SINGLETON METHOD ---
        # Instead of creating a new instance, we call .show() on the existing self.numpad
        self.numpad.show(w, t)
        return "break"

    def show_page(self, k: str) -> None:
        for n, f in self.pages.items():
            if n == k:
                f.pack(fill="both", expand=True)
                if n == "history":
                    self.act_hist_ref()
                if n in ["temp", "press", "flow"]:
                    self._ref_combo(n.upper())
            else:
                f.pack_forget()

    def _init_logic(self) -> None:
        self.cmb_p["values"] = self.ctrl.get_ports()
        if self.cmb_p["values"]:
            self.cmb_p.current(0)

    # --- Actions ---
    def do_connect(self) -> None:
        if self.btn_conn["text"] == "Connect":
            p = self.cmb_p.get()
            if p:
                self.ctrl.connect_port(p)
        else:
            self.ctrl.disconnect_port()

    def act_test_start(self) -> None:
        if "Start" in self.btn_t_start["text"]:
            try:
                v = float(self.ent_tgt.get())
                if v <= 0:
                    raise ValueError
                self.ctrl.start_test(v)
                self.btn_t_start.config(text="Stop", style="Danger.TButton")
                self.btn_t_save.config(state="disabled")
                self.prog_bar["value"] = 0
                self.lbl_prog.config(text=f"0.00 / {v:.2f} L")
            except:
                messagebox.showerror("Err", "Invalid Target")
        else:
            self._stop_routine("User Stopped")

    def _stop_routine(self, r: str) -> None:
        self.ctrl.stop_test()
        self.btn_t_start.config(text="Start", style="Primary.TButton")
        self.btn_t_save.config(state="normal")
        messagebox.showinfo("Done", f"Reason: {r}")

    def act_test_save(self) -> None:
        try:
            im = float(self.ent_ini.get())
            fm = float(self.ent_fin.get())
            res = self.ctrl.finish_test(im, fm)

            msg = (
                f"Meter: {res['measured_volume']:.3f} L\n"
                f"Real: {res['actual_volume']:.3f} L\n"
                f"Error: {res['error_rate']:.2f}%"
            )
            if abs(res["error_rate"]) <= 2.0:
                msg += "\n[PASS]"
            else:
                msg += "\n[FAIL]"
            messagebox.showinfo("Result", msg)
            self.act_test_reset()
        except:
            messagebox.showerror("Err", "Invalid Inputs")

    def act_test_reset(self) -> None:
        self.ctrl.stop_test()
        self.ent_tgt.delete(0, tk.END)
        self.ent_ini.delete(0, tk.END)
        self.ent_fin.delete(0, tk.END)
        self.prog_bar["value"] = 0
        self.lbl_prog.config(text="0.00 / 0.00 L")
        self.btn_t_start.config(text="Start", style="Primary.TButton")
        self.btn_t_save.config(state="disabled")

    def act_hist_ref(self) -> None:
        for x in self.tree.get_children():
            self.tree.delete(x)
        for r in self.ctrl.get_history():
            # r: 0=id, 1=ts, 2=tgt, 3=ini, 4=fin, 5=meas, 6=act, 7=err, 8=af, 9=ap, 10=at, 11=st
            v = (r[1], r[2], r[3], r[4], r[5], r[6], f"{r[7]:.2f}%", r[11])
            self.tree.insert("", "end", iid=r[0], values=v)

    def act_hist_del(self) -> None:
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Del", f"Delete {len(sel)}?"):
            for i in sel:
                self.ctrl.delete_log(int(i))
            self.act_hist_ref()

    def _ref_combo(self, t: str) -> None:
        pts = self.ctrl.get_cal_list(t)
        self.cmap = getattr(self, "cmap", {})
        lst = []
        for p in pts:
            # 0=id, 2=raw, 3=ref
            s = f"ID:{p[0]} | Raw:{p[2]:.2f} | Ref:{p[3]:.2f}"
            lst.append(s)
            self.cmap[s] = p[0]
        self.refs_cal[t]["c"]["values"] = lst

    def act_cal_sel(self, t: str) -> None:
        w = self.refs_cal[t]
        s = w["c"].get()
        pid = self.cmap.get(s)
        if pid:
            pt = self.ctrl.get_cal_detail(pid)
            if pt:
                w["lr"].config(text=f"{pt[3]:.2f}")
                w["lg"].config(text=f"{pt[4]:.4f}")

    def act_cal_del(self, t: str) -> None:
        w = self.refs_cal[t]
        s = w["c"].get()
        pid = self.cmap.get(s)
        if pid and messagebox.askyesno("Confirm", "Delete?"):
            self.ctrl.del_cal_point(pid)
            self._ref_combo(t)
            w["c"].set("")
            w["lr"].config(text="-")
            w["lg"].config(text="-")

    def act_cal_save(self, t: str, k: str) -> None:
        try:
            e = getattr(self, f"ent_ref_{k}")
            rv = float(e.get())
            raw = 0.0
            if t == "TEMP":
                raw = self.ctrl.last_packet["temp"]
            elif t == "PRESS":
                raw = self.ctrl.last_packet["pressure"]

            self.ctrl.save_point(t, raw, rv)
            self._ref_combo(t)
            e.delete(0, tk.END)
            messagebox.showinfo("OK", "Saved")
        except:
            messagebox.showerror("Err", "Bad Input")

    def act_f_start(self) -> None:
        if not self.ctrl.is_connected():
            return messagebox.showerror("Err", "No Serial")
        self.ctrl.start_flow_cal()
        self.btn_f_save.config(state="disabled")
        self.l_f_rv.config(text="...")
        self.l_f_ra.config(text="...")

    def act_f_stop(self) -> None:
        v, r = self.ctrl.stop_flow_cal()
        self.l_f_rv.config(text=f"{v:.2f}")
        self.l_f_ra.config(text=f"{r:.2f}")
        self.btn_f_save.config(state="normal")

    def act_f_save(self) -> None:
        try:
            rv_s = self.e_f_rv.get().strip()
            rr_s = self.e_f_rr.get().strip()
            rv = float(rv_s) if rv_s else None
            rr = float(rr_s) if rr_s else None

            _, _, g = self.ctrl.calc_save_flow_gain(rv, rr)
            self._ref_combo("FLOW")
            self.e_f_rv.delete(0, tk.END)
            self.e_f_rr.delete(0, tk.END)
            messagebox.showinfo("OK", f"Gain: {g:.4f}")
        except Exception as e:
            messagebox.showerror("Err", str(e))

    # --- Loops ---
    def _loop_serial(self) -> None:
        try:
            while True:
                c, m = self.ctrl.queue_status().get_nowait()
                if c:
                    self.lbl_stat.config(text=f"OK: {m}", foreground="green")
                    self.btn_conn.config(text="Disconnect", style="Danger.TButton")
                else:
                    self.lbl_stat.config(text=f"Err: {m}", foreground="red")
                    self.btn_conn.config(text="Connect", style="Primary.TButton")
                    self.act_test_reset()
        except queue.Empty:
            pass

        try:
            while True:
                typ, dat = self.ctrl.queue_data().get_nowait()
                if typ == "DATA":
                    res = self.ctrl.ingest_packet(dat)
                    self._update_ui_data(res)
        except queue.Empty:
            pass

        self.after(100, self._loop_serial)

    def _loop_sensor(self) -> None:
        self.ctrl.trigger_poll()
        self.after(500, self._loop_sensor)

    def _update_ui_data(self, d: Dict[str, Any]) -> None:
        self.card_flow.config(text=f"{d['flow']:.2f}")
        self.card_pres.config(text=f"{d['press']:.2f}")
        self.card_temp.config(text=f"{d['temp']:.2f}")

        if hasattr(self, "lbl_live_temp"):
            self.lbl_live_temp.config(text=f"{d['raw_temp']:.2f}")
        if hasattr(self, "lbl_live_press"):
            self.lbl_live_press.config(text=f"{d['raw_press']:.2f}")

        if self.ctrl.flag_testing:
            tgt = self.ctrl.test_target_vol
            acc = d["accum_vol"]
            if tgt > 0:
                p = (acc / tgt) * 100
                self.prog_bar["value"] = min(p, 100)
                self.lbl_prog.config(text=f"{acc:.2f} / {tgt:.2f} L")
                if d["target_hit"]:
                    self._stop_routine("Target Hit")
