import serial
import serial.tools.list_ports
import time
import threading
import queue
from typing import Optional, Dict, Any, List, Tuple


## @class SerialWorker
#  @brief Handles threaded serial communication to prevent UI freezing.
class SerialWorker:
    def __init__(self) -> None:
        self.serial_conn: Optional[serial.Serial] = None
        self.is_active: bool = False
        self.port_name: str = ""
        self.baud_rate: int = 9600

        # Thread Communication Queues
        self.queue_cmds: queue.Queue[str] = queue.Queue()
        self.queue_data: queue.Queue[Tuple[str, Any]] = queue.Queue()
        self.queue_status: queue.Queue[Tuple[bool, str]] = queue.Queue()

        self.worker_thread: Optional[threading.Thread] = None

        # Simulator State
        self.is_simulation: bool = False
        self.sim_state: Dict[str, Any] = {"testing": False, "volume": 0.0}

    ## @brief Check if hardware is logically connected.
    def is_connected(self) -> bool:
        if self.is_simulation:
            return True
        return self.serial_conn is not None and self.serial_conn.is_open

    ## @brief Attempt to open serial port.
    def connect_serial(self, port: str, baud: int = 9600) -> bool:
        self.port_name = port
        self.baud_rate = baud

        if self.port_name == "MOCK_DEVICE":
            self.is_simulation = True
            self.is_active = True
            self._spawn_thread()
            self.queue_status.put((True, "Simulated Device Connected"))
            return True

        self.is_simulation = False
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()

            self.serial_conn = serial.Serial(port, baud, timeout=1)
            self.is_active = True
            self._spawn_thread()
            self.queue_status.put((True, f"Connected: {port}"))
            return True
        except Exception as e:
            self.queue_status.put((False, str(e)))
            return False

    ## @brief Close connection and stop thread.
    def disconnect_serial(self) -> None:
        self.is_active = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)

        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.queue_status.put((False, "Disconnected"))

    ## @brief Push command to write queue.
    def send_command(self, cmd: str) -> None:
        self.queue_cmds.put(cmd)

    def _spawn_thread(self) -> None:
        self.worker_thread = threading.Thread(target=self._run_io_loop, daemon=True)
        self.worker_thread.start()

    def _run_io_loop(self) -> None:
        while self.is_active:
            # Write
            try:
                cmd: str = self.queue_cmds.get_nowait()
                self._physical_write(cmd)
                time.sleep(0.05)
            except queue.Empty:
                pass

            # Read
            if self.is_simulation:
                self._sim_read()
                time.sleep(0.1)
            else:
                if self.serial_conn and self.serial_conn.in_waiting:
                    try:
                        line: str = (
                            self.serial_conn.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                        if line:
                            self._parse_packet(line)
                    except Exception as e:
                        print(f"Serial IO Error: {e}")
                time.sleep(0.05)

    def _physical_write(self, cmd: str) -> None:
        if self.is_simulation:
            self._sim_write(cmd)
        elif self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(cmd.encode("utf-8"))
            except Exception as e:
                self.queue_status.put((False, f"Write Fail: {e}"))

    def _sim_write(self, cmd: str) -> None:
        if "{S:1}" in cmd:
            self.sim_state["testing"] = True
            self.sim_state["volume"] = 0.0
            self.queue_data.put(("RESP", "S:OK"))
        elif "{S:0}" in cmd:
            self.sim_state["testing"] = False
            self.queue_data.put(("RESP", "S:OK"))
        elif "{B:" in cmd:
            self.queue_data.put(("RESP", "B:OK"))

    def _sim_read(self) -> None:
        flow: float = 0.0
        press: float = 0.1
        if self.sim_state["testing"]:
            self.sim_state["volume"] += 0.15
            flow = 1200.5
            press = 2.1

        # Protocol: {D:pulses,freq,flow,vol,press,temp,sol1,sol2}
        pkt: str = "{{D:1000,50.0,{:.2f},{:.2f},{:.2f},28.5,0,1}}".format(
            flow, self.sim_state["volume"], press
        )
        self._parse_packet(pkt)

    def _parse_packet(self, raw_str: str) -> None:
        if not (raw_str.startswith("{") and raw_str.endswith("}")):
            return
        content: str = raw_str[1:-1]
        if ":" not in content:
            return

        cid, val_part = content.split(":", 1)

        if cid == "D":
            parts = val_part.split(",")
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
                    self.queue_data.put(("DATA", data))
                except ValueError:
                    pass
        elif cid in ["S", "B", "Z"]:
            self.queue_data.put(("RESP", val_part))

    @staticmethod
    def get_available_ports() -> List[str]:
        ports: List[str] = [p.device for p in serial.tools.list_ports.comports()]
        ports.append("MOCK_DEVICE")
        return ports
