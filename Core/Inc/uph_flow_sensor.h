/*
 * uph_flow_sensor.h
 *
 *  Created on: Mar 8, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_FLOW_SENSOR_H_
#define INC_UPH_FLOW_SENSOR_H_

#include "main.h"
#include <stdint.h>

typedef struct {
    volatile uint32_t pulse_count;
    uint32_t calculation_interval_ms;
    uint8_t	is_running;
    float frequency_hz;
    float flow_rate_lpm;
    float total_volume_liters;

} FlowSensor_Handler_t;

extern FlowSensor_Handler_t h_flow_sensor;

void FlowSensor_Init(FlowSensor_Handler_t* hflow, uint32_t interval_ms);
void FlowSensor_Process(FlowSensor_Handler_t* hflow);

float FlowSensor_GetFrequency(FlowSensor_Handler_t* hflow);
float FlowSensor_GetFlowRate(FlowSensor_Handler_t* hflow);
float FlowSensor_GetTotalVolume(FlowSensor_Handler_t* hflow);

void Periodic_Calculation_Callback(void);

__STATIC_INLINE void FlowSensor_Set_Started(FlowSensor_Handler_t *hflow, uint8_t val) {
	if (hflow) {
		hflow->is_running = 1;
	}
}

__STATIC_INLINE void FlowSensor_Pulse_ISR_Handler(FlowSensor_Handler_t* hflow) {
    if (hflow) {
        hflow->pulse_count++;
    }
}

#endif /* INC_UPH_FLOW_SENSOR_H_ */
