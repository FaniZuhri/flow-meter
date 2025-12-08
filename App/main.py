import sys
import statistics
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer

# Import View dan Model
from app_ui import Ui_MainWindow
from database import DatabaseManager
from serial_worker import SerialWorker
from calibration_manager import CalibrationManager


class WaterMeterApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # --- Inisialisasi Model, Worker, & Calibration ---
        self.db = DatabaseManager()
        self.serial = SerialWorker()
        self.calib_mgr = CalibrationManager(self.db)

        # --- Variabel State Aplikasi ---
        self.is_testing = False
        self.is_calibrating_flow = False
        self.target_volume = 0.0

        # Buffer data
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

        self.latest_corrected_data = {
            "flow_rate": 0.0,
            "pressure": 0.0,
            "temp": 0.0,
            "total_volume": 0.0,
        }

        # --- Timer Polling ---
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

    def init_ui_connections(self):
        self.btn_connect.clicked.connect(self.toggle_connection)

        self.btn_nav_test.clicked.connect(lambda: self.navigate_to(0))
        self.btn_nav_temp_cal.clicked.connect(lambda: self.navigate_to(1))
        self.btn_nav_press_cal.clicked.connect(lambda: self.navigate_to(2))
        self.btn_nav_flow_cal.clicked.connect(lambda: self.navigate_to(3))

        self.btn_test_start.clicked.connect(self.handle_test_button)
        self.btn_test_finish.clicked.connect(self.save_test_result)
        self.btn_test_reset.clicked.connect(self.reset_test_ui)

        # Temp Calibration
        self.btn_cal_temp_save.clicked.connect(
            lambda: self.save_calibration_generic("TEMP")
        )
        # Pass widget display (Ref & Gain) ke fungsi delete agar bisa dibersihkan
        self.btn_cal_temp_delete.clicked.connect(
            lambda: self.delete_calibration(
                self.cmb_cal_temp_history,
                "TEMP",
                self.testInitDutCount_2,
                self.display_cal_temp_gain,
            )
        )
        # Saat dropdown berubah, update Gain & Ref display
        self.cmb_cal_temp_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_temp_history,
                self.testInitDutCount_2,
                self.display_cal_temp_gain,
            )
        )

        # Pressure Calibration
        self.btn_cal_press_save.clicked.connect(
            lambda: self.save_calibration_generic("PRESS")
        )
        self.btn_cal_press_delete.clicked.connect(
            lambda: self.delete_calibration(
                self.cmb_cal_press_history,
                "PRESS",
                self.testInitDutCount_3,
                self.display_cal_press_gain,
            )
        )
        self.cmb_cal_press_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_press_history,
                self.testInitDutCount_3,
                self.display_cal_press_gain,
            )
        )

        # Flow Calibration
        self.btn_cal_flow_start.clicked.connect(self.start_flow_cal)
        self.btn_cal_flow_stop.clicked.connect(self.stop_flow_cal)
        self.btn_cal_flow_save.clicked.connect(self.save_flow_calibration)
        self.btn_cal_flow_delete.clicked.connect(
            lambda: self.delete_calibration(
                self.cmb_cal_flow_history,
                "FLOW",
                self.testLastDutCount_7,
                self.testLastDutCount_6,
            )
        )
        self.cmb_cal_flow_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_flow_history,
                self.testLastDutCount_7,
                self.testLastDutCount_6,
            )
        )

        if hasattr(self, "testResetBtn_10"):
            self.testResetBtn_10.clicked.connect(self.reset_flow_cal_ui)

    def init_serial_connections(self):
        self.serial.connection_status_signal.connect(self.on_connection_changed)
        self.serial.data_received_signal.connect(self.on_sensor_data)
        self.serial.response_received_signal.connect(self.on_command_response)

    def refresh_ports(self):
        self.cmb_port_select.clear()
        self.cmb_port_select.addItems(SerialWorker.get_available_ports())

    def toggle_connection(self):
        if self.btn_connect.text() == "Connect":
            port = self.cmb_port_select.currentText()
            if not port:
                return
            self.serial.connect_serial(port)
        else:
            self.serial.disconnect_serial()

    def on_connection_changed(self, connected, message):
        self.statusbar.showMessage(f"Serial: {message}")
        if connected:
            self.btn_connect.setText("Disconnect")
            self.poll_timer.start()
        else:
            self.btn_connect.setText("Connect")
            self.poll_timer.stop()
            self.is_testing = False
            self.btn_test_start.setText("Start")
            self.btn_test_start.setEnabled(True)

    def send_data_request(self):
        if self.serial.is_running:
            self.serial.send_command("{D?}")

    def navigate_to(self, index):
        self.menuStackedWidget.setCurrentIndex(index)
        if index == 1:
            self.refresh_cal_combo(self.cmb_cal_temp_history, "TEMP")
        elif index == 2:
            self.refresh_cal_combo(self.cmb_cal_press_history, "PRESS")
        elif index == 3:
            self.refresh_cal_combo(self.cmb_cal_flow_history, "FLOW")

    def on_sensor_data(self, raw_data):
        self.latest_raw_data = raw_data

        raw_flow = raw_data.get("flow_rate", 0.0)
        raw_press = raw_data.get("pressure", 0.0)
        raw_temp = raw_data.get("temp", 0.0)
        raw_vol = raw_data.get("total_volume", 0.0)

        corr_temp = self.calib_mgr.get_corrected_value("TEMP", raw_temp)
        corr_press = self.calib_mgr.get_corrected_value("PRESS", raw_press)
        flow_gain = self.calib_mgr.get_interpolated_gain("FLOW", raw_flow)

        corr_flow = raw_flow * flow_gain
        corr_vol = raw_vol * flow_gain

        self.latest_corrected_data = {
            "flow_rate": corr_flow,
            "pressure": corr_press,
            "temp": corr_temp,
            "total_volume": corr_vol,
        }

        self.lcd_flow.display(corr_flow)
        self.lcd_press.display(corr_press)
        self.lcd_temp.display(corr_temp)
        self.lcd_cal_temp_sensor.display(corr_temp)
        self.lcd_cal_press_sensor.display(corr_press)

        if self.is_testing:
            self.current_session_data["flow_rate"].append(corr_flow)
            self.current_session_data["pressure"].append(corr_press)
            self.current_session_data["temp"].append(corr_temp)
            self.current_session_data["last_total_volume"] = corr_vol

            if self.target_volume > 0:
                progress = int((corr_vol / self.target_volume) * 100)
                self.progress_bar_test.setValue(min(progress, 100))
                self.statusbar.showMessage(
                    f"Testing: {corr_vol:.2f} / {self.target_volume:.2f} L"
                )

                if corr_vol >= self.target_volume:
                    self.force_stop_test("Target Volume Tercapai!")

        if self.is_calibrating_flow:
            self.calib_flow_buffer.append(raw_flow)

    def on_command_response(self, cmd_id, val):
        self.statusbar.showMessage(f"MCU Responded: {cmd_id} -> {val}", 3000)

    def handle_test_button(self):
        if self.btn_test_start.text() == "Start":
            self.start_test()
        else:
            self.force_stop_test("Dihentikan User")

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
                self, "Input Error", "Masukkan angka Volume Target yang valid."
            )
            return

        self.is_testing = True
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }
        self.poll_timer.stop()
        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:0,1}")
        self.btn_test_start.setText("Stop")
        self.btn_test_finish.setEnabled(False)
        self.progress_bar_test.setValue(0)
        self.statusbar.showMessage("Test Started (Streaming Mode)...")

    def force_stop_test(self, reason="Stopped"):
        if not self.is_testing:
            return
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_testing = False
        self.poll_timer.start()
        self.btn_test_start.setText("Start")
        self.btn_test_finish.setEnabled(True)
        final_vol = self.current_session_data["last_total_volume"]
        QtWidgets.QMessageBox.information(
            self,
            "Info",
            f"Pengujian Selesai: {reason}\nVolume Tercatat: {final_vol:.3f} Liter\nSilakan masukkan 'Final Meter Value'.",
        )

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
        msg = f"Data Saved!\nSys Vol (Corr): {actual_volume:.3f} L\nMeter Vol: {measured_volume:.3f} L\nError: {error_rate:.2f} %"
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

    def save_calibration_generic(self, sensor_type):
        if sensor_type == "TEMP":
            input_widget = self.input_cal_temp_ref
            raw_val = self.latest_raw_data["temp"]
            combo = self.cmb_cal_temp_history
        elif sensor_type == "PRESS":
            input_widget = self.input_cal_press_ref
            raw_val = self.latest_raw_data["pressure"]
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

    def start_flow_cal(self):
        if not self.serial.is_running:
            QtWidgets.QMessageBox.warning(self, "Error", "Serial not connected!")
            return
        self.is_calibrating_flow = True
        self.calib_flow_buffer = []
        self.poll_timer.stop()
        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:0,1}")
        self.statusbar.showMessage("Flow Calibration Started...")

    def stop_flow_cal(self):
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_calibrating_flow = False
        self.poll_timer.start()
        self.statusbar.showMessage("Flow Calibration Stopped.")
        raw_vol_end = self.latest_raw_data["total_volume"]
        self.testLastDutCount_8.setText(f"{raw_vol_end:.2f}")

    def save_flow_calibration(self):
        try:
            ref_vol = float(self.input_cal_flow_ref.toPlainText().strip())
            raw_vol = self.latest_raw_data["total_volume"]
            if raw_vol <= 0:
                raise ValueError("Sensor Volume is 0")
            target_gain = ref_vol / raw_vol
            if not self.calib_flow_buffer:
                avg_flow_rate = self.latest_raw_data["flow_rate"]
            else:
                avg_flow_rate = statistics.mean(self.calib_flow_buffer)
            artificial_ref_flow = avg_flow_rate * target_gain
            self.db.upsert_calibration_point("FLOW", avg_flow_rate, artificial_ref_flow)
            self.refresh_cal_combo(self.cmb_cal_flow_history, "FLOW")
            self.input_cal_flow_ref.clear()
            self.testLastDutCount_8.clear()
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                f"Flow Calibrated!\nAvg Flow: {avg_flow_rate:.1f} L/h\nGain: {target_gain:.4f}",
            )
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Input Invalid: {e}")

    def reset_flow_cal_ui(self):
        self.input_cal_flow_ref.clear()
        self.testLastDutCount_8.clear()
        self.testLastDutCount_6.clear()

    def refresh_cal_combo(self, combo_box, sensor_type):
        combo_box.clear()
        points = self.db.get_calibration_points(sensor_type)
        for p in points:
            # Tampilan Bersih: Ref & Sens
            text = f"Ref: {p[2]:.2f} | Sens: {p[1]:.2f}"
            combo_box.addItem(text, userData=p[0])

    def load_cal_details(self, combo, ref_display, gain_display):
        """
        [NEW] Mengambil detail lengkap dari DB berdasarkan ID item dropdown.
        Memperbarui tampilan Reference Value dan Gain Factor.
        """
        curr_id = combo.currentData()
        if not curr_id:
            # Kosongkan jika tidak ada pilihan
            ref_display.clear()
            gain_display.clear()
            return

        # Query detail lengkap dari DB
        point = self.db.get_calibration_point_by_id(curr_id)
        if point:
            # point: (id, sensor_val, reference_value, gain_factor, timestamp)
            ref_val = point[2]
            gain_val = point[3]

            ref_display.setText(f"{ref_val:.2f}")
            gain_display.setText(f"{gain_val:.4f}")

    def delete_calibration(self, combo, sensor_type, ref_display, gain_display):
        """
        [NEW] Menghapus data dan membersihkan tampilan detail.
        """
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
            # Bersihkan detail setelah delete
            ref_display.clear()
            gain_display.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WaterMeterApp()
    window.show()
    sys.exit(app.exec_())
