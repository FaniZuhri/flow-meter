# main_wmtk.py (hanya contoh penggunaan)

from database import DatabaseManager
from calibration_manager import CalibrationManager


def simulate_wmtk_run():
    # 1. Setup
    db = DatabaseManager()
    calib_mgr = CalibrationManager(db)

    print("--- Inisialisasi & Kalibrasi ---")

    # Kalibrasi FLOW: Mengupdate titik baku (debit 1000 L/h)
    # Ref=1000, Sensor baca 995 -> Gain harus > 1
    db.upsert_calibration_point("FLOW", sens_val=798.0, ref_val=800.0)
    # Kalibrasi TEMP: Menambah titik dinamis (Ref 30.0C)
    # Ref=30.0, Sensor baca 28.0 -> Gain harus > 1
    db.upsert_calibration_point("TEMP", sens_val=19.0, ref_val=20.0)

    print("\n--- Simulasi Pembacaan Real-Time ---")

    # 2. Kasus A: Pembacaan Flow (Interpolasi)
    raw_flow_reading = 500.0  # Di antara titik 128 dan 995
    corrected_flow = calib_mgr.get_corrected_value("FLOW", raw_flow_reading)
    print(f"Flow RAW: {raw_flow_reading:.2f} L/h")
    print(f"Flow CORR: {corrected_flow:.2f} L/h")
    # Hasil: corrected_flow akan mendekati raw_flow_reading karena 500 masih di tengah range 1.0 gain default.

    # 3. Kasus B: Pembacaan Temperature (Clamping/Interpolasi)
    raw_temp_reading = 29.0  # Mendekati titik kalibrasi 28.0
    corrected_temp = calib_mgr.get_corrected_value("TEMP", raw_temp_reading)
    print(f"Temp RAW: {raw_temp_reading:.2f} C")
    print(f"Temp CORR: {corrected_temp:.2f} C")
    # Hasil: corrected_temp akan lebih tinggi dari 29.0, mendekati 30.0 karena gain > 1


if __name__ == "__main__":
    simulate_wmtk_run()
