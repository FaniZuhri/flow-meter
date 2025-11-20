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

        # Model Initialization
        self.db = DatabaseManager()
        self.serial_worker = SerialWorker()

        # Application State
        self.is_testing = False
        self.latest_sensor_data = {
            "flow_rate": 0.0,
            "pressure": 0.0,
            "temp": 0.0,
            "total_volume": 0.0,
        }
        self.test_buffer = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }

        # Timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.request_sensor_data)
        self.poll_timer.setInterval(500)  # 500ms

        # Setup
        self.init_ui_connections()
        self.init_serial_connections()
        self.refresh_ports()

        # Default Page
        self.menuStackedWidget.setCurrentIndex(0)

        # Kondisi Awal Tombol Finish: Disable
        self.btn_test_finish.setEnabled(False)

    # --- UI Connections ---
    def init_ui_connections(self):
        # Header
        self.btn_connect.clicked.connect(self.toggle_connection)

        # Sidebar Navigation
        self.btn_nav_test.clicked.connect(lambda: self.navigate_to_page(0))
        self.btn_nav_temp_cal.clicked.connect(lambda: self.navigate_to_page(1))
        self.btn_nav_press_cal.clicked.connect(lambda: self.navigate_to_page(2))
        self.btn_nav_flow_cal.clicked.connect(lambda: self.navigate_to_page(3))

        # --- TEST PAGE LOGIC ---
        # Hubungkan ke handler toggle (bukan langsung start_test)
        self.btn_test_start.clicked.connect(self.handle_test_toggle)
        self.btn_test_finish.clicked.connect(self.finish_test)
        self.btn_test_reset.clicked.connect(self.reset_test_ui)

        # Temp Cal Page
        self.btn_cal_temp_save.clicked.connect(self.calibrate_temp_save)
        self.btn_cal_temp_delete.clicked.connect(self.calibrate_temp_delete)
        self.cmb_cal_temp_history.currentIndexChanged.connect(
            self.load_temp_cal_details
        )

        # Press Cal Page
        self.btn_cal_press_save.clicked.connect(self.calibrate_press_save)
        self.btn_cal_press_delete.clicked.connect(self.calibrate_press_delete)
        self.cmb_cal_press_history.currentIndexChanged.connect(
            self.load_press_cal_details
        )

        # Flow Cal Page
        self.btn_cal_flow_start.clicked.connect(self.calibrate_flow_start)
        self.btn_cal_flow_stop.clicked.connect(self.calibrate_flow_stop)
        self.btn_cal_flow_save.clicked.connect(self.calibrate_flow_save)
        self.btn_cal_flow_delete.clicked.connect(self.calibrate_flow_delete)

    def init_serial_connections(self):
        self.serial_worker.connection_status_signal.connect(
            self.on_serial_status_changed
        )
        self.serial_worker.data_received_signal.connect(self.on_sensor_data_received)

    def refresh_ports(self):
        self.cmb_port_select.clear()
        self.cmb_port_select.addItems(SerialWorker.get_available_ports())

    def navigate_to_page(self, index):
        self.menuStackedWidget.setCurrentIndex(index)
        if index == 1:
            self.refresh_cal_dropdown(self.cmb_cal_temp_history, "TEMP")
        elif index == 2:
            self.refresh_cal_dropdown(self.cmb_cal_press_history, "PRESS")
        elif index == 3:
            self.refresh_cal_dropdown(self.cmb_cal_flow_history, "FLOW")

    # --- Serial Logic ---
    def toggle_connection(self):
        if self.btn_connect.text() == "Connect":
            port = self.cmb_port_select.currentText()
            if port and self.serial_worker.connect_serial(port):
                self.btn_connect.setText("Disconnect")
                self.poll_timer.start()
        else:
            self.serial_worker.disconnect_serial()
            self.btn_connect.setText("Connect")
            self.poll_timer.stop()

    def on_serial_status_changed(self, connected, msg):
        self.statusbar.showMessage(f"Serial: {msg}")
        if not connected:
            self.btn_connect.setText("Connect")
            self.poll_timer.stop()

            # Reset State jika putus koneksi
            self.is_testing = False
            self.btn_test_start.setText("Start")
            self.btn_test_start.setEnabled(True)
            self.btn_test_finish.setEnabled(False)

    def request_sensor_data(self):
        # PERBAIKAN 1: Gunakan is_connected() agar support Mock
        if self.serial_worker.is_connected():
            self.serial_worker.send_command("{D?}")

    def on_sensor_data_received(self, data):
        self.latest_sensor_data = data

        # Update Displays
        self.lcd_flow.display(data["flow_rate"])
        self.lcd_press.display(data["pressure"])
        self.lcd_temp.display(data["temp"])

        self.lcd_cal_temp_sensor.display(data["temp"])
        self.lcd_cal_press_sensor.display(data["pressure"])

        # Update Progress
        try:
            target_str = self.input_test_volume.toPlainText()
            if target_str:
                target = float(target_str)
                if target > 0:
                    percent = int((data["total_volume"] / target) * 100)
                    self.progress_bar_test.setValue(min(percent, 100))
        except:
            pass

        if self.is_testing:
            self.test_buffer["flow_rate"].append(data["flow_rate"])
            self.test_buffer["pressure"].append(data["pressure"])
            self.test_buffer["temp"].append(data["temp"])
            self.test_buffer["last_total_volume"] = data["total_volume"]

    # --- Test Logic (Revised Toggle) ---

    def handle_test_toggle(self):
        """Handler pintar untuk tombol Start/Stop."""
        current_label = self.btn_test_start.text()

        if current_label == "Start":
            self.start_test_sequence()
        else:
            self.stop_test_sequence()

    def start_test_sequence(self):
        """Memulai Pengujian."""
        # PERBAIKAN 2: Cek koneksi menggunakan is_connected() bukan .ser
        if not self.serial_worker.is_connected():
            QtWidgets.QMessageBox.critical(
                self, "Error", "Serial belum terhubung! Silakan Connect dulu."
            )
            return

        # 2. Validasi Input (Tidak boleh kosong)
        vol_str = self.input_test_volume.toPlainText()
        init_str = self.input_test_init_meter.toPlainText()

        if not vol_str or not init_str:
            QtWidgets.QMessageBox.warning(
                self,
                "Input Error",
                "Volume Target dan Initial Meter tidak boleh kosong!",
            )
            return

        try:
            float(vol_str)
            float(init_str)
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Input Error", "Masukkan angka yang valid!"
            )
            return

        # 3. Reset Buffer & Kirim Command
        self.test_buffer = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0,
        }
        self.serial_worker.send_command("{S:1}")  # Start MCU Counting
        self.serial_worker.send_command("{B:0,1}")  # Open Valve

        # 4. Update UI State
        self.is_testing = True
        self.btn_test_start.setText("Stop")  # Ubah label jadi STOP
        self.btn_test_finish.setEnabled(False)  # Finish tetap disable
        self.statusbar.showMessage("Test Started...")

    def stop_test_sequence(self):
        """Menghentikan Pengujian."""
        # 1. Kirim Command Stop (Valve dulu baru Test)
        self.serial_worker.send_command("{B:0,0}")  # Close Valve First
        self.serial_worker.send_command("{S:0}")  # Stop MCU Counting

        # 2. Update UI State
        self.is_testing = False
        self.btn_test_start.setText("Start")  # Balik jadi START
        self.btn_test_finish.setEnabled(True)  # BARU Enable Finish

        self.statusbar.showMessage("Test Stopped. Please Input Last Meter.")
        QtWidgets.QMessageBox.information(
            self,
            "Info",
            "Pengujian Dihentikan.\nSilakan input 'Last Meter' dan tekan Finish.",
        )

    def finish_test(self):
        """Menyimpan Data (Hanya bisa diklik setelah Stop)."""
        # 1. Validasi Input Akhir
        last_meter_str = self.input_test_final_meter.toPlainText()

        if not last_meter_str:
            QtWidgets.QMessageBox.warning(
                self, "Input Error", "Kolom 'Last Meter' harus diisi sebelum Finish!"
            )
            return

        try:
            final_meter = float(last_meter_str)
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Input Error", "'Last Meter' harus berupa angka!"
            )
            return

        # 2. Hitung Rata-rata
        buff = self.test_buffer
        avg_flow = (
            sum(buff["flow_rate"]) / len(buff["flow_rate"]) if buff["flow_rate"] else 0
        )
        avg_press = (
            sum(buff["pressure"]) / len(buff["pressure"]) if buff["pressure"] else 0
        )
        avg_temp = sum(buff["temp"]) / len(buff["temp"]) if buff["temp"] else 0

        # 3. Simpan ke Database
        data = {
            "volume_target": float(self.input_test_volume.toPlainText()),
            "initial_meter": float(self.input_test_init_meter.toPlainText()),
            "final_meter": final_meter,
            "actual_volume": buff["last_total_volume"],
            "avg_flow_rate": round(avg_flow, 2),
            "avg_pressure": round(avg_press, 2),
            "avg_temp": round(avg_temp, 2),
            "status": "FINISHED",
        }
        self.db.insert_test_log(data)

        # 4. Reset Tombol Finish (Disable lagi setelah save)
        QtWidgets.QMessageBox.information(self, "Success", "Data Berhasil Disimpan!")
        self.btn_test_finish.setEnabled(False)
        self.statusbar.showMessage("Data Saved.")

    def reset_test_ui(self):
        """Emergency Reset."""
        self.serial_worker.send_command("{B:0,0}")
        self.serial_worker.send_command("{S:0}")

        self.is_testing = False
        self.btn_test_start.setText("Start")
        self.btn_test_start.setEnabled(True)
        self.btn_test_finish.setEnabled(False)

        self.input_test_volume.clear()
        self.input_test_init_meter.clear()
        self.input_test_final_meter.clear()
        self.progress_bar_test.setValue(0)
        self.statusbar.showMessage("System Reset.")

    # --- Calibration Helpers ---
    def refresh_cal_dropdown(self, combo, type_):
        combo.clear()
        for p in self.db.get_calibration_points(type_):
            combo.addItem(f"ID:{p[0]} | S:{p[1]} | R:{p[2]} | G:{p[3]:.4f}", userData=p)

    def generic_cal_save(self, type_, ref_input, sens_val, combo, clear_input=True):
        try:
            ref_str = ref_input.toPlainText()
            if not ref_str:
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Input tidak boleh kosong!"
                )
                return

            ref = float(ref_str)
            self.db.add_calibration_point(type_, sens_val, ref)
            self.refresh_cal_dropdown(combo, type_)
            if clear_input:
                ref_input.clear()
            QtWidgets.QMessageBox.information(self, "Success", "Calibration Saved!")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid Input!")

    def generic_cal_delete(self, combo, type_):
        idx = combo.currentIndex()
        if idx < 0:
            return
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Confirm",
                "Delete Point?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            == QtWidgets.QMessageBox.Yes
        ):
            self.db.delete_calibration_point(combo.currentData()[0])
            self.refresh_cal_dropdown(combo, type_)

    # --- Calibration Slots ---
    def calibrate_temp_save(self):
        self.generic_cal_save(
            "TEMP",
            self.input_cal_temp_ref,
            self.latest_sensor_data["temp"],
            self.cmb_cal_temp_history,
        )

    def calibrate_temp_delete(self):
        self.generic_cal_delete(self.cmb_cal_temp_history, "TEMP")

    def load_temp_cal_details(self):
        d = self.cmb_cal_temp_history.currentData()
        if d:
            self.display_cal_temp_gain.setText(str(d[3]))

    def calibrate_press_save(self):
        self.generic_cal_save(
            "PRESS",
            self.input_cal_press_ref,
            self.latest_sensor_data["pressure"],
            self.cmb_cal_press_history,
        )

    def calibrate_press_delete(self):
        self.generic_cal_delete(self.cmb_cal_press_history, "PRESS")

    def load_press_cal_details(self):
        d = self.cmb_cal_press_history.currentData()
        if d:
            self.display_cal_press_gain.setText(str(d[3]))

    def calibrate_flow_start(self):
        # PERBAIKAN 3: Gunakan is_connected() untuk Flow Calibration juga
        if not self.serial_worker.is_connected():
            QtWidgets.QMessageBox.critical(self, "Error", "Serial Disconnected!")
            return
        self.serial_worker.send_command("{S:1}")
        self.serial_worker.send_command("{B:0,1}")

    def calibrate_flow_stop(self):
        self.serial_worker.send_command("{B:0,0}")
        self.serial_worker.send_command("{S:0}")

    def calibrate_flow_save(self):
        self.generic_cal_save(
            "FLOW",
            self.input_cal_flow_ref,
            self.latest_sensor_data["total_volume"],
            self.cmb_cal_flow_history,
        )

    def calibrate_flow_delete(self):
        self.generic_cal_delete(self.cmb_cal_flow_history, "FLOW")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WaterMeterApp()
    window.show()
    sys.exit(app.exec_())
