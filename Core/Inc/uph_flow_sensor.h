/*
 * flow_sensor.h
 *
 *  Created on: Mar 8, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_FLOW_SENSOR_H_
#define INC_UPH_FLOW_SENSOR_H_

#include "stm32g0xx_ll_system.h"

#define PULSE_TO_LITERS 0.0055  // 1 pulsa = 5.5 mL
#define FLOW_FACTOR 11.0        // Faktor konversi flow rate

uint8_t flow_get_test_started(void);
uint32_t flow_get_pulse_count(void);
void flow_inc_pulse_count(void);
float flow_get_flow_rate(void);

void flow_sensor_start_timer(void);
void flow_sensor_stop_timer(void);
void flow_sensor_reset(void);
void flow_sensor_stop_sensing(void);
void flow_sensor_start_sensing(void);
float flow_sensor_get_volume_litre(float flow_rate);
float flow_sensor_get_speed_litre_min(uint32_t pulse_count);

#endif /* INC_UPH_FLOW_SENSOR_H_ */
