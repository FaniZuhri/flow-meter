import serial
import serial.tools.list_ports
import time
import random
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


## @class SerialWorker
#  @brief Worker Thread for handling Serial UART communication.
#
#  This class runs in a separate thread from the GUI (QThread) to prevent
#  the application from freezing while waiting for serial I/O.
#  Supports MOCK_DEVICE mode for simulation without physical hardware.
class SerialWorker(QThread):

    # -- SIGNALS --
    # Emits parsed sensor data (dict) to the Main Thread
    data_received_signal = pyqtSignal(dict)
    # Emits connection status (bool) and log message (str)
    connection_status_signal = pyqtSignal(bool, str)
    # Emits raw command responses (e.g., "B:OK!")
    response_received_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.is_running = False
        self.port = ""
        self.baudrate = 9600
        # Mutex to prevent race conditions on the command queue
        self.mutex = QMutex()
        self.command_queue = []

        # --- Mock Simulation State ---
        self.is_mock = False
        self.mock_state = {
            "testing": False,
            "volume": 0.0,  # Simulation volume accumulator
        }

    ## @brief Checks if serial connection is active (or mock mode is active).
    def is_connected(self):
        if self.is_mock:
            return True
        return self.ser is not None and self.ser.is_open

    ## @brief Initiates connection to the serial port.
    #  @param port Port name (e.g., "COM3" or "/dev/ttyUSB0") or "MOCK_DEVICE".
    #  @param baudrate Communication speed (default 9600).
    def connect_serial(self, port, baudrate=9600):
        self.port = port
        self.baudrate = baudrate

        # Special logic for simulation mode
        if self.port == "MOCK_DEVICE":
            self.is_mock = True
            self.is_running = True
            self.start()  # Start the thread run() loop
            self.connection_status_signal.emit(True, "Connected to Simulator")
            return True

        self.is_mock = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()

            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.is_running = True
            self.start()  # Start the thread run() loop
            self.connection_status_signal.emit(True, f"Connected to {port}")
            return True
        except Exception as e:
            self.connection_status_signal.emit(False, str(e))
            return False

    ## @brief Disconnects serial and stops the thread.
    def disconnect_serial(self):
        self.is_running = False
        self.wait()  # Wait for thread loop to finish safely
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connection_status_signal.emit(False, "Disconnected")

    ## @brief Adds a command to the sending queue (Thread-Safe).
    #  @param command Command string (e.g., "{S:1}").
    def send_command(self, command):
        self.mutex.lock()
        self.command_queue.append(command)
        self.mutex.unlock()

    ## @brief Main thread loop.
    #  Handles sending commands from the queue and reading incoming data.
    def run(self):
        while self.is_running:
            # 1. Sending Process (Priority: Send before read)
            cmd_to_send = None
            self.mutex.lock()
            if self.command_queue:
                cmd_to_send = self.command_queue.pop(0)
            self.mutex.unlock()

            if cmd_to_send:
                self._write_serial(cmd_to_send)
                # Small delay to give microcontroller time to process
                time.sleep(0.05)

            # 2. Reading & Simulation Process
            if self.is_mock:
                self._read_mock()
                # Mock sleep set fast (0.1s) to be responsive in UI
                time.sleep(0.1)
            else:
                # Reading physical data from UART buffer
                if self.ser and self.ser.in_waiting:
                    try:
                        # Decode utf-8 and ignore byte errors
                        raw_line = (
                            self.ser.readline().decode("utf-8", errors="ignore").strip()
                        )
                        if raw_line:
                            self._parse_protocol(raw_line)
                    except Exception as e:
                        print(f"Serial Read Error: {e}")
                time.sleep(0.05)

    ## @brief Internal: Sends data to hardware or processes mock commands.
    def _write_serial(self, cmd):
        if self.is_mock:
            # Simulate stateful MCU response & behavior
            if "{D?}" in cmd:
                pass  # Data request handled by _read_mock
            elif "{S:1}" in cmd:
                self.mock_state["testing"] = True
                self.mock_state["volume"] = 0.0  # Reset volume on Start
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

    ## @brief Internal: Dummy data generator for simulation mode.
    def _read_mock(self):
        flow = 0.0
        press = 0.1

        if self.mock_state["testing"]:
            # Simulate rising volume and flow rate when testing is active
            self.mock_state["volume"] += 0.15
            flow = 1200.5
            press = 2.1

        # Protocol format: {D:pulses,freq,flow,vol,press,temp,sol1,sol2}
        mock_str = "{{D:1000,50.5,{:.2f},{:.2f},{:.2f},28.5,0,1}}".format(
            flow, self.mock_state["volume"], press
        )
        self._parse_protocol(mock_str)

    ## @brief Internal: Parser for UART communication protocol.
    #  Expected format: {ID:Value1,Value2,...}
    def _parse_protocol(self, raw_data):
        if not (raw_data.startswith("{") and raw_data.endswith("}")):
            return

        content = raw_data[1:-1]
        if ":" not in content:
            return

        cmd_id, val_str = content.split(":", 1)

        if cmd_id == "D":
            # Sensor Data
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
                    pass  # Ignore corrupt data/NaN

        elif cmd_id in ["S", "B", "Z"]:
            # Command Response
            self.response_received_signal.emit(cmd_id, val_str)

    ## @brief Static helper to list available serial ports.
    @staticmethod
    def get_available_ports():
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports.append("MOCK_DEVICE")
        return ports
