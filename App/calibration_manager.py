import numpy as np
from database import DatabaseManager
from typing import Union, List, Tuple


## @class CalibrationManager
#  @brief Manages sensor value correction logic.
#
#  This class uses Piecewise Linear Interpolation on the Gain Factor.
#  Instead of interpolating the reading directly to the reference value,
#  the system interpolates the multiplier (Gain) to accommodate
#  non-linear sensor characteristics.
class CalibrationManager:

    ## List of supported sensor type constants.
    #  Must be synchronized with the strings sent from main.py.
    SUPPORTED_SENSORS = ("FLOW", "TEMP", "PRESS")

    ## @brief Constructor.
    #  @param db_manager Instance of DatabaseManager to fetch calibration data.
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    ## @brief Calculates the interpolated Gain Factor for the current raw value.
    #
    #  Uses linear interpolation algorithm (numpy.interp).
    #  If the raw value is outside the calibration range, the function will perform
    #  "clamping" (using the gain from the nearest point).
    #
    #  @param sensor_type Sensor type ("FLOW", "TEMP", "PRESS").
    #  @param current_raw_value Raw value from the sensor.
    #  @return Float Gain Factor. Defaults to 1.0 if no data exists.
    def get_interpolated_gain(
        self, sensor_type: str, current_raw_value: Union[float, int]
    ) -> float:

        if sensor_type not in self.SUPPORTED_SENSORS:
            # Safe fallback for unknown sensor types
            return 1.0

        # 1. Fetch sorted calibration data (X=Raw, Y=Gain) from DB
        x_points, y_points = self.db.get_sorted_calibration_data(sensor_type)

        # 2. If database is empty for this sensor, return default gain 1.0 (pass-through)
        if not x_points:
            return 1.0

        # 3. Convert to numpy array for computational efficiency
        xp = np.array(x_points, dtype=float)  # X-Axis: Raw Sensor Value
        fp = np.array(y_points, dtype=float)  # Y-Axis: Gain Factor

        # 4. Perform Linear Interpolation
        # np.interp automatically handles flat extrapolation (clamping)
        interpolated_gain = np.interp(current_raw_value, xp, fp)

        return float(interpolated_gain)

    ## @brief Calculates the corrected value.
    #
    #  Formula: Corrected = Raw * G(Raw)
    #  Where G(Raw) is the gain factor obtained from interpolation.
    #
    #  @param sensor_type Sensor type.
    #  @param current_raw_value Raw value.
    #  @return Float Corrected value.
    def get_corrected_value(
        self, sensor_type: str, current_raw_value: Union[float, int]
    ) -> float:
        # Get dynamic gain
        gain = self.get_interpolated_gain(sensor_type, current_raw_value)

        # Apply correction
        corrected_value = current_raw_value * gain

        return corrected_value
