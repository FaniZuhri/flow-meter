import serial
import serial.tools.list_ports
import time
import random
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class SerialWorker(QThread):
    """
    Worker Thread untuk menangani komunikasi Serial UART.
    Mendukung MODE MOCK (Simulasi) jika tidak ada hardware.
    """

    # Signals
    data_received_signal = pyqtSignal(dict)
    connection_status_signal = pyqtSignal(bool, str)
    response_received_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.is_running = False
        self.port = ""
        self.baudrate = 9600
        self.mutex = QMutex()
        self.command_queue = []

        # --- Mock Variables ---
        self.is_mock = False
        self.mock_data = {
            "pulses": 0,
            "freq": 0.0,
            "flow_rate": 0.0,
            "total_volume": 0.0,
            "pressure": 0.0,
            "temp": 25.0,
            "sol_inlet": 0,
            "sol_outlet": 0,
        }
        self.is_testing_mock = False

    def is_connected(self):
        """Helper untuk mengecek status koneksi (Real atau Mock)."""
        if self.is_mock:
            return True
        return self.ser is not None and self.ser.is_open

    def connect_serial(self, port: str, baudrate: int = 9600) -> bool:
        self.port = port
        self.baudrate = baudrate

        # --- MOCK CONNECTION ---
        if port == "MOCK_PORT":
            self.is_mock = True
            self.is_running = True
            self.start()
            self.connection_status_signal.emit(True, "Connected to MOCK DEVICE")
            return True

        # --- REAL CONNECTION ---
        self.is_mock = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_running = True
            self.start()
            self.connection_status_signal.emit(True, f"Connected to {port}")
            return True
        except Exception as e:
            self.connection_status_signal.emit(False, str(e))
            return False

    def disconnect_serial(self):
        self.is_running = False
        self.wait()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_mock = False
        self.connection_status_signal.emit(False, "Disconnected")

    def send_command(self, command_str: str):
        self.mutex.lock()
        self.command_queue.append(command_str)
        self.mutex.unlock()

    # --- SIMULASI MCU ---
    def _process_mock_command(self, cmd):
        """Meniru respons MCU."""
        if not (cmd.startswith("{") and cmd.endswith("}")):
            return
        content = cmd[1:-1]
        parts = content.split(":")
        cmd_id = parts[0]
        val_str = parts[1] if len(parts) > 1 else ""

        time.sleep(0.05)  # Delay simulasi

        if cmd_id == "S":  # Start/Stop
            if val_str == "1":
                self.is_testing_mock = True
                self.response_received_signal.emit("S", "OK!")
            else:
                self.is_testing_mock = False
                self.response_received_signal.emit("S", "OK!")

        elif cmd_id == "B":  # Valve
            self.response_received_signal.emit("B", "OK!")

        elif cmd_id == "D?":  # Data Request
            self._generate_mock_data()
            self.data_received_signal.emit(self.mock_data)

    def _generate_mock_data(self):
        """Generator angka sensor palsu."""
        if self.is_testing_mock:
            self.mock_data["flow_rate"] = random.uniform(1200, 1250)
            self.mock_data["pressure"] = random.uniform(2.1, 2.3)
            self.mock_data["temp"] = random.uniform(28.0, 28.5)
            # Tambah volume (simulasi 0.5 detik)
            self.mock_data["total_volume"] += random.uniform(0.15, 0.17)
        else:
            self.mock_data["flow_rate"] = 0.0
            self.mock_data["pressure"] = random.uniform(0.0, 0.1)

    def run(self):
        while self.is_running:
            # 1. Ambil Command
            current_cmd = None
            self.mutex.lock()
            if self.command_queue:
                current_cmd = self.command_queue.pop(0)
            self.mutex.unlock()

            if self.is_mock:
                # JALUR MOCK
                if current_cmd:
                    self._process_mock_command(current_cmd)
                time.sleep(0.1)
            else:
                # JALUR REAL
                if self.ser and self.ser.is_open:
                    try:
                        if current_cmd:
                            self.ser.write(current_cmd.encode("utf-8"))
                            time.sleep(0.15)

                        if self.ser.in_waiting:
                            line = (
                                self.ser.readline()
                                .decode("utf-8", errors="ignore")
                                .strip()
                            )
                            if line:
                                self._parse_data(line)
                        time.sleep(0.05)
                    except Exception as e:
                        self.connection_status_signal.emit(False, str(e))
                        self.is_running = False
                else:
                    time.sleep(1)

    def _parse_data(self, raw_data):
        try:
            raw_data = raw_data.strip()
            if not (raw_data.startswith("{") and raw_data.endswith("}")):
                return
            content = raw_data[1:-1]
            parts = content.split(":")
            if len(parts) < 2:
                return
            cmd_id, values = parts[0], parts[1]

            if cmd_id == "D":
                val_list = values.split(",")
                if len(val_list) >= 8:
                    self.data_received_signal.emit(
                        {
                            "pulses": int(val_list[0]),
                            "freq": float(val_list[1]),
                            "flow_rate": float(val_list[2]),
                            "total_volume": float(val_list[3]),
                            "pressure": float(val_list[4]),
                            "temp": float(val_list[5]),
                            "sol_inlet": int(val_list[6]),
                            "sol_outlet": int(val_list[7]),
                        }
                    )
            elif cmd_id in ["B", "S", "Z"]:
                self.response_received_signal.emit(cmd_id, values)
        except Exception:
            pass

    @staticmethod
    def get_available_ports():
        ports = [port.device for port in serial.tools.list_ports.comports()]
        ports.append("MOCK_PORT")  # Tambahkan opsi virtual port
        return ports
