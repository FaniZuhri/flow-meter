import statistics
from database import DatabaseManager
from calibration_manager import CalibrationManager
from serial_worker import SerialWorker


class MeasurementEngine:
    def __init__(self):
        # Dependencies
        self.db = DatabaseManager()
        self.serial = SerialWorker()
        self.calib_mgr = CalibrationManager(self.db)

        # State Flags
        self.is_testing = False
        self.is_calibrating_flow = False

        # Test Parameters
        self.target_volume = 0.0

        # Accumulators & Buffers
        self.last_process_raw_vol = 0.0
        self.accumulated_corrected_vol = 0.0

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

    # --- Connectivity ---
    def get_ports(self):
        return SerialWorker.get_available_ports()

    def connect(self, port):
        return self.serial.connect_serial(port)

    def disconnect(self):
        self.serial.disconnect_serial()

    def is_connected(self):
        return self.serial.is_connected()

    def get_status_queue(self):
        return self.serial.status_queue

    def get_output_queue(self):
        return self.serial.output_queue

    def send_poll_command(self):
        if self.is_connected() and not self.is_testing and not self.is_calibrating_flow:
            self.serial.send_command("{D?}")

    # --- Data Processing Core ---
    def process_incoming_data(self, raw_data):
        self.latest_raw_data = raw_data

        raw_flow = raw_data.get("flow_rate", 0.0)
        raw_press = raw_data.get("pressure", 0.0)
        raw_temp = raw_data.get("temp", 0.0)
        current_total_raw_vol = raw_data.get("total_volume", 0.0)

        # 1. Apply Calibration Corrections
        corr_temp = self.calib_mgr.get_corrected_value("TEMP", raw_temp)
        corr_press = self.calib_mgr.get_corrected_value("PRESS", raw_press)
        flow_gain = self.calib_mgr.get_interpolated_gain("FLOW", raw_flow)
        corr_flow = raw_flow * flow_gain

        # 2. Logic for Volume Correction (Delta Accumulation)
        delta_raw = current_total_raw_vol - self.last_process_raw_vol

        # Handle rollover or hardware reset
        if delta_raw < 0:
            delta_raw = current_total_raw_vol

        delta_corr = delta_raw * flow_gain

        # 3. Update State Accumulators
        if self.is_testing or self.is_calibrating_flow:
            self.accumulated_corrected_vol += delta_corr

        # Update last processed volume
        self.last_process_raw_vol = current_total_raw_vol

        # 4. Record Buffer Data if Testing
        if self.is_testing:
            self.current_session_data["flow_rate"].append(corr_flow)
            self.current_session_data["pressure"].append(corr_press)
            self.current_session_data["temp"].append(corr_temp)
            self.current_session_data["last_total_volume"] = (
                self.accumulated_corrected_vol
            )

        if self.is_calibrating_flow:
            self.calib_flow_buffer.append(raw_flow)

        return {
            "flow": corr_flow,
            "press": corr_press,
            "temp": corr_temp,
            "raw_temp": raw_temp,
            "raw_press": raw_press,
            "raw_flow": raw_flow,
            "raw_vol": current_total_raw_vol,
            "accum_vol": self.accumulated_corrected_vol,
            "target_reached": (
                self.target_volume > 0
                and self.accumulated_corrected_vol >= self.target_volume
            ),
        }

    # --- Test Logic ---
    def start_test(self, target_vol):
        self.target_volume = float(target_vol)
        self.is_testing = True

        # Reset Session Data
        self.current_session_data = {
            "flow_rate": [],
            "pressure": [],
            "temp": [],
            "last_total_volume": 0.0,
        }
        self.accumulated_corrected_vol = 0.0

        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:1,1}")

    def stop_test(self):
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_testing = False

    def finalize_test_results(self, init_meter, final_meter):
        # Unit Conversion: m3 -> Liters
        measured_vol_m3 = final_meter - init_meter
        measured_vol_liters = measured_vol_m3 * 1000.0

        actual_vol = self.current_session_data["last_total_volume"]

        error_rate = 0.0
        if actual_vol > 0:
            error_rate = ((measured_vol_liters - actual_vol) / actual_vol) * 100

        buff = self.current_session_data

        avg_flow = statistics.mean(buff["flow_rate"]) if buff["flow_rate"] else 0.0
        avg_press = statistics.mean(buff["pressure"]) if buff["pressure"] else 0.0
        avg_temp = statistics.mean(buff["temp"]) if buff["temp"] else 0.0

        log_data = {
            "volume_target": self.target_volume,
            "initial_meter": init_meter,
            "final_meter": final_meter,
            "measured_volume": round(measured_vol_liters, 3),
            "actual_volume": round(actual_vol, 3),
            "error_rate": round(error_rate, 2),
            "avg_flow_rate": round(avg_flow, 2),
            "avg_pressure": round(avg_press, 2),
            "avg_temp": round(avg_temp, 2),
            "status": "FINISHED",
        }

        self.db.insert_test_log(log_data)
        return log_data

    # --- History Logic ---
    def fetch_history(self):
        return self.db.get_all_test_logs()

    def delete_history_item(self, log_id):
        self.db.delete_test_log(log_id)

    # --- Calibration Logic ---
    def start_flow_cal(self):
        self.is_calibrating_flow = True
        self.calib_flow_buffer = []
        self.accumulated_corrected_vol = 0.0
        self.serial.send_command("{S:1}")
        self.serial.send_command("{B:1,1}")

    def stop_flow_cal(self):
        self.serial.send_command("{B:0,0}")
        self.serial.send_command("{S:0}")
        self.is_calibrating_flow = False

        avg_flow = (
            statistics.mean(self.calib_flow_buffer) if self.calib_flow_buffer else 0.0
        )
        return self.latest_raw_data["total_volume"], avg_flow

    def save_calibration(self, sensor_type, raw, ref):
        self.db.upsert_calibration_point(sensor_type, raw, ref)

    def calculate_and_save_flow_cal(self, ref_vol, ref_flow_rate):
        if self.calib_flow_buffer:
            avg_sens_flow = statistics.mean(self.calib_flow_buffer)
        else:
            avg_sens_flow = self.latest_raw_data["flow_rate"]

        if avg_sens_flow <= 0:
            raise ValueError("Sensor Flow is 0")

        real_ref_flow = 0.0
        if ref_flow_rate is not None:
            real_ref_flow = ref_flow_rate
        elif ref_vol is not None:
            raw_vol = self.latest_raw_data["total_volume"]
            if raw_vol <= 0:
                raise ValueError("Sensor Volume is 0")
            real_ref_flow = avg_sens_flow * (ref_vol / raw_vol)
        else:
            raise ValueError("No Reference Provided")

        gain = real_ref_flow / avg_sens_flow
        self.db.upsert_calibration_point("FLOW", avg_sens_flow, real_ref_flow)
        return avg_sens_flow, real_ref_flow, gain

    def get_cal_points(self, sensor_type):
        return self.db.get_calibration_points(sensor_type)

    def get_cal_point_details(self, pid):
        return self.db.get_calibration_point_by_id(pid)

    def delete_cal_point(self, pid):
        self.db.delete_calibration_point(pid)
