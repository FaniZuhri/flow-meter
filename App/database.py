import sqlite3
from datetime import datetime
import os


class DatabaseManager:
    """
    MODEL: Mengelola struktur data dan interaksi langsung dengan SQLite.
    Menggunakan mekanisme UPSERT untuk manajemen titik kalibrasi yang fleksibel.
    """

    def __init__(self, db_name="water_meter_test.db"):
        self.db_name = db_name
        self._init_db()
        self._init_default_water_meter_points()  # Hanya init titik baku untuk Water Meter

    def _get_connection(self):
        """Helper untuk membuat koneksi database"""
        return sqlite3.connect(self.db_name)

    def _init_db(self):
        """Inisialisasi tabel dengan CONSTRAINT untuk mendukung UPSERT."""
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
        # CONSTRAINT: Kombinasi (sensor_type + reference_value) harus unik.
        # Ini memungkinkan kita melakukan UPSERT.
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
        """
        Menginisialisasi titik kalibrasi standar HANYA untuk Water Meter (FLOW).
        Nilai referensi diambil dari standar debit (Liter/Jam).
        Sensor Suhu dan Tekanan TIDAK disentuh di sini (tetap dinamis).
        """
        # Daftar titik debit standar sesuai referensi db_lib.py
        wm_points = [6, 10, 128, 800, 1000, 1600, 2000, 2500]

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for ref_val in wm_points:
                # INSERT OR IGNORE:
                # Hanya masukkan row baru jika titik referensi ini BELUM ADA.
                # Jika user sudah pernah mengkalibrasi (gain != 1.0), data user TIDAK AKAN ditimpa.
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO calibration_points 
                    (sensor_type, sensor_value, reference_value, gain_factor, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        "FLOW",  # Tipe Sensor Khusus Water Meter
                        ref_val,  # Sensor value awal disamakan dengan ref (ideal)
                        ref_val,  # Anchor Point (Reference Value)
                        1.0,  # Default Gain Factor (Linear/No Error)
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
        """
        Menambah atau Memperbarui titik kalibrasi (UPSERT).

        Logic:
        1. Hitung Gain Factor (Ref / Sensor).
        2. Cek apakah kombinasi (sensor_type, ref_val) sudah ada?
           - YA (Conflict): Update sensor_value, gain, dan timestamp.
           - TIDAK: Insert row baru.
        """
        # Hindari pembagian dengan nol
        if sens_val == 0:
            gain = 1.0
        else:
            gain = ref_val / sens_val

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Query UPSERT SQLite (ON CONFLICT DO UPDATE)
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
            print(
                f"[DB] Upsert Calibration {sensor_type} @ Ref={ref_val}: New Gain={gain:.4f}"
            )
            return True

        except Exception as e:
            print(f"[DB Error] Upsert Calibration: {e}")
            return False
        finally:
            conn.close()

    def get_sorted_calibration_data(self, sensor_type: str) -> tuple[list, list]:
        """
        Mengambil data kalibrasi untuk keperluan interpolasi (NumPy).
        Data harus terurut berdasarkan nilai sensor (X-Axis) agar np.interp bekerja benar.

        Returns:
            (list_x_sensor_values, list_y_gain_factors)
        """
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

            # Memisahkan kolom menjadi dua list terpisah
            x_values = [row[0] for row in rows]
            y_values = [row[1] for row in rows]

            return x_values, y_values

        except Exception as e:
            print(f"[DB Error] Get Sorted Data: {e}")
            return [], []
        finally:
            conn.close()

    def delete_calibration_point(self, sensor_type: str, ref_val: float):
        """
        Menghapus satu titik kalibrasi spesifik berdasarkan tipe dan nilai referensi.
        Berguna jika user ingin menghapus titik kalibrasi suhu/tekanan yang salah.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                DELETE FROM calibration_points 
                WHERE sensor_type = ? AND reference_value = ?
            """,
                (sensor_type, ref_val),
            )
            conn.commit()
            print(f"[DB] Deleted calibration point {sensor_type} @ {ref_val}")
        except Exception as e:
            print(f"[DB Error] Delete Point: {e}")
        finally:
            conn.close()

    def insert_test_log(self, data: dict):
        """Menyimpan log hasil testing."""
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

    def get_all_test_logs(self):
        """Mengambil semua histori log pengujian."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM test_logs ORDER BY id DESC")
            return cursor.fetchall()
        except Exception as e:
            print(f"[DB Error] Get Logs: {e}")
            return []
        finally:
            conn.close()


# Blok testing sederhana (bisa dihapus saat production)
if __name__ == "__main__":
    db = DatabaseManager()

    # Test Upsert Sensor Suhu (Dinamis)
    db.upsert_calibration_point("TEMP", 28.5, 30.0)  # Kali pertama (Insert)
    db.upsert_calibration_point(
        "TEMP", 29.0, 30.0
    )  # Kali kedua di ref yg sama (Update)

    # Test Get Data
    x, y = db.get_sorted_calibration_data("FLOW")
    print(f"Flow Data X: {x}")
    print(f"Flow Data Y: {y}")

    x_temp, y_temp = db.get_sorted_calibration_data("TEMP")
    print(f"Temp Data X: {x_temp}")
    print(f"Temp Data Y: {y_temp}")
