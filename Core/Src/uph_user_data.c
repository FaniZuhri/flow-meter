/*
 * uph_user_data.c
 *
 *  Created on: Jun 24, 2025
 *      Author: Hardware2
 */

#include "uph_user_data.h"
#include <math.h>

#define USER_TEMP_SENS_RES_DIVIDER_OHM		50000.0f
#define USER_PRES_SENS_RES_DIVIDER_V_OHM	150.0f
#define USER_PRES_SENS_RES_DIVIDER_IN_OHM	326.0f

#define USER_MAX_SENS_RESOLUTION			4095.0f

#define VOLTAGE_IN							3.3f
#define THERMISTOR_NOMINAL					50000.0f
#define B_COEFFICIENT						3950.0f
#define TEMP_NOMINAL						25.0f
const float VOLTAGE_DIVIDER_FACTOR = ((USER_PRES_SENS_RES_DIVIDER_IN_OHM + USER_PRES_SENS_RES_DIVIDER_V_OHM) / USER_PRES_SENS_RES_DIVIDER_IN_OHM);

UserData_t user_data;

void UserData_Init(FlowSensor_Handler_t* flow_h, uint16_t* adc_buf) {
	user_data.flow_sensor = flow_h;
	user_data.adc_buffer = adc_buf;
	user_data.pres_val_bar = 0;
	user_data.temp_val_celcius = 0;

    for (int i = 0; i < NUM_SOLENOIDS; i++) {
        UserData_SetSolenoidState((Solenoid_ID_t)i, false);
    }
}

void UserData_SetSolenoidState(Solenoid_ID_t solenoid_id, bool new_state) {
    if (solenoid_id >= NUM_SOLENOIDS) {
        return;
    }

    user_data.solenoid_states[solenoid_id] = new_state;

    GPIO_TypeDef* port;
    uint16_t pin;

    if (solenoid_id == SOLENOID_1) {
        port = SOL1_OUT_GPIO_Port;
        pin = SOL1_OUT_Pin;
    } else {
        port = SOL2_OUT_GPIO_Port;
        pin = SOL2_OUT_Pin;
    }

    if (new_state == true) {
        LL_GPIO_SetOutputPin(port, pin);
    } else {
        LL_GPIO_ResetOutputPin(port, pin);
    }
}

bool UserData_GetSolenoidState(Solenoid_ID_t solenoid_id) {
    if (solenoid_id >= NUM_SOLENOIDS) {
        return false;
    }
    return user_data.solenoid_states[solenoid_id];
}

void UserData_Calculate_Temp_Celsius(uint16_t adc_val) {
	float resistance = USER_TEMP_SENS_RES_DIVIDER_OHM * (USER_MAX_SENS_RESOLUTION / (float)adc_val - 1.0);
	float steinhart;

	steinhart = resistance / THERMISTOR_NOMINAL;     // (R/R0)
	steinhart = log(steinhart);                      // ln(R/R0)
	steinhart /= B_COEFFICIENT;                      // (1/B) * ln(R/R0)
	steinhart += 1.0 / (TEMP_NOMINAL + 273.15);      // + (1/T0)
	steinhart = 1.0 / steinhart;                     // Temp in Kelvin
	user_data.temp_val_celcius = steinhart - 273.15;          // Temp in Celsius
}

void UserData_Calculate_Pres_Bar(uint16_t adc_val) {
	float voltage_at_pin = (adc_val / USER_MAX_SENS_RESOLUTION) * VOLTAGE_IN;
	float sensor_voltage = voltage_at_pin * VOLTAGE_DIVIDER_FACTOR;
	float pressure_mpa = (sensor_voltage - 0.5) * (1.6 / 4.0);
	user_data.pres_val_bar = pressure_mpa * 10;
}
