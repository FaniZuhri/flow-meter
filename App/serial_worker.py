import serial
import serial.tools.list_ports
import time
import random
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class SerialWorker(QThread):
    """
    Worker Thread untuk menangani komunikasi Serial UART.
    Mendukung MODE MOCK (Simulasi) yang lebih responsif.
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
        self.mock_state = {
            "testing": False,
            "volume": 0.0,  # Simulasi volume internal MCU
        }

    def is_connected(self):
        if self.is_mock:
            return True
        return self.ser is not None and self.ser.is_open

    def connect_serial(self, port, baudrate=9600):
        self.port = port
        self.baudrate = baudrate

        if self.port == "MOCK_DEVICE":
            self.is_mock = True
            self.is_running = True
            self.start()
            self.connection_status_signal.emit(True, "Connected to Simulator")
            return True

        self.is_mock = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()

            self.ser = serial.Serial(port, baudrate, timeout=1)
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
        self.connection_status_signal.emit(False, "Disconnected")

    def send_command(self, command):
        self.mutex.lock()
        self.command_queue.append(command)
        self.mutex.unlock()

    def run(self):
        """Loop utama thread yang lebih cepat agar tidak lag."""
        while self.is_running:
            # 1. Proses Kirim (Priority)
            cmd_to_send = None
            self.mutex.lock()
            if self.command_queue:
                cmd_to_send = self.command_queue.pop(0)
            self.mutex.unlock()

            if cmd_to_send:
                self._write_serial(cmd_to_send)
                # Jeda sebentar untuk stabilitas kirim
                time.sleep(0.05)

            # 2. Proses Baca & Simulasi
            if self.is_mock:
                self._read_mock()
                # PERBAIKAN: Sleep simulasi dikurangi jadi 0.1s agar lebih cepat dari timer UI (0.5s)
                time.sleep(0.1)
            else:
                if self.ser and self.ser.in_waiting:
                    try:
                        raw_line = (
                            self.ser.readline().decode("utf-8", errors="ignore").strip()
                        )
                        if raw_line:
                            self._parse_protocol(raw_line)
                    except Exception as e:
                        print(f"Serial Read Error: {e}")
                time.sleep(0.05)

    def _write_serial(self, cmd):
        if self.is_mock:
            # Simulasi respon & behavior MCU
            if "{D?}" in cmd:
                pass  # Data request di-handle di _read_mock
            elif "{S:1}" in cmd:
                self.mock_state["testing"] = True
                self.mock_state["volume"] = 0.0  # RESET saat Start
                self.response_received_signal.emit("S", "OK!")
            elif "{S:0}" in cmd:
                self.mock_state["testing"] = False
                self.response_received_signal.emit("S", "OK!")
            elif "{B:" in cmd:
                self.response_received_signal.emit("B", "OK!")
        else:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(cmd.encode("utf-8"))
                except Exception as e:
                    self.connection_status_signal.emit(False, f"Write Error: {e}")

    def _read_mock(self):
        """Generator data palsu."""
        # PERBAIKAN: Hapus pengecekan queue agar data tetap mengalir

        flow = 0.0
        press = 0.1

        if self.mock_state["testing"]:
            # Simulasi: tambah 0.15L setiap cycle (0.1s) -> ~1.5L per detik
            self.mock_state["volume"] += 0.15
            flow = 1200.5
            press = 2.1

        # Format: {D:pulsa,freq,debit,vol,tek,suhu,sol1,sol2}
        mock_str = "{{D:1000,50.5,{:.2f},{:.2f},{:.2f},28.5,0,1}}".format(
            flow, self.mock_state["volume"], press
        )
        self._parse_protocol(mock_str)

    def _parse_protocol(self, raw_data):
        if not (raw_data.startswith("{") and raw_data.endswith("}")):
            return

        content = raw_data[1:-1]
        if ":" not in content:
            return

        cmd_id, val_str = content.split(":", 1)

        if cmd_id == "D":
            parts = val_str.split(",")
            if len(parts) >= 8:
                try:
                    data = {
                        "pulses": int(parts[0]),
                        "freq": float(parts[1]),
                        "flow_rate": float(parts[2]),
                        "total_volume": float(parts[3]),
                        "pressure": float(parts[4]),
                        "temp": float(parts[5]),
                        "sol_inlet": int(parts[6]),
                        "sol_outlet": int(parts[7]),
                    }
                    self.data_received_signal.emit(data)
                except ValueError:
                    pass

        elif cmd_id in ["S", "B", "Z"]:
            self.response_received_signal.emit(cmd_id, val_str)

    @staticmethod
    def get_available_ports():
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports.append("MOCK_DEVICE")
        return ports
