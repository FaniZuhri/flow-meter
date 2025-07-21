/*
 * flow_sensor.c
 *
 *  Created on: Mar 8, 2025
 *      Author: Hardware2
 */

#include "uph_flow_sensor.h"
#include "lptim.h"

#define FLOW_SENSOR_SENSING_TIME_MS		999U

volatile uint32_t pulse_count = 0;
volatile float flow_rate = 0.0;
volatile float total_volume = 0.0;
volatile uint32_t last_captured = 0;
volatile uint32_t pulse_frequency = 0;

/**
 * @note volume litre divisor
 * sampling period (seconds) / 60 seconds -> since speed is in litre per minute
 */
const uint32_t volume_litre_divisor = ((FLOW_SENSOR_SENSING_TIME_MS + 1) / 1000) / 60;
uint8_t is_test_started = 0;

void flow_set_test_started(uint8_t val) {
	is_test_started = val;
}

uint8_t flow_get_test_started(void) {
	return is_test_started;
}

void flow_set_last_captured(uint32_t val) {
	last_captured = val;
}

uint32_t flow_get_last_captured(void) {
	return last_captured;
}

void flow_set_pulse_count(uint32_t count) {
	pulse_count = count;
}

uint32_t flow_get_pulse_count(void) {
	return pulse_count;
}

void flow_inc_pulse_count(void) {
	pulse_count += 1;
}

void flow_set_pulse_frequency(uint32_t freq) {
	pulse_frequency = freq;
}

uint32_t flow_get_pulse_frequency(void) {
	return pulse_frequency;
}

void flow_set_flow_rate(float flow) {
	flow_rate = flow;
}

float flow_get_flow_rate(void) {
	return flow_rate;
}

void flow_set_total_volume(float volume) {
	total_volume = volume;
}

float flow_get_total_volume(void) {
	return total_volume;
}

void flow_inc_total_volume(float volume) {
	total_volume += volume;
}

void flow_sensor_start_timer(void) {
	LL_LPTIM_SetCompare(LPTIM1, FLOW_SENSOR_SENSING_TIME_MS);
	LL_LPTIM_Enable(LPTIM1);
	LL_LPTIM_StartCounter(LPTIM1, LL_LPTIM_OPERATING_MODE_ONESHOT);
}

void flow_sensor_stop_timer(void) {
	LL_LPTIM_Disable(LPTIM1);
}

float flow_sensor_get_speed_litre_min(uint32_t pulse_count) {
	flow_set_pulse_frequency(pulse_count * (1 / ((FLOW_SENSOR_SENSING_TIME_MS + 1) * 1000)));
	flow_set_flow_rate(flow_get_pulse_frequency() / FLOW_FACTOR);

	return flow_get_flow_rate();
}

float flow_sensor_get_volume_litre(float flow_rate) {
	// Calculate total volume in litres based on flow rate and the divisor
	float current_volume = 0;

	if (flow_rate > 0) {
		current_volume = flow_rate / volume_litre_divisor;
	}

	flow_inc_total_volume(current_volume);

	return flow_get_total_volume();
}

void flow_sensor_start_sensing(void) {
	flow_sensor_start_timer();
	flow_set_pulse_count(0);
	flow_set_flow_rate(0.0);
	flow_set_test_started(1);
}

void flow_sensor_stop_sensing(void) {
	flow_sensor_stop_timer();
	flow_set_test_started(0);
}

void flow_sensor_reset(void) {
	flow_set_pulse_count(0);
	flow_set_flow_rate(0.0);
	flow_set_total_volume(0.0);
}
