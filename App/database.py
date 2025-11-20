import sqlite3
from datetime import datetime


class DatabaseManager:
    """
    Mengelola koneksi dan operasi database SQLite.
    Menerapkan pola Singleton sederhana melalui pemanggilan instance.
    """

    def __init__(self, db_name="water_meter_test.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """Membuat tabel yang diperlukan jika belum ada."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 1. Tabel Log Pengujian (History Test)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                volume_target REAL,
                initial_meter REAL,
                final_meter REAL,
                actual_volume REAL,
                avg_flow_rate REAL,
                avg_pressure REAL,
                avg_temp REAL,
                status TEXT
            )
        """
        )

        # 2. Tabel Titik Kalibrasi (Calibration Points)
        # sensor_type: 'TEMP', 'PRESS', 'FLOW'
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
        """
        Menyimpan hasil akhir pengujian ke database.

        Args:
            data (dict): Dictionary berisi keys: volume_target, initial_meter,
                         final_meter, actual_volume, avg_flow_rate,
                         avg_pressure, avg_temp, status.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO test_logs (
                    timestamp, volume_target, initial_meter, final_meter, 
                    actual_volume, avg_flow_rate, avg_pressure, avg_temp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data.get("volume_target", 0),
                    data.get("initial_meter", 0),
                    data.get("final_meter", 0),
                    data.get("actual_volume", 0),
                    data.get("avg_flow_rate", 0),
                    data.get("avg_pressure", 0),
                    data.get("avg_temp", 0),
                    data.get("status", "COMPLETED"),
                ),
            )
            conn.commit()
            print("[DB] Test log saved successfully.")
        except Exception as e:
            print(f"[DB] Error saving test log: {e}")
        finally:
            conn.close()

    def add_calibration_point(self, sensor_type: str, sens_val: float, ref_val: float):
        """
        Menghitung Gain Factor dan menyimpannya.
        Rumus: Gain Factor = Reference / Sensor Value

        Args:
            sensor_type (str): 'TEMP', 'PRESS', atau 'FLOW'
            sens_val (float): Nilai bacaan sensor (sebelum kalibrasi)
            ref_val (float): Nilai referensi aktual (termometer/manometer standar)
        """
        if sens_val == 0:
            factor = 0.0
            print("[DB] Warning: Sensor value is 0, gain set to 0.")
        else:
            factor = ref_val / sens_val

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
                    factor,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            print(f"[DB] Calibration point added for {sensor_type}. Gain: {factor:.4f}")
        except Exception as e:
            print(f"[DB] Error adding calibration: {e}")
        finally:
            conn.close()

    def get_calibration_points(self, sensor_type: str) -> list:
        """
        Mengambil list history kalibrasi berdasarkan tipe sensor.
        Digunakan untuk mengisi Dropdown (ComboBox).
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        points = []
        try:
            cursor.execute(
                """
                SELECT id, sensor_value, reference_value, gain_factor 
                FROM calibration_points 
                WHERE sensor_type = ? 
                ORDER BY id DESC
            """,
                (sensor_type,),
            )
            points = cursor.fetchall()
        finally:
            conn.close()
        return points

    def delete_calibration_point(self, point_id: int):
        """Menghapus satu titik kalibrasi berdasarkan ID."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM calibration_points WHERE id = ?", (point_id,))
            conn.commit()
            print(f"[DB] Calibration point {point_id} deleted.")
        finally:
            conn.close()
