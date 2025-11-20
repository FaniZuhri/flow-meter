import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer

# Import View dan Model
from app_ui import Ui_MainWindow
from database import DatabaseManager
from serial_worker import SerialWorker


class WaterMeterApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # --- Inisialisasi Model & Worker ---
        self.db = DatabaseManager()
        self.serial = SerialWorker()

        # --- Variabel State Aplikasi ---
        self.is_testing = False
        self.target_volume = 0.0

        # Buffer data
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }

        self.latest_data = {
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

        # Default Page
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

        self.btn_cal_temp_save.clicked.connect(lambda: self.save_calibration("TEMP"))
        self.btn_cal_temp_delete.clicked.connect(
            lambda: self.delete_calibration(self.cmb_cal_temp_history, "TEMP")
        )
        self.cmb_cal_temp_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_temp_history, self.display_cal_temp_gain
            )
        )

        self.btn_cal_press_save.clicked.connect(lambda: self.save_calibration("PRESS"))
        self.btn_cal_press_delete.clicked.connect(
            lambda: self.delete_calibration(self.cmb_cal_press_history, "PRESS")
        )
        self.cmb_cal_press_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_press_history, self.display_cal_press_gain
            )
        )

        self.btn_cal_flow_start.clicked.connect(self.start_flow_cal)
        self.btn_cal_flow_stop.clicked.connect(self.stop_flow_cal)
        self.btn_cal_flow_save.clicked.connect(lambda: self.save_calibration("FLOW"))
        self.btn_cal_flow_delete.clicked.connect(
            lambda: self.delete_calibration(self.cmb_cal_flow_history, "FLOW")
        )
        self.cmb_cal_flow_history.currentIndexChanged.connect(
            lambda: self.load_cal_details(
                self.cmb_cal_flow_history, self.testLastDutCount_6
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

    def on_sensor_data(self, data):
        self.latest_data = data

        # Update LCDs
        self.lcd_flow.display(data["flow_rate"])
        self.lcd_press.display(data["pressure"])
        self.lcd_temp.display(data["temp"])
        self.lcd_cal_temp_sensor.display(data["temp"])
        self.lcd_cal_press_sensor.display(data["pressure"])

        current_actual_vol = data["total_volume"]

        if self.is_testing:
            self.current_session_data["flow_rate"].append(data["flow_rate"])
            self.current_session_data["pressure"].append(data["pressure"])
            self.current_session_data["temp"].append(data["temp"])
            self.current_session_data["last_total_volume"] = current_actual_vol

            if self.target_volume > 0:
                progress = int((current_actual_vol / self.target_volume) * 100)
                self.progress_bar_test.setValue(min(progress, 100))

                self.statusbar.showMessage(
                    f"Testing: {current_actual_vol:.2f} / {self.target_volume:.2f} L"
                )

                if current_actual_vol >= self.target_volume:
                    self.force_stop_test("Target Volume Tercapai!")

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
            init_str = self.input_test_init_meter.toPlainText().strip()

            if not vol_str:
                raise ValueError("Volume Empty")
            self.target_volume = float(vol_str)
            if self.target_volume <= 0:
                raise ValueError("Volume <= 0")
            if init_str:
                float(init_str)

        except ValueError:
            QtWidgets.QMessageBox.warning(
                self,
                "Input Error",
                "Masukkan angka Volume Target (Liter) dengan benar.",
            )
            return

        self.is_testing = True
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0,
        }

        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:0,1}")

        self.btn_test_start.setText("Stop")
        self.btn_test_finish.setEnabled(False)
        self.progress_bar_test.setValue(0)
        self.statusbar.showMessage("Test Started...")

    def force_stop_test(self, reason="Stopped"):
        if not self.is_testing:
            return

        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")

        self.is_testing = False
        self.btn_test_start.setText("Start")
        self.btn_test_finish.setEnabled(True)

        QtWidgets.QMessageBox.information(
            self,
            "Info",
            f"Pengujian Selesai: {reason}\nSilakan masukkan 'Final Meter Value'.",
        )
        self.statusbar.showMessage(f"Test Stopped: {reason}")

    def save_test_result(self):
        """
        LOGIKA HITUNG ERROR RATE ADA DI SINI.
        """
        try:
            final_str = self.input_test_final_meter.toPlainText().strip()
            init_str = self.input_test_init_meter.toPlainText().strip()
            final_meter = float(final_str)
            init_meter = float(init_str) if init_str else 0.0
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Error", "Input Final Meter Value correctly!"
            )
            return

        buff = self.current_session_data

        # 1. Hitung Volume Terukur (Meter)
        measured_volume = final_meter - init_meter

        # 2. Ambil Volume Sebenarnya (Sistem/Sensor)
        actual_volume = buff["last_total_volume"]

        # 3. Hitung Error Rate
        # Rumus: ((Measured - Actual) / Actual) * 100
        error_rate = 0.0
        if actual_volume > 0:
            error_rate = ((measured_volume - actual_volume) / actual_volume) * 100

        # Rata-rata sensor lain
        avg_flow = (
            sum(buff["flow_rate"]) / len(buff["flow_rate"]) if buff["flow_rate"] else 0
        )
        avg_press = (
            sum(buff["pressure"]) / len(buff["pressure"]) if buff["pressure"] else 0
        )
        avg_temp = sum(buff["temp"]) / len(buff["temp"]) if buff["temp"] else 0

        log_data = {
            "volume_target": self.target_volume,
            "initial_meter": init_meter,
            "final_meter": final_meter,
            "measured_volume": measured_volume,  # Data baru
            "actual_volume": actual_volume,
            "error_rate": round(error_rate, 2),  # Data baru (disimpan 2 desimal)
            "avg_flow_rate": round(avg_flow, 2),
            "avg_pressure": round(avg_press, 2),
            "avg_temp": round(avg_temp, 2),
            "status": "FINISHED",
        }

        self.db.insert_test_log(log_data)

        # Tampilkan hasil Error Rate ke User
        msg = (
            f"Data Saved Successfully!\n\n"
            f"System Volume: {actual_volume:.2f} L\n"
            f"Meter Volume: {measured_volume:.2f} L\n"
            f"--------------------------\n"
            f"Error Rate: {error_rate:.2f} %"
        )

        if abs(error_rate) <= 2.0:  # Contoh standar 2% (bisa disesuaikan)
            msg += "\n[PASSED]"
        else:
            msg += "\n[FAILED / OUT OF SPEC]"

        QtWidgets.QMessageBox.information(self, "Result", msg)
        self.btn_test_finish.setEnabled(False)

    def reset_test_ui(self):
        if self.is_testing:
            self.force_stop_test("Reset Button Pressed")
        self.input_test_volume.clear()
        self.input_test_init_meter.clear()
        self.input_test_final_meter.clear()
        self.progress_bar_test.setValue(0)

    # --- CALIBRATION HELPERS ---
    def refresh_cal_combo(self, combo_box, sensor_type):
        combo_box.clear()
        points = self.db.get_calibration_points(sensor_type)
        for p in points:
            text = f"ID:{p[0]} | Sens:{p[1]:.2f} | Ref:{p[2]:.2f} | Gain:{p[3]:.4f}"
            combo_box.addItem(text, userData=p[0])

    def load_cal_details(self, combo, display_widget):
        text = combo.currentText()
        if "Gain:" in text:
            try:
                gain_str = text.split("Gain:")[1].strip()
                display_widget.setText(gain_str)
            except:
                pass

    def save_calibration(self, sensor_type):
        input_widget = None
        sensor_val = 0.0

        if sensor_type == "TEMP":
            input_widget = self.input_cal_temp_ref
            sensor_val = self.latest_data["temp"]
        elif sensor_type == "PRESS":
            input_widget = self.input_cal_press_ref
            sensor_val = self.latest_data["pressure"]
        elif sensor_type == "FLOW":
            input_widget = self.input_cal_flow_ref
            sensor_val = self.latest_data["total_volume"]

        try:
            ref_str = input_widget.toPlainText().strip()
            if not ref_str:
                raise ValueError
            ref_val = float(ref_str)

            self.db.add_calibration_point(sensor_type, sensor_val, ref_val)

            if sensor_type == "TEMP":
                self.refresh_cal_combo(self.cmb_cal_temp_history, "TEMP")
            elif sensor_type == "PRESS":
                self.refresh_cal_combo(self.cmb_cal_press_history, "PRESS")
            elif sensor_type == "FLOW":
                self.refresh_cal_combo(self.cmb_cal_flow_history, "FLOW")

            input_widget.clear()
            QtWidgets.QMessageBox.information(
                self, "Success", f"{sensor_type} Calibration Saved!"
            )
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid Reference Value!")

    def delete_calibration(self, combo, sensor_type):
        id_to_del = combo.currentData()
        if id_to_del:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete",
                "Delete this point?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.db.delete_calibration_point(id_to_del)
                self.refresh_cal_combo(combo, sensor_type)

    def start_flow_cal(self):
        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:0,1}")
        self.statusbar.showMessage("Flow Calibration Started...")

    def stop_flow_cal(self):
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.statusbar.showMessage("Flow Calibration Stopped.")

    def reset_flow_cal_ui(self):
        self.input_cal_flow_ref.clear()
        self.testLastDutCount_6.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WaterMeterApp()
    window.show()
    sys.exit(app.exec_())
