# Water Meter Test Kit (WMTK) Prototype

This project is a Python-based GUI application for a Water Meter Test Kit prototype. It interfaces with an STM32 microcontroller via Serial UART to perform automated testing and calibration of water meters.

## Features

- **Real-time Monitoring**: Displays Flow Rate, Pressure, Temperature, and Total Volume.

- **Automated Testing**: Controls solenoid valves and tracks accumulated volume to stop testing at a target volume.

- **Sensor Calibration**:

    - Supports calibration for Flow, Pressure, and Temperature sensors.

    - Uses **Piecewise Linear Interpolation** on Gain Factors for accurate correction across the sensor range.

    - **Differential Volume Correction**: Handles unstable flow rates by calculating volume correction incrementally per data frame.

- **Data Logging**: Saves test results and calibration history to a SQLite database.

- **Simulation Mode**: Includes a "Mock Device" mode to simulate sensor data without hardware.

## Project Structure

- `main.py`: The main application entry point (Controller). Manages UI logic, state, and workflow.

- `app_ui.py`: The generated Python UI file from Qt Designer (`app.ui`).

- `database.py`: Handles all SQLite database interactions (Model).

- `serial_worker.py`: Runs serial communication in a background thread to keep the UI responsive. Supports Mock simulation.

- `calibration_manager.py`: Manages the mathematical logic for sensor error correction (interpolation).

- `resources.qrc` / `resources_rc.py`: Qt resources file containing assets like the app logo.

- `water_meter_test.db`: SQLite database file storing calibration points and test logs.

## Requirements

- Python 3.11+

- PyQt5

- pyserial

- numpy

(See `Pipfile` for exact versions)

## Installation & Usage

1. **Install Dependencies**:

```bash
pipenv install
```


2. **Run the Application**:

```bash
pipenv run python main.py
```


3. **Using Mock Mode (No Hardware)**:

- In the application, select `MOCK_DEVICE` from the port dropdown.

- Click **Connect**.

- Go to **Test** tab or **Calibration** tabs to simulate operations.

## Architecture Notes

- **MVC Pattern**: The app follows a Model-View-Controller design.

- **Robust Volume Calculation**: The system assumes the microcontroller sends a cumulative total volume. The app applies a **differential correction** strategy:

    - `Delta_Vol = Current_Raw_Vol - Previous_Raw_Vol`

    - `Corrected_Delta = Delta_Vol * Gain(Current_Flow_Rate)`

    - This ensures accuracy even if the flow rate fluctuates significantly during a test.

## Author

Fani Zuhri