import serial
import serial.tools.list_ports
import time
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class SerialWorker(QThread):
    """
    Worker Thread untuk menangani komunikasi Serial UART dengan STM32.
    Memisahkan proses komunikasi dari UI Thread agar aplikasi tidak freeze.
    """

    # Signals untuk mengirim data ke Main Thread (UI)
    data_received_signal = pyqtSignal(dict)  # Data sensor terparsing
    connection_status_signal = pyqtSignal(bool, str)  # Status koneksi
    response_received_signal = pyqtSignal(str, str)  # Respon command (ACK)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.is_running = False
        self.port = ""
        self.baudrate = 9600
        self.mutex = QMutex()  # Untuk thread safety saat akses antrian
        self.command_queue = []  # Antrian perintah yang akan dikirim

    def connect_serial(self, port: str, baudrate: int = 9600) -> bool:
        """Membuka koneksi ke port serial."""
        self.port = port
        self.baudrate = baudrate
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()

            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_running = True
            self.start()  # Menjalankan method run()
            self.connection_status_signal.emit(True, f"Connected to {port}")
            return True
        except Exception as e:
            self.connection_status_signal.emit(False, str(e))
            return False

    def disconnect_serial(self):
        """Menutup koneksi serial secara aman."""
        self.is_running = False
        self.wait()  # Menunggu thread berhenti
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connection_status_signal.emit(False, "Disconnected")

    def send_command(self, command_str: str):
        """
        Menambahkan perintah ke antrian untuk dikirim (Thread Safe).
        Format command: "{ID:Value}"
        """
        self.mutex.lock()
        self.command_queue.append(command_str)
        self.mutex.unlock()

    def _parse_data(self, raw_data: str):
        """Internal method untuk memparsing string data dari MCU."""
        try:
            raw_data = raw_data.strip()
            # Validasi format: diawali { dan diakhiri }
            if not (raw_data.startswith("{") and raw_data.endswith("}")):
                return

            content = raw_data[1:-1]  # Hapus { dan }
            parts = content.split(":")

            if len(parts) < 2:
                return

            cmd_id = parts[0]
            values = parts[1]

            # --- Handle Data Sensor (Command ID: D) ---
            if cmd_id == "D":
                # Format: <pulsa>,<frek>,<debit>,<total_vol>,<tek>,<suhu>,<sol1>,<sol2>
                val_list = values.split(",")
                if len(val_list) >= 8:
                    sensor_data = {
                        "pulses": int(val_list[0]),
                        "freq": float(val_list[1]),
                        "flow_rate": float(val_list[2]),
                        "total_volume": float(val_list[3]),
                        "pressure": float(val_list[4]),
                        "temp": float(val_list[5]),
                        "sol_inlet": int(val_list[6]),
                        "sol_outlet": int(val_list[7]),
                    }
                    self.data_received_signal.emit(sensor_data)

            # --- Handle Command Response (Command ID: B, S, Z) ---
            elif cmd_id in ["B", "S", "Z"]:
                self.response_received_signal.emit(cmd_id, values)

        except Exception as e:
            print(f"[Serial] Parse Error: {e} | Raw Data: {raw_data}")

    def run(self):
        """Loop utama thread komunikasi."""
        while self.is_running:
            if self.ser and self.ser.is_open:
                try:
                    # 1. Kirim Command dari Antrian
                    self.mutex.lock()
                    if self.command_queue:
                        cmd = self.command_queue.pop(0)
                        self.ser.write(cmd.encode("utf-8"))
                        # Delay penting untuk MCU memproses perintah berurutan
                        time.sleep(0.15)
                    self.mutex.unlock()

                    # 2. Baca Data Masuk
                    if self.ser.in_waiting:
                        line = (
                            self.ser.readline().decode("utf-8", errors="ignore").strip()
                        )
                        if line:
                            self._parse_data(line)

                    time.sleep(0.05)  # Sleep ringan agar tidak memakan CPU 100%

                except Exception as e:
                    print(f"[Serial] Loop Error: {e}")
                    self.connection_status_signal.emit(False, str(e))
                    self.is_running = False
            else:
                time.sleep(1)  # Tunggu jika serial belum connect

    @staticmethod
    def get_available_ports() -> list:
        """Mengambil daftar port COM/TTY yang tersedia di sistem."""
        return [port.device for port in serial.tools.list_ports.comports()]
