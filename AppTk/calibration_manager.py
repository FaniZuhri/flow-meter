import numpy as np
from typing import List, Tuple
from database import DatabaseManager


## @class CalibrationManager
#  @brief Provides corrected sensor values using piecewise linear interpolation.
class CalibrationManager:

    ## Supported sensor types matching DB keys.
    SUPPORTED_TYPES: Tuple[str, ...] = ("FLOW", "TEMP", "PRESS")

    ## @brief Constructor.
    #  @param db_instance Reference to the DatabaseManager.
    def __init__(self, db_instance: DatabaseManager) -> None:
        self.db: DatabaseManager = db_instance

    ## @brief Loads calibration curve (Raw vs Gain) from DB.
    #  @return Tuple containing (X_Array, Y_Array) for interpolation.
    def _load_curve(self, sensor_type: str) -> Tuple[List[float], List[float]]:
        rows = self.db.get_calibration_points(sensor_type)
        if not rows:
            return [], []

        # Row index 2 = Raw Value, Index 4 = Gain Factor
        x_vals: List[float] = [float(r[2]) for r in rows]
        y_vals: List[float] = [float(r[4]) for r in rows]
        return x_vals, y_vals

    ## @brief Computes the gain factor for a specific raw reading.
    def get_interpolated_gain(self, sensor_type: str, raw_val: float) -> float:
        if sensor_type not in self.SUPPORTED_TYPES:
            return 1.0

        x_pts, y_pts = self._load_curve(sensor_type)
        if not x_pts:
            return 1.0

        # Use NumPy for efficient linear interpolation with boundary clamping
        gain: float = float(np.interp(raw_val, x_pts, y_pts))
        return gain

    ## @brief Returns the final corrected physical value.
    #  @details Corrected = Raw * Gain(Raw)
    def get_corrected_value(self, sensor_type: str, raw_val: float) -> float:
        gain: float = self.get_interpolated_gain(sensor_type, raw_val)
        return raw_val * gain
