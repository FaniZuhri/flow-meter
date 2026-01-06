import tkinter as tk
from tkinter import ttk, messagebox
import os
import queue
import math

# Imports from other files
from controller import MeasurementEngine
from ui_styles import apply_theme
from ui_numpad import TouchNumpad


class WaterMeterAppTk(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- Window ---
        self.title("Portable WMTK Proto")
        self.geometry("800x480")
        self.resizable(False, False)

        # --- Initialize Engine ---
        self.engine = MeasurementEngine()

        # --- Setup UI ---
        apply_theme(self)

        self.logo_img = None
        self._load_assets()

        self._build_ui()
        self._init_logic()

        # --- Start Loops ---
        self.after(100, self._process_serial_queues)
        self.after(500, self._poll_sensor_routine)

    def _load_assets(self):
        """Loads and stretches logo."""
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                src_img = tk.PhotoImage(file=logo_path)
                TARGET_WIDTH = 100
                orig_w = src_img.width()
                common_divisor = math.gcd(TARGET_WIDTH, orig_w)
                zoom_factor = TARGET_WIDTH // common_divisor
                subsample_factor = orig_w // common_divisor

                if zoom_factor > 10:
                    simple_factor = int(orig_w / TARGET_WIDTH) or 1
                    self.logo_img = src_img.subsample(simple_factor)
                else:
                    self.logo_img = src_img.zoom(zoom_factor).subsample(
                        subsample_factor
                    )

                self.iconphoto(False, self.logo_img)
            except Exception as e:
                print(f"Error loading logo: {e}")

    def _build_ui(self):
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)

        # Sidebar
        sidebar = ttk.Frame(main_container, style="Sidebar.TFrame", width=160)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        f_header = ttk.Frame(sidebar, style="Sidebar.TFrame")
        f_header.pack(pady=(10, 5))

        if self.logo_img:
            ttk.Label(f_header, image=self.logo_img, style="Sidebar.TLabel").pack(
                side="top", pady=(0, 5)
            )

        ttk.Label(
            f_header,
            text="WMTK Proto",
            style="Sidebar.TLabel",
            font=("Segoe UI", 12, "bold"),
            justify="center",
        ).pack(side="top")

        f_nav = ttk.Frame(sidebar, style="Sidebar.TFrame")
        f_nav.pack(fill="x", pady=5)

        navs = [
            ("Test Mode", "test"),
            ("History Logs", "history"),
            ("Temp Calib", "temp"),
            ("Press Calib", "press"),
            ("Flow Calib", "flow"),
        ]

        for lbl, page in navs:
            ttk.Button(
                f_nav,
                text=lbl,
                style="Nav.TButton",
                command=lambda p=page: self.show_page(p),
            ).pack(fill="x", pady=1)

        ttk.Frame(sidebar, style="Sidebar.TFrame").pack(fill="both", expand=True)

        conn_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        conn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ttk.Label(
            conn_frame,
            text="Serial Port:",
            style="Sidebar.TLabel",
            font=("Segoe UI", 8),
        ).pack(anchor="w")
        self.cmb_port = ttk.Combobox(conn_frame, state="readonly", height=4)
        self.cmb_port.pack(fill="x", pady=(0, 5))

        self.btn_connect = ttk.Button(
            conn_frame,
            text="Connect",
            style="Primary.TButton",
            command=self.toggle_connection,
        )
        self.btn_connect.pack(fill="x")
        self.lbl_status = ttk.Label(
            conn_frame,
            text="Disconnected",
            style="Sidebar.TLabel",
            font=("Segoe UI", 8),
            foreground="red",
        )
        self.lbl_status.pack(pady=(2, 0))

        # Content Area
        self.content_area = ttk.Frame(main_container, padding=20)
        self.content_area.pack(side="left", fill="both", expand=True)

        self.pages = {}
        self._create_test_page()
        self._create_history_page()
        self._create_temp_page()
        self._create_press_page()
        self._create_flow_page()
        self.show_page("test")

    # --- TOUCH INPUT HELPER ---
    def bind_touch_numpad(self, widget, title="Input"):
        """Binds click event to open the custom numpad."""
        widget.bind("<Button-1>", lambda e: self._open_numpad(widget, title))

    def _open_numpad(self, widget, title):
        TouchNumpad(self, widget, title)
        # Return 'break' to prevent default focus behavior if necessary
        return "break"

    # --- PAGES ---

    def _create_test_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["test"] = p
        ttk.Label(p, text="Automated Test", style="Header.TLabel").pack(
            anchor="w", pady=(0, 10)
        )

        f_cards = ttk.Frame(p)
        f_cards.pack(fill="x", pady=0)
        self.lbl_flow_val = self._make_card(f_cards, "Flow Rate (L/h)", "#007BFF")
        self.lbl_press_val = self._make_card(f_cards, "Pressure (Bar)", "#28A745")
        self.lbl_temp_val = self._make_card(f_cards, "Temp (°C)", "#DC3545")

        f_form = ttk.Labelframe(p, text="Test Parameters", padding=15)
        f_form.pack(fill="x", pady=15)

        f_row1 = ttk.Frame(f_form)
        f_row1.pack(fill="x", anchor="w", pady=(0, 10))
        ttk.Label(
            f_row1, text="1. Target Volume (L):", font=("Segoe UI", 10, "bold")
        ).pack(side="left")
        self.ent_test_vol = ttk.Entry(f_row1, width=12)
        self.ent_test_vol.pack(side="left", padx=(5, 25))
        self.bind_touch_numpad(self.ent_test_vol, "Target Volume")  # <--- BINDING

        ttk.Label(f_row1, text="2. Init Meter (m³):").pack(side="left")
        self.ent_test_init = ttk.Entry(f_row1, width=12)
        self.ent_test_init.pack(side="left", padx=(5, 0))
        self.bind_touch_numpad(self.ent_test_init, "Initial Meter")  # <--- BINDING

        ttk.Separator(f_form, orient="horizontal").pack(fill="x", pady=(0, 10))

        f_row2 = ttk.Frame(f_form)
        f_row2.pack(fill="x", anchor="w")
        ttk.Label(f_row2, text="3. Final Meter (m³):").pack(side="left")
        self.ent_test_final = ttk.Entry(f_row2, width=12)
        self.ent_test_final.pack(side="left", padx=(5, 10))
        self.bind_touch_numpad(self.ent_test_final, "Final Meter")  # <--- BINDING

        ttk.Label(
            f_row2,
            text="(Input after test finishes)",
            foreground="gray",
            font=("Segoe UI", 9, "italic"),
        ).pack(side="left")

        f_actions = ttk.Frame(p)
        f_actions.pack(fill="x", pady=5)
        self.btn_test_start = ttk.Button(
            f_actions,
            text="Start Test",
            style="Primary.TButton",
            command=self.handle_test_button,
        )
        self.btn_test_start.pack(side="left", padx=(5, 0))
        self.btn_test_finish = ttk.Button(
            f_actions,
            text="Finish & Save",
            style="Primary.TButton",
            state="disabled",
            command=self.save_test_result,
        )
        self.btn_test_finish.pack(side="left", padx=5)
        ttk.Button(
            f_actions, text="Reset", style="Danger.TButton", command=self.reset_test_ui
        ).pack(side="right", padx=5)

        self.pb_test = ttk.Progressbar(
            p, style="Horizontal.TProgressbar", orient="horizontal", mode="determinate"
        )
        self.pb_test.pack(fill="x", pady=(10, 5), padx=5)
        self.lbl_test_progress = ttk.Label(
            p, text="0.00 / 0.00 L", font=("Segoe UI", 10, "bold"), foreground="#6c757d"
        )
        self.lbl_test_progress.pack(pady=(0, 10))

    def _create_history_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["history"] = p

        f_top = ttk.Frame(p)
        f_top.pack(fill="x", pady=(0, 10))
        ttk.Label(f_top, text="Test History Logs", style="Header.TLabel").pack(
            side="left"
        )

        ttk.Button(
            f_top,
            text="Delete Selected",
            style="Danger.TButton",
            command=self.delete_selected_log,
        ).pack(side="right", padx=5)
        ttk.Button(
            f_top, text="Refresh", style="Primary.TButton", command=self.refresh_history
        ).pack(side="right", padx=5)

        columns = (
            "id",
            "date",
            "target",
            "init",
            "final",
            "measured",
            "actual",
            "error",
            "status",
        )
        self.tree_hist = ttk.Treeview(
            p, columns=columns, show="headings", selectmode="extended"
        )

        headers = {
            "id": "ID",
            "date": "Timestamp",
            "target": "Target(L)",
            "init": "Init(m3)",
            "final": "Final(m3)",
            "measured": "Meter(L)",
            "actual": "Real(L)",
            "error": "Error(%)",
            "status": "Status",
        }
        widths = {
            "id": 40,
            "date": 140,
            "target": 70,
            "init": 70,
            "final": 70,
            "measured": 80,
            "actual": 80,
            "error": 70,
            "status": 80,
        }

        for col, text in headers.items():
            self.tree_hist.heading(col, text=text)
            self.tree_hist.column(col, width=widths[col], anchor="center")

        sb = ttk.Scrollbar(p, orient="vertical", command=self.tree_hist.yview)
        self.tree_hist.configure(yscroll=sb.set)

        self.tree_hist.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _make_card(self, parent, title, color):
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        card.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Label(
            card, text=title, font=("Segoe UI", 9, "bold"), foreground="gray"
        ).pack(anchor="w")
        lbl = ttk.Label(
            card, text="0.00", font=("Consolas", 18, "bold"), foreground=color
        )
        lbl.pack(anchor="w")
        return lbl

    def _create_temp_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["temp"] = p
        self._create_generic_cal_page(
            p,
            "Temperature Calibration",
            "TEMP",
            "°C",
            self.save_generic_cal,
            self.delete_calibration,
            "lbl_temp_live_cal",
            "ent_temp_ref",
        )

    def _create_press_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["press"] = p
        self._create_generic_cal_page(
            p,
            "Pressure Calibration",
            "PRESS",
            "Bar",
            self.save_generic_cal,
            self.delete_calibration,
            "lbl_press_live_cal",
            "ent_press_ref",
        )

    def _create_generic_cal_page(
        self,
        parent,
        title,
        sens_type,
        unit,
        save_cb,
        del_cb,
        live_lbl_attr,
        ref_ent_attr,
    ):
        ttk.Label(parent, text=title, style="Header.TLabel").pack(
            anchor="w", pady=(0, 15)
        )

        f_hist = ttk.Frame(parent)
        f_hist.pack(fill="x", pady=5)
        combo = ttk.Combobox(f_hist, state="readonly", width=35)
        combo.pack(side="left", padx=(0, 5))
        lbl_ref = ttk.Label(f_hist, text="Ref: -")
        lbl_ref.pack(side="left", padx=10)
        lbl_gain = ttk.Label(f_hist, text="Gain: -")
        lbl_gain.pack(side="left", padx=10)

        attr_map = {"TEMP": "cmb_cal_temp", "PRESS": "cmb_cal_press"}
        setattr(self, attr_map[sens_type], combo)

        self.cal_widgets = getattr(self, "cal_widgets", {})
        self.cal_widgets[sens_type] = {"combo": combo, "ref": lbl_ref, "gain": lbl_gain}

        combo.bind(
            "<<ComboboxSelected>>", lambda e, st=sens_type: self.load_cal_details(st)
        )
        ttk.Button(
            f_hist,
            text="Delete",
            style="Danger.TButton",
            command=lambda st=sens_type: del_cb(st),
        ).pack(side="right")

        f_cal = ttk.Labelframe(parent, text="New Calibration Point", padding=20)
        f_cal.pack(fill="x", pady=20)
        f_cal.columnconfigure(1, weight=1)

        ttk.Label(f_cal, text=f"Live Sensor Value ({unit}):").grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        lbl_live = ttk.Label(f_cal, text="0.00", font=("Consolas", 14, "bold"))
        lbl_live.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        setattr(self, live_lbl_attr, lbl_live)

        ttk.Label(f_cal, text=f"Actual Reference ({unit}):").grid(
            row=1, column=0, sticky="e", padx=5, pady=5
        )
        ent_ref = ttk.Entry(f_cal, width=15)
        ent_ref.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        setattr(self, ref_ent_attr, ent_ref)
        self.bind_touch_numpad(ent_ref, f"Ref {unit}")  # <--- BINDING

        ttk.Button(
            f_cal,
            text="Save Calibration Point",
            style="Primary.TButton",
            command=lambda st=sens_type: save_cb(st),
        ).grid(row=2, column=1, sticky="w", pady=15)

    def _create_flow_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["flow"] = p
        ttk.Label(p, text="Flow Sensor Calibration", style="Header.TLabel").pack(
            anchor="w", pady=(0, 15)
        )

        f_hist = ttk.Frame(p)
        f_hist.pack(fill="x", pady=5)
        self.cmb_cal_flow = ttk.Combobox(f_hist, state="readonly", width=30)
        self.cmb_cal_flow.pack(side="left", padx=(0, 5))
        self.lbl_flow_cal_ref = ttk.Label(f_hist, text="Ref: -")
        self.lbl_flow_cal_ref.pack(side="left", padx=5)
        self.lbl_flow_cal_gain = ttk.Label(f_hist, text="Gain: -")
        self.lbl_flow_cal_gain.pack(side="left", padx=5)

        self.cal_widgets = getattr(self, "cal_widgets", {})
        self.cal_widgets["FLOW"] = {
            "combo": self.cmb_cal_flow,
            "ref": self.lbl_flow_cal_ref,
            "gain": self.lbl_flow_cal_gain,
        }
        self.cmb_cal_flow.bind(
            "<<ComboboxSelected>>", lambda e: self.load_cal_details("FLOW")
        )
        ttk.Button(
            f_hist,
            text="Delete",
            style="Danger.TButton",
            command=lambda: self.delete_calibration("FLOW"),
        ).pack(side="right")

        f_main = ttk.Frame(p)
        f_main.pack(fill="both", expand=True, pady=10)

        f_ctrl = ttk.Labelframe(f_main, text="1. Capture Data", padding=15)
        f_ctrl.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.btn_flow_cal_start = ttk.Button(
            f_ctrl,
            text="Start Flow",
            style="Primary.TButton",
            command=self.start_flow_cal,
        )
        self.btn_flow_cal_start.pack(fill="x", pady=5)
        self.btn_flow_cal_stop = ttk.Button(
            f_ctrl, text="Stop Flow", style="Danger.TButton", command=self.stop_flow_cal
        )
        self.btn_flow_cal_stop.pack(fill="x", pady=5)

        ttk.Label(f_ctrl, text="Captured Raw Volume:").pack(anchor="w", pady=(15, 0))
        self.lbl_flow_raw_vol = ttk.Label(
            f_ctrl, text="0.00", font=("Consolas", 14, "bold"), foreground="gray"
        )
        self.lbl_flow_raw_vol.pack(anchor="w")
        ttk.Label(f_ctrl, text="Captured Avg Flow:").pack(anchor="w", pady=(5, 0))
        self.lbl_flow_avg_rate = ttk.Label(
            f_ctrl, text="0.00", font=("Consolas", 14, "bold"), foreground="#007BFF"
        )
        self.lbl_flow_avg_rate.pack(anchor="w")

        f_ref = ttk.Labelframe(f_main, text="2. Set Reference", padding=15)
        f_ref.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ttk.Label(f_ref, text="Option A: Ref Volume (L)").pack(anchor="w")
        self.ent_flow_ref = ttk.Entry(f_ref)
        self.ent_flow_ref.pack(fill="x", pady=(0, 10))
        self.bind_touch_numpad(self.ent_flow_ref, "Ref Volume")  # <--- BINDING

        ttk.Label(f_ref, text="Option B: Ref Flow Rate (L/h)").pack(anchor="w")
        self.ent_flow_rate_ref = ttk.Entry(f_ref)
        self.ent_flow_rate_ref.pack(fill="x", pady=(0, 15))
        self.bind_touch_numpad(self.ent_flow_rate_ref, "Ref Flow Rate")  # <--- BINDING

        self.btn_flow_save = ttk.Button(
            f_ref,
            text="Calculate & Save",
            style="Primary.TButton",
            state="disabled",
            command=self.save_flow_calibration,
        )
        self.btn_flow_save.pack(fill="x", side="bottom")

    def show_page(self, page_name):
        for name, frame in self.pages.items():
            if name == page_name:
                frame.pack(fill="both", expand=True)
                if name in ["temp", "press", "flow"]:
                    self.refresh_cal_combo(name.upper())
                if name == "history":
                    self.refresh_history()
            else:
                frame.pack_forget()

    def _init_logic(self):
        ports = self.engine.get_ports()
        self.cmb_port["values"] = ports
        if ports:
            self.cmb_port.current(0)

    # --- Communication Loops ---
    def toggle_connection(self):
        if self.btn_connect["text"] == "Connect":
            port = self.cmb_port.get()
            if port and self.engine.connect(port):
                pass
        else:
            self.engine.disconnect()

    def _process_serial_queues(self):
        try:
            while True:
                connected, msg = self.engine.get_status_queue().get_nowait()
                if connected:
                    self.lbl_status.config(text=f"Status: {msg}", foreground="green")
                    self.btn_connect.config(text="Disconnect", style="Danger.TButton")
                else:
                    self.lbl_status.config(text=f"Status: {msg}", foreground="red")
                    self.btn_connect.config(text="Connect", style="Primary.TButton")
                    self.btn_test_start.config(
                        text="Start Test", style="Primary.TButton"
                    )
                    self.btn_test_finish.config(state="disabled")
        except queue.Empty:
            pass

        try:
            while True:
                item = self.engine.get_output_queue().get_nowait()
                if item[0] == "DATA":
                    display_data = self.engine.process_incoming_data(item[1])
                    self.update_live_display(display_data)
        except queue.Empty:
            pass

        self.after(100, self._process_serial_queues)

    def _poll_sensor_routine(self):
        self.engine.send_poll_command()
        self.after(500, self._poll_sensor_routine)

    # --- UI Updates ---
    def update_live_display(self, data):
        self.lbl_flow_val.config(text=f"{data['flow']:.2f}")
        self.lbl_press_val.config(text=f"{data['press']:.2f}")
        self.lbl_temp_val.config(text=f"{data['temp']:.2f}")

        if hasattr(self, "lbl_temp_live_cal"):
            self.lbl_temp_live_cal.config(text=f"{data['raw_temp']:.2f}")
        if hasattr(self, "lbl_press_live_cal"):
            self.lbl_press_live_cal.config(text=f"{data['raw_press']:.2f}")

        if self.engine.is_testing:
            target = self.engine.target_volume
            accum = data["accum_vol"]
            if target > 0:
                pct = (accum / target) * 100
                self.pb_test["value"] = min(pct, 100)
                self.lbl_test_progress.config(text=f"{accum:.2f} / {target:.2f} L")
                if data["target_reached"]:
                    self.force_stop_test("Target Reached")

    # --- History Logic ---
    def refresh_history(self):
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)

        logs = self.engine.fetch_history()
        for log in logs:
            row_id = log[0]
            values = (
                log[0],
                log[1],
                log[2],
                log[3],
                log[4],
                log[5],
                log[6],
                f"{log[7]:.2f}%",
                log[11],
            )
            self.tree_hist.insert("", "end", iid=row_id, values=values)

    def delete_selected_log(self):
        selected = self.tree_hist.selection()
        if not selected:
            return

        if messagebox.askyesno("Confirm", f"Delete {len(selected)} logs?"):
            for row_id in selected:
                self.engine.delete_history_item(row_id)
            self.refresh_history()

    # --- Test Interactions ---
    def handle_test_button(self):
        if "Start" in self.btn_test_start["text"]:
            try:
                vol = float(self.ent_test_vol.get())
                if vol <= 0:
                    raise ValueError
                self.engine.start_test(vol)
                self.btn_test_start.config(text="Stop Test", style="Danger.TButton")
                self.btn_test_finish.config(state="disabled")
                self.pb_test["value"] = 0
                self.lbl_test_progress.config(text=f"0.00 / {vol:.2f} L")
            except:
                messagebox.showerror("Error", "Invalid Target Volume")
        else:
            self.force_stop_test("User Stopped")

    def force_stop_test(self, reason):
        self.engine.stop_test()
        self.btn_test_start.config(text="Start Test", style="Primary.TButton")
        self.btn_test_finish.config(state="normal")
        messagebox.showinfo("Test Finished", f"Reason: {reason}")

    def save_test_result(self):
        try:
            init_m = float(self.ent_test_init.get())
            final_m = float(self.ent_test_final.get())

            res = self.engine.finalize_test_results(init_m, final_m)

            msg = (
                f"Measured (Meter): {res['measured_volume']:.3f} L\n"
                f"Actual (System): {res['actual_volume']:.3f} L\n"
                f"Error Rate: {res['error_rate']:.2f}%"
            )
            if abs(res["error_rate"]) <= 2.0:
                msg += "\n\n[PASSED]"
            else:
                msg += "\n\n[FAILED]"

            messagebox.showinfo("Result", msg)
            self.reset_test_ui()

        except ValueError:
            messagebox.showerror("Error", "Invalid Meter Readings")

    def reset_test_ui(self):
        self.engine.stop_test()
        self.ent_test_vol.delete(0, tk.END)
        self.ent_test_init.delete(0, tk.END)
        self.ent_test_final.delete(0, tk.END)
        self.pb_test["value"] = 0
        self.lbl_test_progress.config(text="0.00 / 0.00 L")
        self.btn_test_start.config(text="Start Test", style="Primary.TButton")
        self.btn_test_finish.config(state="disabled")

    # --- Calibration Interactions ---
    def save_generic_cal(self, sensor_type):
        try:
            if sensor_type == "TEMP":
                ref = float(self.ent_temp_ref.get())
                raw = self.engine.latest_raw_data["temp"]
                ent_widget = self.ent_temp_ref
            elif sensor_type == "PRESS":
                ref = float(self.ent_press_ref.get())
                raw = self.engine.latest_raw_data["pressure"]
                ent_widget = self.ent_press_ref
            else:
                return

            self.engine.save_calibration(sensor_type, raw, ref)
            self.refresh_cal_combo(sensor_type)
            ent_widget.delete(0, tk.END)
            messagebox.showinfo("Success", "Point Saved!")
        except ValueError:
            messagebox.showerror("Error", "Invalid Value")

    def start_flow_cal(self):
        if not self.engine.is_connected():
            messagebox.showerror("Error", "Not Connected")
            return
        self.engine.start_flow_cal()
        self.btn_flow_save.config(state="disabled")
        self.lbl_flow_raw_vol.config(text="Recording...")
        self.lbl_flow_avg_rate.config(text="Recording...")

    def stop_flow_cal(self):
        raw_vol, avg_flow = self.engine.stop_flow_cal()
        self.lbl_flow_raw_vol.config(text=f"{raw_vol:.2f}")
        self.lbl_flow_avg_rate.config(text=f"{avg_flow:.2f}")
        self.btn_flow_save.config(state="normal")

    def save_flow_calibration(self):
        try:
            r_rate = self.ent_flow_rate_ref.get().strip()
            r_vol = self.ent_flow_ref.get().strip()

            ref_rate = float(r_rate) if r_rate else None
            ref_vol = float(r_vol) if r_vol else None

            avg, real_ref, gain = self.engine.calculate_and_save_flow_cal(
                ref_vol, ref_rate
            )

            self.refresh_cal_combo("FLOW")
            self.ent_flow_ref.delete(0, tk.END)
            self.ent_flow_rate_ref.delete(0, tk.END)
            messagebox.showinfo("Success", f"Gain: {gain:.4f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_cal_combo(self, sensor_type):
        pts = self.engine.get_cal_points(sensor_type)
        self.cal_map = getattr(self, "cal_map", {})
        display_vals = []
        for p in pts:
            s = f"ID:{p[0]} | Ref:{p[2]:.2f} | Sens:{p[1]:.2f}"
            display_vals.append(s)
            self.cal_map[s] = p[0]

        widgets = self.cal_widgets.get(sensor_type)
        if widgets:
            widgets["combo"]["values"] = display_vals

    def load_cal_details(self, sensor_type):
        widgets = self.cal_widgets.get(sensor_type)
        if not widgets:
            return
        sel = widgets["combo"].get()
        pid = self.cal_map.get(sel)
        if not pid:
            return
        pt = self.engine.get_cal_point_details(pid)
        if pt:
            widgets["ref"].config(text=f"{pt[2]:.2f}")
            widgets["gain"].config(text=f"{pt[3]:.4f}")

    def delete_calibration(self, sensor_type):
        widgets = self.cal_widgets.get(sensor_type)
        sel = widgets["combo"].get()
        pid = self.cal_map.get(sel)
        if pid and messagebox.askyesno("Confirm", "Delete this point?"):
            self.engine.delete_cal_point(pid)
            self.refresh_cal_combo(sensor_type)
            widgets["ref"].config(text="-")
            widgets["gain"].config(text="-")
            widgets["combo"].set("")
