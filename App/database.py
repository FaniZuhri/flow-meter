import sqlite3
from datetime import datetime
import os


class DatabaseManager:
    """
    MODEL: Mengelola struktur data dan interaksi langsung dengan SQLite.
    """

    def __init__(self, db_name="water_meter_test.db"):
        self.db_name = db_name
        self._init_db()
        self._init_default_water_meter_points()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. Tabel Log Pengujian
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
                sensor_type TEXT NOT NULL,
                sensor_value REAL, 
                reference_value REAL NOT NULL,
                gain_factor REAL,
                timestamp TEXT,
                CONSTRAINT unique_calibration_point UNIQUE (sensor_type, reference_value)
            )
        """
        )

        conn.commit()
        conn.close()

    def _init_default_water_meter_points(self):
        wm_points = [6, 10, 128, 800, 1000, 1600, 2000, 2500]
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for ref_val in wm_points:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO calibration_points 
                    (sensor_type, sensor_value, reference_value, gain_factor, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        "FLOW",
                        ref_val,
                        ref_val,
                        1.0,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Init WM Points: {e}")
        finally:
            conn.close()

    def upsert_calibration_point(
        self, sensor_type: str, sens_val: float, ref_val: float
    ):
        if sens_val == 0:
            gain = 1.0
        else:
            gain = ref_val / sens_val

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO calibration_points (sensor_type, sensor_value, reference_value, gain_factor, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(sensor_type, reference_value) 
                DO UPDATE SET 
                    sensor_value = excluded.sensor_value,
                    gain_factor = excluded.gain_factor,
                    timestamp = excluded.timestamp
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
            return True
        except Exception as e:
            print(f"[DB Error] Upsert Calibration: {e}")
            return False
        finally:
            conn.close()

    def get_calibration_points(self, sensor_type: str) -> list:
        conn = self._get_connection()
        cursor = conn.cursor()
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
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB Error] Get Cal Points: {e}")
            return []
        finally:
            conn.close()

    def get_calibration_point_by_id(self, point_id: int):
        """
        [NEW] Mengambil detail satu titik kalibrasi berdasarkan ID.
        Digunakan untuk menampilkan detail Gain/Ref saat user memilih dropdown.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, sensor_value, reference_value, gain_factor, timestamp 
                FROM calibration_points 
                WHERE id = ?
            """,
                (point_id,),
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"[DB Error] Get Point by ID: {e}")
            return None
        finally:
            conn.close()

    def get_sorted_calibration_data(self, sensor_type: str) -> tuple[list, list]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT sensor_value, gain_factor 
                FROM calibration_points 
                WHERE sensor_type = ? 
                ORDER BY sensor_value ASC
            """,
                (sensor_type,),
            )
            rows = cursor.fetchall()
            if not rows:
                return [], []
            x_values = [row[0] for row in rows]
            y_values = [row[1] for row in rows]
            return x_values, y_values
        except Exception as e:
            print(f"[DB Error] Get Sorted Data: {e}")
            return [], []
        finally:
            conn.close()

    def delete_calibration_point(self, point_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM calibration_points WHERE id = ?",
                (point_id,),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Delete Point: {e}")
        finally:
            conn.close()

    def insert_test_log(self, data: dict):
        conn = self._get_connection()
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
                    data.get("measured_volume", 0),
                    data.get("actual_volume", 0),
                    data.get("error_rate", 0),
                    data.get("avg_flow_rate", 0),
                    data.get("avg_pressure", 0),
                    data.get("avg_temp", 0),
                    data.get("status", "COMPLETED"),
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Insert Log: {e}")
        finally:
            conn.close()
