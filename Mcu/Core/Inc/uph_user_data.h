/*
 * uph_user_data.h
 *
 *  Created on: Jun 24, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_USER_DATA_H_
#define INC_UPH_USER_DATA_H_

#include "uph_flow_sensor.h"
#include <stdbool.h>
#include <stdint.h>

#define NUM_SOLENOIDS 2

typedef enum {
    SOLENOID_1 = 0,
    SOLENOID_2 = 1
} Solenoid_ID_t;

typedef struct {
    FlowSensor_Handler_t* flow_sensor;
    uint16_t* adc_buffer;
    float temp_val_celcius;
    float pres_val_bar;
    bool solenoid_states[NUM_SOLENOIDS];
} UserData_t;

extern UserData_t user_data;

void UserData_Init(FlowSensor_Handler_t* flow_h, uint16_t* adc_buf);
void UserData_SetSolenoidState(Solenoid_ID_t solenoid_id, bool new_state);
bool UserData_GetSolenoidState(Solenoid_ID_t solenoid_id);

void UserData_Calculate_Temp_Celsius(uint16_t adc_val);
void UserData_Calculate_Pres_Bar(uint16_t adc_val);

#endif /* INC_UPH_USER_DATA_H_ */
