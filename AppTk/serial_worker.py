import serial
import serial.tools.list_ports
import time
import threading
import queue


class SerialWorker:
    def __init__(self):
        self.ser = None
        self.is_running = False
        self.port = ""
        self.baudrate = 9600

        # Threading Queues
        self.command_queue = queue.Queue()
        self.output_queue = queue.Queue()  # Sends data back to Main App
        self.status_queue = queue.Queue()  # Sends connection status msgs

        self.thread = None

        # --- Mock Simulation State ---
        self.is_mock = False
        self.mock_state = {
            "testing": False,
            "volume": 0.0,
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
            self._start_thread()
            self.status_queue.put((True, "Connected to Simulator"))
            return True

        self.is_mock = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()

            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.is_running = True
            self._start_thread()
            self.status_queue.put((True, f"Connected to {port}"))
            return True
        except Exception as e:
            self.status_queue.put((False, str(e)))
            return False

    def disconnect_serial(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status_queue.put((False, "Disconnected"))

    def send_command(self, command):
        self.command_queue.put(command)

    def _start_thread(self):
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        while self.is_running:
            # 1. Sending Process
            try:
                cmd_to_send = self.command_queue.get_nowait()
                self._write_serial(cmd_to_send)
                time.sleep(0.05)
            except queue.Empty:
                pass

            # 2. Reading Process
            if self.is_mock:
                self._read_mock()
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
            if "{D?}" in cmd:
                pass
            elif "{S:1}" in cmd:
                self.mock_state["testing"] = True
                self.mock_state["volume"] = 0.0
                self.output_queue.put(("RESP", "S", "OK!"))
            elif "{S:0}" in cmd:
                self.mock_state["testing"] = False
                self.output_queue.put(("RESP", "S", "OK!"))
            elif "{B:" in cmd:
                self.output_queue.put(("RESP", "B", "OK!"))
        else:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(cmd.encode("utf-8"))
                except Exception as e:
                    self.status_queue.put((False, f"Write Error: {e}"))

    def _read_mock(self):
        flow = 0.0
        press = 0.1
        if self.mock_state["testing"]:
            self.mock_state["volume"] += 0.15
            flow = 1200.5
            press = 2.1

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
                    self.output_queue.put(("DATA", data))
                except ValueError:
                    pass
        elif cmd_id in ["S", "B", "Z"]:
            self.output_queue.put(("RESP", cmd_id, val_str))

    @staticmethod
    def get_available_ports():
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports.append("MOCK_DEVICE")
        return ports
