import tkinter as tk
from tkinter import ttk, messagebox
import statistics
import queue
from database import DatabaseManager
from calibration_manager import CalibrationManager
from serial_worker import SerialWorker


class WaterMeterAppTk(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Portable WMTK Proto (Tkinter)")
        self.geometry("800x480")
        self.resizable(False, False)

        # --- Logic & Models ---
        self.db = DatabaseManager()
        self.serial = SerialWorker()
        self.calib_mgr = CalibrationManager(self.db)

        # --- State Variables ---
        self.is_testing = False
        self.is_calibrating_flow = False
        self.target_volume = 0.0

        # Differential Accumulators
        self.last_process_raw_vol = 0.0
        self.accumulated_corrected_vol = 0.0

        # Data Buffers
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }
        self.calib_flow_buffer = []
        self.latest_raw_data = {
            "flow_rate": 0.0,
            "pressure": 0.0,
            "temp": 0.0,
            "total_volume": 0.0,
        }

        # --- GUI Construction ---
        self._build_ui()
        self._init_logic()

        # --- Start Loops ---
        self.after(100, self._process_serial_queues)  # Check incoming data
        self.after(500, self._poll_sensor_routine)  # Send commands

    def _build_ui(self):
        # 1. Main Layout: Header (Top) + Body (Bottom)
        header_frame = ttk.LabelFrame(self, text="Connection", padding=5)
        header_frame.pack(side="top", fill="x", padx=5, pady=5)

        # Header Content
        ttk.Label(header_frame, text="Port:").pack(side="left", padx=5)
        self.cmb_port = ttk.Combobox(header_frame, width=20)
        self.cmb_port.pack(side="left", padx=5)

        self.btn_connect = ttk.Button(
            header_frame, text="Connect", command=self.toggle_connection
        )
        self.btn_connect.pack(side="left", padx=5)

        self.lbl_status = ttk.Label(
            header_frame, text="Status: Disconnected", foreground="red"
        )
        self.lbl_status.pack(side="right", padx=10)

        # 2. Body: Sidebar (Left) + Content (Right)
        body_frame = ttk.Frame(self)
        body_frame.pack(side="top", fill="both", expand=True, padx=5, pady=0)

        sidebar = ttk.Frame(body_frame, width=150, relief="sunken", borderwidth=1)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)

        # Navigation Buttons
        ttk.Button(
            sidebar, text="Test Mode", command=lambda: self.show_page("test")
        ).pack(fill="x", pady=2)
        ttk.Button(
            sidebar, text="Temp Calibration", command=lambda: self.show_page("temp")
        ).pack(fill="x", pady=2)
        ttk.Button(
            sidebar, text="Press Calibration", command=lambda: self.show_page("press")
        ).pack(fill="x", pady=2)
        ttk.Button(
            sidebar, text="Flow Calibration", command=lambda: self.show_page("flow")
        ).pack(fill="x", pady=2)

        # Content Area
        self.content_area = ttk.Frame(body_frame)
        self.content_area.pack(side="left", fill="both", expand=True, padx=10)

        # Initialize Pages
        self.pages = {}

        # -- Create Page Frames --
        self._create_test_page()
        self._create_temp_page()
        self._create_press_page()
        self._create_flow_page()

        self.show_page("test")

    def _create_test_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["test"] = p

        # Input Area
        f_inputs = ttk.Frame(p)
        f_inputs.pack(fill="x", pady=10)

        # Volume Target
        ttk.Label(f_inputs, text="Target Volume (L):").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.ent_test_vol = ttk.Entry(f_inputs)
        self.ent_test_vol.grid(row=0, column=1, padx=5, pady=5)

        # Init Meter
        ttk.Label(f_inputs, text="Initial Meter (m3):").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        self.ent_test_init = ttk.Entry(f_inputs)
        self.ent_test_init.grid(row=1, column=1, padx=5, pady=5)

        # Final Meter
        ttk.Label(f_inputs, text="Final Meter (m3):").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )
        self.ent_test_final = ttk.Entry(f_inputs)
        self.ent_test_final.grid(row=2, column=1, padx=5, pady=5)

        # Buttons
        f_btns = ttk.Frame(p)
        f_btns.pack(fill="x", pady=5)
        self.btn_test_start = ttk.Button(
            f_btns, text="Start", command=self.handle_test_button
        )
        self.btn_test_start.pack(side="left", padx=5)

        self.btn_test_finish = ttk.Button(
            f_btns,
            text="Finish (Save)",
            state="disabled",
            command=self.save_test_result,
        )
        self.btn_test_finish.pack(side="left", padx=5)

        ttk.Button(f_btns, text="Reset", command=self.reset_test_ui).pack(
            side="right", padx=5
        )

        # Progress
        self.pb_test = ttk.Progressbar(p, orient="horizontal", mode="determinate")
        self.pb_test.pack(fill="x", pady=10)

        # Digital Displays (Sensor Data)
        f_lcd = ttk.LabelFrame(p, text="Live Readings")
        f_lcd.pack(fill="x", pady=5)

        # Flow
        ttk.Label(f_lcd, text="Flow (L/h):").grid(row=0, column=0, padx=10)
        self.lbl_flow_val = ttk.Label(
            f_lcd, text="0.00", font=("Courier", 16, "bold"), foreground="blue"
        )
        self.lbl_flow_val.grid(row=1, column=0, padx=10)

        # Pressure
        ttk.Label(f_lcd, text="Pressure (Bar):").grid(row=0, column=1, padx=10)
        self.lbl_press_val = ttk.Label(
            f_lcd, text="0.00", font=("Courier", 16, "bold"), foreground="green"
        )
        self.lbl_press_val.grid(row=1, column=1, padx=10)

        # Temp
        ttk.Label(f_lcd, text="Temp (°C):").grid(row=0, column=2, padx=10)
        self.lbl_temp_val = ttk.Label(
            f_lcd, text="0.00", font=("Courier", 16, "bold"), foreground="red"
        )
        self.lbl_temp_val.grid(row=1, column=2, padx=10)

    def _create_temp_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["temp"] = p

        ttk.Label(p, text="Temperature Calibration", font=("Arial", 12, "bold")).pack(
            pady=10
        )

        # History
        f_hist = ttk.Frame(p)
        f_hist.pack(fill="x", pady=5)
        ttk.Label(f_hist, text="History:").pack(side="left")
        self.cmb_cal_temp = ttk.Combobox(f_hist, state="readonly", width=40)
        self.cmb_cal_temp.pack(side="left", padx=5)
        self.cmb_cal_temp.bind(
            "<<ComboboxSelected>>",
            lambda e: self.load_cal_details(
                self.cmb_cal_temp, self.lbl_temp_cal_ref, self.lbl_temp_cal_gain
            ),
        )
        ttk.Button(
            f_hist,
            text="Delete",
            command=lambda: self.delete_calibration(
                self.cmb_cal_temp, "TEMP", self.lbl_temp_cal_ref, self.lbl_temp_cal_gain
            ),
        ).pack(side="left")

        # Details
        f_det = ttk.LabelFrame(p, text="Selected Point Details")
        f_det.pack(fill="x", pady=5)
        ttk.Label(f_det, text="Ref:").pack(side="left", padx=5)
        self.lbl_temp_cal_ref = ttk.Label(f_det, text="-")
        self.lbl_temp_cal_ref.pack(side="left", padx=5)
        ttk.Label(f_det, text="Gain:").pack(side="left", padx=5)
        self.lbl_temp_cal_gain = ttk.Label(f_det, text="-")
        self.lbl_temp_cal_gain.pack(side="left", padx=5)

        # New Calibration
        f_new = ttk.LabelFrame(p, text="New Calibration Point")
        f_new.pack(fill="x", pady=10)

        ttk.Label(f_new, text="Current Sensor Value:").grid(row=0, column=0, sticky="e")
        self.lbl_temp_live_cal = ttk.Label(f_new, text="0.00", font=("Courier", 12))
        self.lbl_temp_live_cal.grid(row=0, column=1, sticky="w")

        ttk.Label(f_new, text="Actual Reference Value:").grid(
            row=1, column=0, sticky="e"
        )
        self.ent_temp_ref = ttk.Entry(f_new)
        self.ent_temp_ref.grid(row=1, column=1, sticky="w")

        ttk.Button(
            f_new, text="Save / Set", command=lambda: self.save_generic_cal("TEMP")
        ).grid(row=2, column=1, pady=10)

    def _create_press_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["press"] = p

        ttk.Label(p, text="Pressure Calibration", font=("Arial", 12, "bold")).pack(
            pady=10
        )

        # History
        f_hist = ttk.Frame(p)
        f_hist.pack(fill="x", pady=5)
        ttk.Label(f_hist, text="History:").pack(side="left")
        self.cmb_cal_press = ttk.Combobox(f_hist, state="readonly", width=40)
        self.cmb_cal_press.pack(side="left", padx=5)
        self.cmb_cal_press.bind(
            "<<ComboboxSelected>>",
            lambda e: self.load_cal_details(
                self.cmb_cal_press, self.lbl_press_cal_ref, self.lbl_press_cal_gain
            ),
        )
        ttk.Button(
            f_hist,
            text="Delete",
            command=lambda: self.delete_calibration(
                self.cmb_cal_press,
                "PRESS",
                self.lbl_press_cal_ref,
                self.lbl_press_cal_gain,
            ),
        ).pack(side="left")

        # Details
        f_det = ttk.LabelFrame(p, text="Selected Point Details")
        f_det.pack(fill="x", pady=5)
        ttk.Label(f_det, text="Ref:").pack(side="left", padx=5)
        self.lbl_press_cal_ref = ttk.Label(f_det, text="-")
        self.lbl_press_cal_ref.pack(side="left", padx=5)
        ttk.Label(f_det, text="Gain:").pack(side="left", padx=5)
        self.lbl_press_cal_gain = ttk.Label(f_det, text="-")
        self.lbl_press_cal_gain.pack(side="left", padx=5)

        # New Calibration
        f_new = ttk.LabelFrame(p, text="New Calibration Point")
        f_new.pack(fill="x", pady=10)

        ttk.Label(f_new, text="Current Sensor Value:").grid(row=0, column=0, sticky="e")
        self.lbl_press_live_cal = ttk.Label(f_new, text="0.00", font=("Courier", 12))
        self.lbl_press_live_cal.grid(row=0, column=1, sticky="w")

        ttk.Label(f_new, text="Actual Reference Value:").grid(
            row=1, column=0, sticky="e"
        )
        self.ent_press_ref = ttk.Entry(f_new)
        self.ent_press_ref.grid(row=1, column=1, sticky="w")

        ttk.Button(
            f_new, text="Save / Set", command=lambda: self.save_generic_cal("PRESS")
        ).grid(row=2, column=1, pady=10)

    def _create_flow_page(self):
        p = ttk.Frame(self.content_area)
        self.pages["flow"] = p

        ttk.Label(p, text="Flow Sensor Calibration", font=("Arial", 12, "bold")).pack(
            pady=5
        )

        # History
        f_hist = ttk.Frame(p)
        f_hist.pack(fill="x", pady=5)
        self.cmb_cal_flow = ttk.Combobox(f_hist, state="readonly", width=40)
        self.cmb_cal_flow.pack(side="left", padx=5)
        self.cmb_cal_flow.bind(
            "<<ComboboxSelected>>",
            lambda e: self.load_cal_details(
                self.cmb_cal_flow, self.lbl_flow_cal_ref, self.lbl_flow_cal_gain
            ),
        )
        ttk.Button(
            f_hist,
            text="Delete",
            command=lambda: self.delete_calibration(
                self.cmb_cal_flow, "FLOW", self.lbl_flow_cal_ref, self.lbl_flow_cal_gain
            ),
        ).pack(side="left")

        # Details
        f_det = ttk.LabelFrame(p, text="Selected Point Details")
        f_det.pack(fill="x", pady=5)
        ttk.Label(f_det, text="Ref:").pack(side="left")
        self.lbl_flow_cal_ref = ttk.Label(f_det, text="-")
        self.lbl_flow_cal_ref.pack(side="left", padx=5)
        ttk.Label(f_det, text="Gain:").pack(side="left")
        self.lbl_flow_cal_gain = ttk.Label(f_det, text="-")
        self.lbl_flow_cal_gain.pack(side="left", padx=5)

        # Process
        f_proc = ttk.LabelFrame(p, text="Calibration Process")
        f_proc.pack(fill="x", pady=10)

        self.btn_flow_cal_start = ttk.Button(
            f_proc, text="Start Flow", command=self.start_flow_cal
        )
        self.btn_flow_cal_start.pack(side="left", padx=5, pady=5)

        self.btn_flow_cal_stop = ttk.Button(
            f_proc, text="Stop Flow", command=self.stop_flow_cal
        )
        self.btn_flow_cal_stop.pack(side="left", padx=5, pady=5)

        # Save
        f_save = ttk.Frame(p)
        f_save.pack(fill="x", pady=5)
        ttk.Label(f_save, text="Sensor Total Volume:").grid(row=0, column=0, sticky="e")
        self.lbl_flow_raw_vol = ttk.Label(f_save, text="0.00")
        self.lbl_flow_raw_vol.grid(row=0, column=1, sticky="w")

        ttk.Label(f_save, text="Actual Volume (Ref):").grid(row=1, column=0, sticky="e")
        self.ent_flow_ref = ttk.Entry(f_save)
        self.ent_flow_ref.grid(row=1, column=1, sticky="w")

        self.btn_flow_save = ttk.Button(
            f_save,
            text="Finish & Save",
            state="disabled",
            command=self.save_flow_calibration,
        )
        self.btn_flow_save.grid(row=2, column=1, pady=5)

    def show_page(self, page_name):
        for name, frame in self.pages.items():
            if name == page_name:
                frame.pack(fill="both", expand=True)
                # Refresh combos when entering page
                if name == "temp":
                    self.refresh_cal_combo(self.cmb_cal_temp, "TEMP")
                if name == "press":
                    self.refresh_cal_combo(self.cmb_cal_press, "PRESS")
                if name == "flow":
                    self.refresh_cal_combo(self.cmb_cal_flow, "FLOW")
            else:
                frame.pack_forget()

    def _init_logic(self):
        self.refresh_ports()

    def refresh_ports(self):
        ports = SerialWorker.get_available_ports()
        self.cmb_port["values"] = ports
        if ports:
            self.cmb_port.current(0)

    # --- Connection & Loops ---

    def toggle_connection(self):
        if self.btn_connect["text"] == "Connect":
            port = self.cmb_port.get()
            if not port:
                return
            self.serial.connect_serial(port)
        else:
            self.serial.disconnect_serial()

    def _process_serial_queues(self):
        # 1. Check Status Queue
        try:
            while True:
                connected, msg = self.serial.status_queue.get_nowait()
                if connected:
                    self.lbl_status.config(text=f"Status: {msg}", foreground="green")
                    self.btn_connect.config(text="Disconnect")
                else:
                    self.lbl_status.config(text=f"Status: {msg}", foreground="red")
                    self.btn_connect.config(text="Connect")
                    self.is_testing = False
                    self.is_calibrating_flow = False
                    self.btn_test_start.config(text="Start")
                    self.btn_test_finish.config(state="disabled")
        except queue.Empty:
            pass

        # 2. Check Data/Response Queue
        try:
            while True:
                item = self.serial.output_queue.get_nowait()
                msg_type = item[0]
                if msg_type == "DATA":
                    self.on_sensor_data(item[1])
                elif msg_type == "RESP":
                    # print(f"Response: {item[1]} -> {item[2]}")
                    pass
        except queue.Empty:
            pass

        self.after(100, self._process_serial_queues)

    def _poll_sensor_routine(self):
        # Only poll if connected AND NOT in streaming mode (Testing/Flow Cal)
        if (
            self.serial.is_connected()
            and not self.is_testing
            and not self.is_calibrating_flow
        ):
            self.serial.send_command("{D?}")
        self.after(500, self._poll_sensor_routine)

    # --- Data Processing ---

    def on_sensor_data(self, raw_data):
        self.latest_raw_data = raw_data

        raw_flow = raw_data.get("flow_rate", 0.0)
        raw_press = raw_data.get("pressure", 0.0)
        raw_temp = raw_data.get("temp", 0.0)
        current_total_raw_vol = raw_data.get("total_volume", 0.0)

        # Corrections
        corr_temp = self.calib_mgr.get_corrected_value("TEMP", raw_temp)
        corr_press = self.calib_mgr.get_corrected_value("PRESS", raw_press)
        flow_gain = self.calib_mgr.get_interpolated_gain("FLOW", raw_flow)
        corr_flow = raw_flow * flow_gain

        # Logic for Volume Correction (Delta Accumulation)
        delta_raw = current_total_raw_vol - self.last_process_raw_vol
        if delta_raw < 0:
            delta_raw = current_total_raw_vol  # Reset detected

        delta_corr = delta_raw * flow_gain

        if self.is_testing or self.is_calibrating_flow:
            self.accumulated_corrected_vol += delta_corr
            display_vol = self.accumulated_corrected_vol
        else:
            display_vol = current_total_raw_vol * flow_gain

        self.last_process_raw_vol = current_total_raw_vol

        # Update UI
        self.lbl_flow_val.config(text=f"{corr_flow:.2f}")
        self.lbl_press_val.config(text=f"{corr_press:.2f}")
        self.lbl_temp_val.config(text=f"{corr_temp:.2f}")

        # Update Cal Page Live Views
        self.lbl_temp_live_cal.config(text=f"{raw_temp:.2f}")
        self.lbl_press_live_cal.config(text=f"{raw_press:.2f}")

        # Testing Logic
        if self.is_testing:
            self.current_session_data["flow_rate"].append(corr_flow)
            self.current_session_data["pressure"].append(corr_press)
            self.current_session_data["temp"].append(corr_temp)
            self.current_session_data["last_total_volume"] = (
                self.accumulated_corrected_vol
            )

            if self.target_volume > 0:
                pct = (self.accumulated_corrected_vol / self.target_volume) * 100
                self.pb_test["value"] = min(pct, 100)

                if self.accumulated_corrected_vol >= self.target_volume:
                    self.force_stop_test("Target Volume Reached")

        # Flow Cal Buffer
        if self.is_calibrating_flow:
            self.calib_flow_buffer.append(raw_flow)

    # --- Test Logic ---
    def handle_test_button(self):
        if self.btn_test_start["text"] == "Start":
            # Start
            try:
                self.target_volume = float(self.ent_test_vol.get())
                if self.target_volume <= 0:
                    raise ValueError
            except:
                messagebox.showerror("Error", "Invalid Target Volume")
                return

            self.is_testing = True
            self.current_session_data = {
                "flow_rate": [],
                "pressure": [],
                "temp": [],
                "last_total_volume": 0.0,
            }
            self.last_process_raw_vol = 0.0
            self.accumulated_corrected_vol = 0.0

            self.serial.send_command("{S:1}")
            self.serial.send_command("{B:1,1}")
            self.btn_test_start.config(text="Stop")
            self.btn_test_finish.config(state="disabled")
            self.pb_test["value"] = 0
        else:
            # Stop
            self.force_stop_test("User Stopped")

    def force_stop_test(self, reason):
        if not self.is_testing:
            return
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_testing = False
        self.btn_test_start.config(text="Start")
        self.btn_test_finish.config(state="normal")
        messagebox.showinfo(
            "Test Finished",
            f"Reason: {reason}\nVol: {self.accumulated_corrected_vol:.3f} L",
        )

    def save_test_result(self):
        try:
            final_meter = float(self.ent_test_final.get())
            init_meter = float(self.ent_test_init.get())
        except:
            messagebox.showerror("Error", "Invalid Meter Values")
            return

        measured_vol = final_meter - init_meter
        actual_vol = self.current_session_data["last_total_volume"]

        error_rate = 0.0
        if actual_vol > 0:
            error_rate = ((measured_vol - actual_vol) / actual_vol) * 100

        buff = self.current_session_data
        log_data = {
            "volume_target": self.target_volume,
            "initial_meter": init_meter,
            "final_meter": final_meter,
            "measured_volume": measured_vol,
            "actual_volume": actual_vol,
            "error_rate": round(error_rate, 2),
            "avg_flow_rate": round(statistics.mean(buff["flow_rate"] or [0]), 2),
            "avg_pressure": round(statistics.mean(buff["pressure"] or [0]), 2),
            "avg_temp": round(statistics.mean(buff["temp"] or [0]), 2),
            "status": "FINISHED",
        }
        self.db.insert_test_log(log_data)
        messagebox.showinfo("Saved", f"Error Rate: {error_rate:.2f}%")
        self.btn_test_finish.config(state="disabled")

    def reset_test_ui(self):
        self.force_stop_test("Reset")
        self.ent_test_vol.delete(0, tk.END)
        self.ent_test_init.delete(0, tk.END)
        self.ent_test_final.delete(0, tk.END)
        self.pb_test["value"] = 0

    # --- Calibration Logic ---

    def save_generic_cal(self, sensor_type):
        try:
            if sensor_type == "TEMP":
                ref_val = float(self.ent_temp_ref.get())
                raw_val = self.latest_raw_data["temp"]
                combo = self.cmb_cal_temp
            elif sensor_type == "PRESS":
                ref_val = float(self.ent_press_ref.get())
                raw_val = self.latest_raw_data["pressure"]
                combo = self.cmb_cal_press
            else:
                return

            self.db.upsert_calibration_point(sensor_type, raw_val, ref_val)
            self.refresh_cal_combo(combo, sensor_type)
            messagebox.showinfo("Success", f"{sensor_type} Point Saved!")
        except ValueError:
            messagebox.showerror("Error", "Invalid Reference Value")

    def start_flow_cal(self):
        if not self.serial.is_connected():
            messagebox.showerror("Error", "Not Connected")
            return
        self.is_calibrating_flow = True
        self.calib_flow_buffer = []
        self.last_process_raw_vol = 0.0
        self.accumulated_corrected_vol = 0.0

        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:1,1}")
        self.btn_flow_save.config(state="disabled")

    def stop_flow_cal(self):
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_calibrating_flow = False
        self.lbl_flow_raw_vol.config(text=f"{self.latest_raw_data['total_volume']:.2f}")
        self.btn_flow_save.config(state="normal")

    def save_flow_calibration(self):
        try:
            ref_vol = float(self.ent_flow_ref.get())
            raw_vol = self.latest_raw_data["total_volume"]
            if raw_vol <= 0:
                raise ValueError("Sensor Volume 0")

            target_gain = ref_vol / raw_vol
            avg_flow = (
                statistics.mean(self.calib_flow_buffer)
                if self.calib_flow_buffer
                else self.latest_raw_data["flow_rate"]
            )
            art_ref_flow = avg_flow * target_gain

            self.db.upsert_calibration_point("FLOW", avg_flow, art_ref_flow)
            self.refresh_cal_combo(self.cmb_cal_flow, "FLOW")
            messagebox.showinfo("Success", f"Flow Gain: {target_gain:.4f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_cal_combo(self, combo, sensor_type):
        pts = self.db.get_calibration_points(sensor_type)
        # Store ID in a parallel list or interpret from string.
        # Tkinter combos deal in strings. We'll store ID in a hidden dict map for simplicity.
        self.cal_map = getattr(self, "cal_map", {})

        display_vals = []
        for p in pts:
            # p: (id, sens_val, ref_val, gain, time)
            s = f"ID:{p[0]} | Ref:{p[2]:.2f} | Sens:{p[1]:.2f}"
            display_vals.append(s)
            self.cal_map[s] = p[0]  # Map string to ID

        combo["values"] = display_vals

    def load_cal_details(self, combo, lbl_ref, lbl_gain):
        sel = combo.get()
        if not sel:
            return
        pid = self.cal_map.get(sel)
        if not pid:
            return

        pt = self.db.get_calibration_point_by_id(pid)
        if pt:
            lbl_ref.config(text=f"{pt[2]:.2f}")
            lbl_gain.config(text=f"{pt[3]:.4f}")

    def delete_calibration(self, combo, s_type, lbl_ref, lbl_gain):
        sel = combo.get()
        if not sel:
            return
        pid = self.cal_map.get(sel)
        if not pid:
            return

        if messagebox.askyesno("Confirm", "Delete this point?"):
            self.db.delete_calibration_point(pid)
            self.refresh_cal_combo(combo, s_type)
            lbl_ref.config(text="-")
            lbl_gain.config(text="-")
            combo.set("")


if __name__ == "__main__":
    app = WaterMeterAppTk()
    app.mainloop()
