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

extern volatile uint32_t pulse_count, last_captured, pulse_frequency;
extern volatile float flow_rate, total_volume;
extern uint8_t is_test_started;

__STATIC_INLINE void flow_set_test_started(uint8_t val) {
	is_test_started = val;
}

__STATIC_INLINE uint8_t flow_get_test_started(void) {
	return is_test_started;
}

__STATIC_INLINE void flow_set_last_captured(uint32_t val) {
	last_captured = val;
}

__STATIC_INLINE uint32_t flow_get_last_captured(void) {
	return last_captured;
}

__STATIC_INLINE void flow_set_pulse_count(uint32_t count) {
	pulse_count = count;
}

__STATIC_INLINE uint32_t flow_get_pulse_count(void) {
	return pulse_count;
}

__STATIC_INLINE void flow_inc_pulse_count(void) {
	pulse_count += 1;
}

__STATIC_INLINE void flow_set_pulse_frequency(uint32_t freq) {
	pulse_frequency = freq;
}

__STATIC_INLINE uint32_t flow_get_pulse_frequency(void) {
	return pulse_frequency;
}

__STATIC_INLINE void flow_set_flow_rate(float flow) {
	flow_rate = flow;
}

__STATIC_INLINE float flow_get_flow_rate(void) {
	return flow_rate;
}

__STATIC_INLINE void flow_set_total_volume(float volume) {
	total_volume = volume;
}

__STATIC_INLINE float flow_get_total_volume(void) {
	return total_volume;
}

__STATIC_INLINE void flow_inc_total_volume(void) {
	total_volume += PULSE_TO_LITERS;
}

#endif /* INC_UPH_FLOW_SENSOR_H_ */
