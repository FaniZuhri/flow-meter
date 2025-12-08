import numpy as np
from database import DatabaseManager
from typing import Union, List, Tuple


class CalibrationManager:
    """
    Menangani logika koreksi nilai sensor menggunakan interpolasi linear
    berdasarkan data gain factor yang tersimpan di database.

    Logic: Corrected Value = Raw Value * Interpolated Gain Factor
    """

    # Tipe sensor yang didukung (Disesuaikan dengan string di main.py)
    # "PRESS" digunakan di main.py, bukan "PRESSURE"
    SUPPORTED_SENSORS = ("FLOW", "TEMP", "PRESS")

    def __init__(self, db_manager: DatabaseManager):
        """
        Inisialisasi dengan instance DatabaseManager.
        """
        self.db = db_manager

    def get_interpolated_gain(
        self, sensor_type: str, current_raw_value: Union[float, int]
    ) -> float:
        """
        Mencari Gain Factor yang tepat untuk nilai sensor saat ini menggunakan Interpolasi Linear.
        """
        if sensor_type not in self.SUPPORTED_SENSORS:
            # Debugging opsional, bisa di-comment jika mengganggu
            # print(f"[Calib Error] Sensor type '{sensor_type}' not supported.")
            return 1.0

        # 1. Ambil data titik kalibrasi yang sudah diurutkan dari database
        # x_points: Nilai Sensor Raw; y_points: Gain Factor
        x_points, y_points = self.db.get_sorted_calibration_data(sensor_type)

        # 2. Jika tidak ada data kalibrasi sama sekali, gunakan Gain default (1.0)
        if not x_points:
            return 1.0

        # 3. Konversi ke numpy array untuk performa interpolasi
        xp = np.array(
            x_points, dtype=float
        )  # Sumbu X: Nilai Sensor Raw (Titik kalibrasi)
        fp = np.array(y_points, dtype=float)  # Sumbu Y: Gain Factor (Titik kalibrasi)

        # 4. Lakukan Interpolasi Linear menggunakan numpy.interp
        interpolated_gain = np.interp(current_raw_value, xp, fp)

        return float(interpolated_gain)

    def get_corrected_value(
        self, sensor_type: str, current_raw_value: Union[float, int]
    ) -> float:
        """
        Menghitung nilai sensor terkoreksi menggunakan Gain Factor hasil interpolasi.
        """
        # Dapatkan Gain Factor dinamis
        gain = self.get_interpolated_gain(sensor_type, current_raw_value)

        # Hitung Nilai Koreksi
        corrected_value = current_raw_value * gain

        return corrected_value
