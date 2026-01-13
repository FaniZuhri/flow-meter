import statistics
import queue
from typing import Dict, Any, List, Optional, Tuple

from database import DatabaseManager
from calibration_manager import CalibrationManager
from serial_worker import SerialWorker


## @class WMTKController
#  @brief Orchestrates data flow between Hardware, Database, and UI.
class WMTKController:
    def __init__(self) -> None:
        self.db: DatabaseManager = DatabaseManager()
        self.serial: SerialWorker = SerialWorker()
        self.calib: CalibrationManager = CalibrationManager(self.db)

        # State Variables
        self.flag_testing: bool = False
        self.flag_calibrating_flow: bool = False

        self.test_target_vol: float = 0.0

        # Accumulation Logic
        self.prev_raw_vol: float = 0.0
        self.accumulated_vol: float = 0.0

        # Data Buffers
        self.test_buffer: Dict[str, List[float]] = {"flow": [], "press": [], "temp": []}
        self.test_final_vol: float = 0.0
        self.flow_calib_buffer: List[float] = []

        # Latest Snapshot
        self.last_packet: Dict[str, Any] = {
            "flow_rate": 0.0,
            "pressure": 0.0,
            "temp": 0.0,
            "total_volume": 0.0,
        }

    # --- Connectivity Wrappers ---
    def get_ports(self) -> List[str]:
        return self.serial.get_available_ports()

    def connect_port(self, port: str) -> bool:
        return self.serial.connect_serial(port)

    def disconnect_port(self) -> None:
        self.serial.disconnect_serial()

    def is_connected(self) -> bool:
        return self.serial.is_connected()

    def queue_status(self) -> queue.Queue:
        return self.serial.queue_status

    def queue_data(self) -> queue.Queue:
        return self.serial.queue_data

    def trigger_poll(self) -> None:
        if (
            self.is_connected()
            and not self.flag_testing
            and not self.flag_calibrating_flow
        ):
            self.serial.send_command("{D?}")

    # --- Logic Core ---
    def ingest_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        self.last_packet = packet

        raw_flow_lpm: float = packet.get("flow_rate", 0.0)
        raw_flow: float = raw_flow_lpm * 60.0  # LPM to LPH
        raw_press: float = packet.get("pressure", 0.0)
        raw_temp: float = packet.get("temp", 0.0)
        curr_total_vol: float = packet.get("total_volume", 0.0)

        # 1. Math Correction
        val_temp: float = self.calib.get_corrected_value("TEMP", raw_temp)
        val_press: float = self.calib.get_corrected_value("PRESS", raw_press)
        gain_flow: float = self.calib.get_interpolated_gain("FLOW", raw_flow)
        val_flow: float = raw_flow * gain_flow

        # 2. Accumulation (Delta)
        delta_raw: float = curr_total_vol - self.prev_raw_vol
        if delta_raw < 0:
            delta_raw = curr_total_vol  # Reset/Rollover

        delta_corr: float = delta_raw * gain_flow

        if self.flag_testing or self.flag_calibrating_flow:
            self.accumulated_vol += delta_corr

        self.prev_raw_vol = curr_total_vol

        # 3. Buffering
        if self.flag_testing:
            self.test_buffer["flow"].append(val_flow)
            self.test_buffer["press"].append(val_press)
            self.test_buffer["temp"].append(val_temp)
            self.test_final_vol = self.accumulated_vol

        if self.flag_calibrating_flow:
            self.flow_calib_buffer.append(raw_flow)

        target_hit: bool = (
            self.test_target_vol > 0 and self.accumulated_vol >= self.test_target_vol
        )

        return {
            "flow": val_flow,
            "press": val_press,
            "temp": val_temp,
            "raw_temp": raw_temp,
            "raw_press": raw_press,
            "accum_vol": self.accumulated_vol,
            "target_hit": target_hit,
        }

    # --- Test Workflow ---
    def start_test(self, target: float) -> None:
        self.test_target_vol = float(target)
        self.flag_testing = True
        self.test_buffer = {"flow": [], "press": [], "temp": []}
        self.accumulated_vol = 0.0
        self.serial.send_command("{S:1}")

    def stop_test(self) -> None:
        self.serial.send_command("{S:0}")
        self.flag_testing = False

    def finish_test(self, init_m3: float, final_m3: float) -> Dict[str, Any]:
        measured_l: float = (final_m3 - init_m3) * 1000.0
        actual_l: float = self.test_final_vol

        err: float = 0.0
        if actual_l > 0:
            err = ((measured_l - actual_l) / actual_l) * 100.0

        avg_f: float = statistics.mean(self.test_buffer["flow"] or [0])
        avg_p: float = statistics.mean(self.test_buffer["press"] or [0])
        avg_t: float = statistics.mean(self.test_buffer["temp"] or [0])

        rec: Dict[str, Any] = {
            "volume_target": self.test_target_vol,
            "initial_meter": init_m3,
            "final_meter": final_m3,
            "measured_volume": round(measured_l, 3),
            "actual_volume": round(actual_l, 3),
            "error_rate": round(err, 2),
            "avg_flow_rate": round(avg_f, 2),
            "avg_pressure": round(avg_p, 2),
            "avg_temp": round(avg_t, 2),
            "status": "FINISHED",
        }
        self.db.insert_test_log(rec)
        return rec

    # --- History ---
    def get_history(self) -> List[Tuple[Any, ...]]:
        return self.db.fetch_all_test_logs()

    def delete_log(self, lid: int) -> None:
        self.db.delete_test_log(lid)

    # --- Calibration ---
    def start_flow_cal(self) -> None:
        self.flag_calibrating_flow = True
        self.flow_calib_buffer = []
        self.accumulated_vol = 0.0
        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:1,1}")

    def stop_flow_cal(self) -> Tuple[float, float]:
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.flag_calibrating_flow = False

        avg: float = (
            statistics.mean(self.flow_calib_buffer) if self.flow_calib_buffer else 0.0
        )
        return self.last_packet["total_volume"], avg

    def save_point(self, stype: str, raw: float, ref: float) -> None:
        self.db.upsert_calibration_point(stype, raw, ref)

    def calc_save_flow_gain(
        self, ref_vol: Optional[float], ref_rate: Optional[float]
    ) -> Tuple[float, float, float]:
        if self.flow_calib_buffer:
            avg_raw = statistics.mean(self.flow_calib_buffer)
        else:
            avg_raw = self.last_packet["flow_rate"]

        if avg_raw <= 0:
            raise ValueError("Sensor Flow is 0")

        real_ref: float = 0.0
        if ref_rate is not None:
            real_ref = ref_rate
        elif ref_vol is not None:
            curr_vol = self.last_packet["total_volume"]
            if curr_vol <= 0:
                raise ValueError("Sensor Volume 0")
            real_ref = avg_raw * (ref_vol / curr_vol)
        else:
            raise ValueError("No Reference")

        gain = real_ref / avg_raw
        self.db.upsert_calibration_point("FLOW", avg_raw, real_ref)
        return avg_raw, real_ref, gain

    def get_cal_list(self, stype: str) -> List[Tuple[Any, ...]]:
        return self.db.get_calibration_points(stype)

    def get_cal_detail(self, pid: int) -> Optional[Tuple[Any, ...]]:
        return self.db.get_calibration_point_by_id(pid)

    def del_cal_point(self, pid: int) -> None:
        self.db.delete_calibration_point(pid)
