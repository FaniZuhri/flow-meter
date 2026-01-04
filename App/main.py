import sys
import statistics
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer

# Import View and Model
from app_ui import Ui_MainWindow
from database import DatabaseManager
from serial_worker import SerialWorker
from calibration_manager import CalibrationManager


## @class WaterMeterApp
#  @brief Main Controller Class (Main Window) of the application.
#
#  This class serves as the central controller, connecting the business logic
#  (Database, Serial Communication, Calibration) with the user interface (View).
#  It manages the application state, handles user interactions, processes sensor data,
#  and updates the GUI in real-time.
#
#  @details
#  Key responsibilities include:
#  - Managing the connection to the microcontroller via SerialWorker.
#  - Handling the automated testing workflow (Start/Stop logic).
#  - Implementing differential volume correction to handle unstable flow rates.
#  - Managing sensor calibration (Temperature, Pressure, Flow).
#  - Displaying real-time sensor data on the dashboard.
class WaterMeterApp(QtWidgets.QMainWindow, Ui_MainWindow):

    ## @brief Constructor for the main application window.
    #  Initializes the UI, models, workers, state variables, and connections.
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # --- ALIASING UI COMPONENTS ---
        # Creating aliases to make code more readable and understandable.
        # Original names from Qt Designer are often generic (e.g. testInitDutCount_2).

        # 1. Temp Calibration Page
        self.ui_view_temp_ref = self.testInitDutCount_2  # View: Reference Value Display
        self.ui_view_temp_gain = self.display_cal_temp_gain  # View: Gain Factor Display

        # 2. Pressure Calibration Page
        self.ui_view_press_ref = (
            self.testInitDutCount_3
        )  # View: Reference Value Display
        self.ui_view_press_gain = (
            self.display_cal_press_gain
        )  # View: Gain Factor Display

        # 3. Flow Calibration Page
        self.ui_view_flow_ref = self.testLastDutCount_7  # View: Reference Value Display
        self.ui_view_flow_gain = self.testLastDutCount_6  # View: Gain Factor Display
        self.ui_set_flow_raw_vol = (
            self.testLastDutCount_8
        )  # Set: Last raw vol display for input reference
        self.ui_btn_flow_reset = self.testResetBtn_10  # Reset Button

        # --- Initialize Model, Worker, & Calibration ---
        self.db = DatabaseManager()
        self.serial = SerialWorker()
        self.calib_mgr = CalibrationManager(self.db)

        # --- Application State Variables ---
        self.is_testing = False
        self.is_calibrating_flow = False
        self.target_volume = 0.0

        # --- DIFFERENTIAL ACCUMULATORS (Crucial for Unstable Flow) ---
        # Tracks the Raw Volume value from the PREVIOUS packet to calculate delta.
        self.last_process_raw_vol = 0.0
        # Accumulates the Corrected Volume delta-by-delta.
        self.accumulated_corrected_vol = 0.0

        # Data Buffer (Stores CORRECTED data for Test session)
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }

        # Buffer specifically for RAW flow rate data during flow calibration
        self.calib_flow_buffer = []

        # Stores last RAW data snapshot
        self.latest_raw_data = {
            "flow_rate": 0.0,
            "pressure": 0.0,
            "temp": 0.0,
            "total_volume": 0.0,
        }

        # Stores last CORRECTED data (for display)
        self.latest_corrected_data = {
            "flow_rate": 0.0,
            "pressure": 0.0,
            "temp": 0.0,
            "total_volume": 0.0,
        }

        # --- Polling Timer ---
        # Used ONLY during IDLE state. During Testing, timer is stopped (Streaming Mode).
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.send_data_request)
        self.poll_timer.setInterval(500)

        # --- Setup ---
        self.init_ui_connections()
        self.init_serial_connections()
        self.refresh_ports()

        # Default UI State
        self.menuStackedWidget.setCurrentIndex(0)
        self.btn_test_finish.setEnabled(False)
        self.progress_bar_test.setValue(0)

    ## @brief Connects signals from UI widgets to controller methods.
    def init_ui_connections(self):
        # Header Connection
        self.btn_connect.clicked.connect(self.toggle_connection)

        # Sidebar Navigation
        self.btn_nav_test.clicked.connect(lambda: self.navigate_to(0))
        self.btn_nav_temp_cal.clicked.connect(lambda: self.navigate_to(1))
        self.btn_nav_press_cal.clicked.connect(lambda: self.navigate_to(2))
        self.btn_nav_flow_cal.clicked.connect(lambda: self.navigate_to(3))

        # Test Page Logic
        self.btn_test_start.clicked.connect(self.handle_test_button)
        self.btn_test_finish.clicked.connect(self.save_test_result)
        self.btn_test_reset.clicked.connect(self.reset_test_ui)

        # -- Temp Calibration --
        self.btn_cal_temp_save.clicked.connect(
            lambda: self.save_calibration_generic("TEMP")
        )
        # Delete data & clear alias views
        self.btn_cal_temp_delete.clicked.connect(
            lambda: self.delete_calibration(
                self.cmb_cal_temp_history,
                "TEMP",
                self.ui_view_temp_ref,
                self.ui_view_temp_gain,
            )
        )
        # Load details to alias views
        self.cmb_cal_temp_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_temp_history, self.ui_view_temp_ref, self.ui_view_temp_gain
            )
        )

        # -- Pressure Calibration --
        self.btn_cal_press_save.clicked.connect(
            lambda: self.save_calibration_generic("PRESS")
        )
        self.btn_cal_press_delete.clicked.connect(
            lambda: self.delete_calibration(
                self.cmb_cal_press_history,
                "PRESS",
                self.ui_view_press_ref,
                self.ui_view_press_gain,
            )
        )
        self.cmb_cal_press_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_press_history,
                self.ui_view_press_ref,
                self.ui_view_press_gain,
            )
        )

        # -- Flow Calibration --
        self.btn_cal_flow_start.clicked.connect(self.start_flow_cal)
        self.btn_cal_flow_stop.clicked.connect(self.stop_flow_cal)
        self.btn_cal_flow_save.clicked.connect(self.save_flow_calibration)
        self.btn_cal_flow_delete.clicked.connect(
            lambda: self.delete_calibration(
                self.cmb_cal_flow_history,
                "FLOW",
                self.ui_view_flow_ref,
                self.ui_view_flow_gain,
            )
        )
        self.cmb_cal_flow_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_flow_history, self.ui_view_flow_ref, self.ui_view_flow_gain
            )
        )

        # Reset Logic Flow
        self.ui_btn_flow_reset.clicked.connect(self.reset_flow_cal_ui)

    ## @brief Connects signals from SerialWorker to controller methods.
    def init_serial_connections(self):
        self.serial.connection_status_signal.connect(self.on_connection_changed)
        self.serial.data_received_signal.connect(self.on_sensor_data)
        self.serial.response_received_signal.connect(self.on_command_response)

    ## @brief Populates port dropdown with available serial ports.
    def refresh_ports(self):
        self.cmb_port_select.clear()
        self.cmb_port_select.addItems(SerialWorker.get_available_ports())

    ## @brief Toggles Connect/Disconnect button.
    def toggle_connection(self):
        if self.btn_connect.text() == "Connect":
            port = self.cmb_port_select.currentText()
            if not port:
                return
            self.serial.connect_serial(port)
        else:
            self.serial.disconnect_serial()

    ## @brief Callback for connection status changes.
    #  @param connected Connection status (True/False).
    #  @param message Status message.
    def on_connection_changed(self, connected, message):
        self.statusbar.showMessage(f"Serial: {message}")
        if connected:
            self.btn_connect.setText("Disconnect")
            # Start polling timer when idle so sensor data is displayed
            self.poll_timer.start()
        else:
            self.btn_connect.setText("Connect")
            self.poll_timer.stop()
            self.is_testing = False
            self.btn_test_start.setText("Start")
            self.btn_test_start.setEnabled(True)

    ## @brief Sends manual data request ({D?}).
    #  Only active during IDLE state (poll_timer active).
    def send_data_request(self):
        if self.serial.is_running:
            self.serial.send_command("{D?}")

    ## @brief UI Page Navigation.
    #  Automatically refreshes history dropdown based on the open page.
    def navigate_to(self, index):
        self.menuStackedWidget.setCurrentIndex(index)
        if index == 1:
            self.refresh_cal_combo(self.cmb_cal_temp_history, "TEMP")
        elif index == 2:
            self.refresh_cal_combo(self.cmb_cal_press_history, "PRESS")
        elif index == 3:
            self.refresh_cal_combo(self.cmb_cal_flow_history, "FLOW")

    ## @brief Main callback when sensor data is received from SerialWorker.
    #
    #  Logic Flow (Differential Integration):
    #  1. Calculate Delta Raw Volume (Current - Last).
    #  2. Calculate Delta Corrected Volume = Delta Raw * Gain(Current Flow).
    #  3. Accumulate Corrected Volume.
    #
    #  This ensures that volume accumulated at low flow is corrected with low-flow gain,
    #  and volume at high flow with high-flow gain, regardless of fluctuation.
    #
    #  @param raw_data Dictionary containing raw sensor data.
    def on_sensor_data(self, raw_data):
        self.latest_raw_data = raw_data

        raw_flow = raw_data.get("flow_rate", 0.0)
        raw_press = raw_data.get("pressure", 0.0)
        raw_temp = raw_data.get("temp", 0.0)

        # Raw Total Volume from MCU
        current_total_raw_vol = raw_data.get("total_volume", 0.0)

        # --- CORRECTION LOGIC ---
        # Temp & Pressure corrected normally
        corr_temp = self.calib_mgr.get_corrected_value("TEMP", raw_temp)
        corr_press = self.calib_mgr.get_corrected_value("PRESS", raw_press)

        # 1. Get Gain for Current Flow Rate
        flow_gain = self.calib_mgr.get_interpolated_gain("FLOW", raw_flow)

        # 2. Correct Flow Rate
        corr_flow = raw_flow * flow_gain

        # 3. Correct Volume (Differential Approach)
        # Calculate how much raw volume increased since last packet
        delta_raw_vol = current_total_raw_vol - self.last_process_raw_vol

        # Handle potential reset or negative delta (e.g., if MCU reset volume)
        if delta_raw_vol < 0:
            delta_raw_vol = (
                current_total_raw_vol  # Assume reset to 0, so delta is the whole value
            )

        # Apply current gain ONLY to the new volume increment
        delta_corr_vol = delta_raw_vol * flow_gain

        # Accumulate corrected volume
        # If not testing/calibrating, we just show corrected 'total' based on simple multiplication
        # to avoid infinite accumulation drift in IDLE mode.
        if self.is_testing or self.is_calibrating_flow:
            self.accumulated_corrected_vol += delta_corr_vol
            corr_vol_display = self.accumulated_corrected_vol
        else:
            # In IDLE mode, just show snapshot correction to keep it simple
            corr_vol_display = current_total_raw_vol * flow_gain

        # Update Last Processed Value
        self.last_process_raw_vol = current_total_raw_vol

        # Store Data
        self.latest_corrected_data = {
            "flow_rate": corr_flow,
            "pressure": corr_press,
            "temp": corr_temp,
            "total_volume": corr_vol_display,
        }

        # Update LCD Display
        self.lcd_flow.display(corr_flow)
        self.lcd_press.display(corr_press)
        self.lcd_temp.display(corr_temp)
        self.lcd_cal_temp_sensor.display(corr_temp)
        self.lcd_cal_press_sensor.display(corr_press)

        # Test Logic
        if self.is_testing:
            self.current_session_data["flow_rate"].append(corr_flow)
            self.current_session_data["pressure"].append(corr_press)
            self.current_session_data["temp"].append(corr_temp)

            # Update session volume with the ACCUMULATED corrected volume
            self.current_session_data["last_total_volume"] = (
                self.accumulated_corrected_vol
            )

            if self.target_volume > 0:
                progress = int(
                    (self.accumulated_corrected_vol / self.target_volume) * 100
                )
                self.progress_bar_test.setValue(min(progress, 100))
                self.statusbar.showMessage(
                    f"Testing: {self.accumulated_corrected_vol:.2f} / {self.target_volume:.2f} L"
                )

                # Auto-Stop
                if self.accumulated_corrected_vol >= self.target_volume:
                    self.force_stop_test("Target Volume Reached!")

        # Flow Calibration Buffer
        if self.is_calibrating_flow:
            self.calib_flow_buffer.append(raw_flow)

    def on_command_response(self, cmd_id, val):
        self.statusbar.showMessage(f"MCU Responded: {cmd_id} -> {val}", 3000)

    # --- TEST PAGE LOGIC ---

    def handle_test_button(self):
        if self.btn_test_start.text() == "Start":
            self.start_test()
        else:
            self.force_stop_test("User Stopped")

    ## @brief Starts the automated testing procedure.
    #  Sends command to MCU to reset and open valve.
    #  Polling timer is stopped because MCU will send streaming data.
    def start_test(self):
        if not self.serial.is_running:
            QtWidgets.QMessageBox.warning(self, "Error", "Serial not connected!")
            return

        try:
            vol_str = self.input_test_volume.toPlainText().strip()
            self.target_volume = float(vol_str)
            if self.target_volume <= 0:
                raise ValueError
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Input Error", "Please enter a valid Target Volume."
            )
            return

        self.is_testing = True
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }

        # RESET DIFFERENTIAL ACCUMULATORS
        self.last_process_raw_vol = 0.0  # Assuming MCU resets to 0 on {S:1}
        self.accumulated_corrected_vol = 0.0

        # STOP Polling
        self.poll_timer.stop()

        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:1,1}")
        self.btn_test_start.setText("Stop")
        self.btn_test_finish.setEnabled(False)
        self.progress_bar_test.setValue(0)
        self.statusbar.showMessage("Test Started (Streaming Mode)...")

    ## @brief Stops the testing procedure.
    #  Closes valve and reactivates polling timer.
    def force_stop_test(self, reason="Stopped"):
        if not self.is_testing:
            return
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_testing = False

        # RESUME Polling timer after stop (Idle Mode)
        self.poll_timer.start()

        self.btn_test_start.setText("Start")
        self.btn_test_finish.setEnabled(True)
        final_vol = self.current_session_data["last_total_volume"]
        QtWidgets.QMessageBox.information(
            self,
            "Info",
            f"Test Finished: {reason}\nRecorded Volume: {final_vol:.3f} Liters\nPlease input 'Final Meter Value'.",
        )

    ## @brief Saves test result to database and calculates Error Rate.
    def save_test_result(self):
        try:
            final_meter = float(self.input_test_final_meter.toPlainText().strip())
            init_str = self.input_test_init_meter.toPlainText().strip()
            init_meter = float(init_str) if init_str else 0.0
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Error", "Input Final Meter Value error!"
            )
            return

        measured_volume = final_meter - init_meter
        # Use accumulated corrected volume
        actual_volume = self.current_session_data["last_total_volume"]

        error_rate = 0.0
        if actual_volume > 0:
            error_rate = ((measured_volume - actual_volume) / actual_volume) * 100

        buff = self.current_session_data
        avg_flow = statistics.mean(buff["flow_rate"]) if buff["flow_rate"] else 0
        avg_press = statistics.mean(buff["pressure"]) if buff["pressure"] else 0
        avg_temp = statistics.mean(buff["temp"]) if buff["temp"] else 0

        log_data = {
            "volume_target": self.target_volume,
            "initial_meter": init_meter,
            "final_meter": final_meter,
            "measured_volume": measured_volume,
            "actual_volume": actual_volume,
            "error_rate": round(error_rate, 2),
            "avg_flow_rate": round(avg_flow, 2),
            "avg_pressure": round(avg_press, 2),
            "avg_temp": round(avg_temp, 2),
            "status": "FINISHED",
        }
        self.db.insert_test_log(log_data)

        # Show Short Report
        msg = (
            f"Data Saved!\n"
            f"Sys Vol (Corr): {actual_volume:.3f} L\n"
            f"Meter Vol: {measured_volume:.3f} L\n"
            f"Error: {error_rate:.2f} %"
        )
        if abs(error_rate) <= 2.0:
            msg += "\n[PASSED]"
        else:
            msg += "\n[FAILED]"
        QtWidgets.QMessageBox.information(self, "Result", msg)
        self.btn_test_finish.setEnabled(False)

    def reset_test_ui(self):
        if self.is_testing:
            self.force_stop_test("Reset")
        self.input_test_volume.clear()
        self.input_test_init_meter.clear()
        self.input_test_final_meter.clear()
        self.progress_bar_test.setValue(0)
        self.btn_test_finish.setEnabled(False)

    # --- CALIBRATION LOGIC ---

    ## @brief Saves single point calibration for Temp/Pressure.
    #  Uses the last RAW data stored in memory.
    def save_calibration_generic(self, sensor_type):
        if sensor_type == "TEMP":
            input_widget = self.input_cal_temp_ref
            raw_val = self.latest_raw_data["temp"]  # IMPORTANT: Use RAW
            combo = self.cmb_cal_temp_history
        elif sensor_type == "PRESS":
            input_widget = self.input_cal_press_ref
            raw_val = self.latest_raw_data["pressure"]  # IMPORTANT: Use RAW
            combo = self.cmb_cal_press_history
        else:
            return

        try:
            ref_val = float(input_widget.toPlainText().strip())
            self.db.upsert_calibration_point(sensor_type, raw_val, ref_val)
            self.refresh_cal_combo(combo, sensor_type)
            input_widget.clear()
            QtWidgets.QMessageBox.information(self, "Success", f"{sensor_type} Saved!")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid Reference Value!")

    # --- FLOW CALIBRATION LOGIC (SPECIAL) ---

    ## @brief Starts flow calibration session.
    #  Resets flow buffer and enters streaming mode.
    def start_flow_cal(self):
        if not self.serial.is_running:
            QtWidgets.QMessageBox.warning(self, "Error", "Serial not connected!")
            return
        self.is_calibrating_flow = True
        self.calib_flow_buffer = []

        # Reset Accumulators
        self.last_process_raw_vol = 0.0
        self.accumulated_corrected_vol = 0.0

        self.poll_timer.stop()
        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:1,1}")
        self.statusbar.showMessage("Flow Calibration Started...")

    def stop_flow_cal(self):
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_calibrating_flow = False
        self.poll_timer.start()
        self.statusbar.showMessage("Flow Calibration Stopped.")

        # For calibration reference, we usually want the RAW volume the sensor saw
        raw_vol_end = self.latest_raw_data["total_volume"]
        self.ui_set_flow_raw_vol.setText(f"{raw_vol_end:.2f}")

    ## @brief Saves flow calibration result.
    #  Calculates Gain = Ref Volume / Raw Volume.
    #  Gain is stored at the Average Flow Rate point during the session.
    def save_flow_calibration(self):
        try:
            ref_vol = float(self.input_cal_flow_ref.toPlainText().strip())
            raw_vol = self.latest_raw_data["total_volume"]
            if raw_vol <= 0:
                raise ValueError("Sensor Volume is 0")

            target_gain = ref_vol / raw_vol

            # Calculate average flow rate during calibration to determine operating point (X-Axis)
            if not self.calib_flow_buffer:
                avg_flow_rate = self.latest_raw_data["flow_rate"]
            else:
                avg_flow_rate = statistics.mean(self.calib_flow_buffer)

            # Calculate artificial reference flow value
            artificial_ref_flow = avg_flow_rate * target_gain

            self.db.upsert_calibration_point("FLOW", avg_flow_rate, artificial_ref_flow)
            self.refresh_cal_combo(self.cmb_cal_flow_history, "FLOW")

            self.input_cal_flow_ref.clear()
            self.ui_set_flow_raw_vol.clear()
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                f"Flow Calibrated!\nAvg Flow: {avg_flow_rate:.1f} L/h\nGain: {target_gain:.4f}",
            )
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Input Invalid: {e}")

    def reset_flow_cal_ui(self):
        self.btn_cal_flow_save.setEnabled(False)
        self.input_cal_flow_ref.clear()
        self.ui_set_flow_raw_vol.clear()
        self.ui_view_flow_gain.clear()

    # --- HELPERS ---

    ## @brief Populates dropdown with filtered calibration history.
    def refresh_cal_combo(self, combo_box, sensor_type):
        combo_box.clear()
        points = self.db.get_calibration_points(sensor_type)
        for p in points:
            # Clean Display: Ref & Sens
            text = f"Ref: {p[2]:.2f} | Sens: {p[1]:.2f}"
            combo_box.addItem(text, userData=p[0])  # Store ID in userData

    ## @brief Displays full details (Gain & Ref) when dropdown item is selected.
    #  Uses widget aliases (ref_display, gain_display) passed as arguments.
    def load_cal_details(self, combo, ref_display, gain_display):
        curr_id = combo.currentData()
        if not curr_id:
            # Clear if no selection
            ref_display.clear()
            gain_display.clear()
            return

        # Query full details from DB based on ID
        point = self.db.get_calibration_point_by_id(curr_id)
        if point:
            # point: (id, sensor_val, reference_value, gain_factor, timestamp)
            ref_val = point[2]
            gain_val = point[3]

            ref_display.setText(f"{ref_val:.2f}")
            gain_display.setText(f"{gain_val:.4f}")

    ## @brief Deletes selected calibration data.
    def delete_calibration(self, combo, sensor_type, ref_display, gain_display):
        id_to_del = combo.currentData()
        if not id_to_del:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete",
            "Delete this calibration point?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.db.delete_calibration_point(id_to_del)
            self.refresh_cal_combo(combo, sensor_type)
            # Clear details after delete
            ref_display.clear()
            gain_display.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WaterMeterApp()
    window.show()
    sys.exit(app.exec_())
