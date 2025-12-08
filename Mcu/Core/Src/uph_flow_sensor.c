/*
 * uph_flow_sensor.c
 *
 *  Created on: Mar 8, 2025
 *      Author: Hardware2
 */

#include "uph_flow_sensor.h"
#include "tim_handler.h"

#define FLOW_SENSOR_CONSTANT 6.6f

FlowSensor_Handler_t h_flow_sensor;

void FlowSensor_Init(FlowSensor_Handler_t* hflow, uint32_t interval_ms) {
    if (!hflow) return;
    hflow->calculation_interval_ms = interval_ms;
    hflow->pulse_count = 0;
    hflow->frequency_hz = 0.0f;
    hflow->flow_rate_lpm = 0.0f;
    hflow->total_volume_liters = 0.0f;
}

void FlowSensor_Process(FlowSensor_Handler_t* hflow) {
    if (!hflow || hflow->calculation_interval_ms == 0) return;

    uint32_t pulses_in_interval;
    NVIC_DisableIRQ(EXTI3_IRQn);
    pulses_in_interval = hflow->pulse_count;
    hflow->pulse_count = 0;
    NVIC_EnableIRQ(EXTI3_IRQn);

    float interval_sec = (float)hflow->calculation_interval_ms / 1000.0f;
    hflow->frequency_hz = (float)pulses_in_interval / interval_sec;

    hflow->flow_rate_lpm = hflow->frequency_hz / FLOW_SENSOR_CONSTANT;

    float interval_min = (float)hflow->calculation_interval_ms / 60000.0f;
    float volume_in_interval = hflow->flow_rate_lpm * interval_min;
    hflow->total_volume_liters += volume_in_interval;
}

float FlowSensor_GetFrequency(FlowSensor_Handler_t* hflow) {
    return hflow->frequency_hz;
}

float FlowSensor_GetFlowRate(FlowSensor_Handler_t* hflow) {
    return hflow->flow_rate_lpm;
}

float FlowSensor_GetTotalVolume(FlowSensor_Handler_t* hflow) {
    return hflow->total_volume_liters;
}

void Periodic_Calculation_Callback(void) {
    FlowSensor_Process(&h_flow_sensor);
}
