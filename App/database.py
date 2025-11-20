import sqlite3
from datetime import datetime


class DatabaseManager:
    """
    MODEL: Mengelola struktur data dan interaksi langsung dengan SQLite.
    """

    def __init__(self, db_name="water_meter_test.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """Inisialisasi tabel jika belum ada."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 1. Tabel Log Pengujian (Test Logs)
        # UPDATE: Menambahkan kolom 'error_rate'
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                volume_target REAL,
                initial_meter REAL,
                final_meter REAL,
                measured_volume REAL,
                actual_volume REAL,
                error_rate REAL,
                avg_flow_rate REAL,
                avg_pressure REAL,
                avg_temp REAL,
                status TEXT
            )
        """
        )

        # 2. Tabel Titik Kalibrasi
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT,
                sensor_value REAL,
                reference_value REAL,
                gain_factor REAL,
                timestamp TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def insert_test_log(self, data: dict):
        """Menyimpan hasil pengujian."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO test_logs (
                    timestamp, volume_target, initial_meter, final_meter, measured_volume,
                    actual_volume, error_rate, avg_flow_rate, avg_pressure, avg_temp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data.get("volume_target", 0),
                    data.get("initial_meter", 0),
                    data.get("final_meter", 0),
                    data.get(
                        "measured_volume", 0
                    ),  # Volume hasil bacaan meter (Final - Initial)
                    data.get("actual_volume", 0),  # Volume dari Sensor MCU
                    data.get("error_rate", 0),  # Persentase Error
                    data.get("avg_flow_rate", 0),
                    data.get("avg_pressure", 0),
                    data.get("avg_temp", 0),
                    data.get("status", "COMPLETED"),
                ),
            )
            conn.commit()
            print("[DB] Test result saved with Error Rate.")
        except Exception as e:
            print(f"[DB Error] Insert Log: {e}")
        finally:
            conn.close()

    def add_calibration_point(self, sensor_type: str, sens_val: float, ref_val: float):
        if sens_val == 0:
            gain = 0.0
        else:
            gain = ref_val / sens_val

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO calibration_points (sensor_type, sensor_value, reference_value, gain_factor, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    sensor_type,
                    sens_val,
                    ref_val,
                    gain,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Add Calibration: {e}")
        finally:
            conn.close()

    def get_calibration_points(self, sensor_type: str) -> list:
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        data = []
        try:
            cursor.execute(
                """
                SELECT id, sensor_value, reference_value, gain_factor, timestamp 
                FROM calibration_points 
                WHERE sensor_type = ? 
                ORDER BY id DESC
            """,
                (sensor_type,),
            )
            data = cursor.fetchall()
        finally:
            conn.close()
        return data

    def delete_calibration_point(self, point_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM calibration_points WHERE id = ?", (point_id,))
            conn.commit()
        finally:
            conn.close()
