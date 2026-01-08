import sqlite3
from datetime import datetime
from typing import List, Tuple, Any, Optional, Dict, Union


## @class DatabaseManager
#  @brief Manages all SQLite database interactions.
#  @details Handles connection pooling, schema initialization, and CRUD operations for logs and calibration data.
class DatabaseManager:

    ## Default filename for the SQLite database.
    DEFAULT_DB_NAME: str = "water_meter_test.db"

    ## @brief Constructor.
    #  @param db_file_path The filesystem path to the database.
    def __init__(self, db_file_path: str = DEFAULT_DB_NAME) -> None:
        self.db_file_path: str = db_file_path
        self._initialize_schema()
        self._seed_defaults()

    ## @brief Establishes a new database connection.
    #  @return sqlite3.Connection object.
    def _create_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_file_path)

    ## @brief Creates tables if they do not exist.
    def _initialize_schema(self) -> None:
        conn: sqlite3.Connection = self._create_connection()
        cursor: sqlite3.Cursor = conn.cursor()

        # Table: Test Logs
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

        # Table: Calibration Points
        # Enforce unique constraint to prevent duplicate raw values for the same sensor
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT,
                raw_value REAL,
                reference_value REAL,
                gain_factor REAL,
                timestamp TEXT,
                UNIQUE(sensor_type, raw_value)
            )
        """
        )
        conn.commit()
        conn.close()

    ## @brief Inserts default data if the database is empty.
    def _seed_defaults(self) -> None:
        if not self.get_calibration_points("FLOW"):
            self.upsert_calibration_point("FLOW", 0.0, 0.0)
            # Default 1:1 slope reference
            self.upsert_calibration_point("FLOW", 100.0, 100.0)

    # --- Calibration Methods ---

    ## @brief Inserts or Updates a calibration point.
    #  @details Automatically calculates Gain = Reference / Raw.
    def upsert_calibration_point(
        self, sensor_type: str, raw_val: float, ref_val: float
    ) -> None:
        gain: float = 1.0
        if raw_val != 0.0:
            gain = ref_val / raw_val

        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO calibration_points (sensor_type, raw_value, reference_value, gain_factor, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(sensor_type, raw_value) DO UPDATE SET
                    reference_value=excluded.reference_value,
                    gain_factor=excluded.gain_factor,
                    timestamp=excluded.timestamp
            """,
                (sensor_type, raw_val, ref_val, gain, timestamp),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Upsert Calibration: {e}")
        finally:
            conn.close()

    ## @brief Fetches all calibration points for a sensor, sorted by raw value.
    def get_calibration_points(self, sensor_type: str) -> List[Tuple[Any, ...]]:
        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM calibration_points WHERE sensor_type = ? ORDER BY raw_value ASC",
                (sensor_type,),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    ## @brief Fetches a single calibration point by its primary key ID.
    def get_calibration_point_by_id(self, point_id: int) -> Optional[Tuple[Any, ...]]:
        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calibration_points WHERE id = ?", (point_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    ## @brief Deletes a calibration point by ID.
    def delete_calibration_point(self, point_id: int) -> None:
        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM calibration_points WHERE id = ?", (point_id,))
            conn.commit()
        finally:
            conn.close()

    # --- Test Log Methods ---

    ## @brief Records a finished test session.
    def insert_test_log(self, data: Dict[str, Any]) -> None:
        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO test_logs (
                    timestamp, volume_target, initial_meter, final_meter, measured_volume,
                    actual_volume, error_rate, avg_flow_rate, avg_pressure, avg_temp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data.get("volume_target", 0.0),
                    data.get("initial_meter", 0.0),
                    data.get("final_meter", 0.0),
                    data.get("measured_volume", 0.0),
                    data.get("actual_volume", 0.0),
                    data.get("error_rate", 0.0),
                    data.get("avg_flow_rate", 0.0),
                    data.get("avg_pressure", 0.0),
                    data.get("avg_temp", 0.0),
                    data.get("status", "UNKNOWN"),
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB Error] Insert Log: {e}")
        finally:
            conn.close()

    ## @brief Retrieves all test history, newest first.
    def fetch_all_test_logs(self) -> List[Tuple[Any, ...]]:
        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_logs ORDER BY id DESC")
            return cursor.fetchall()
        finally:
            conn.close()

    ## @brief Deletes a test log entry by ID.
    def delete_test_log(self, log_id: int) -> None:
        conn: sqlite3.Connection = self._create_connection()
        try:
            cursor: sqlite3.Cursor = conn.cursor()
            cursor.execute("DELETE FROM test_logs WHERE id = ?", (log_id,))
            conn.commit()
        finally:
            conn.close()
