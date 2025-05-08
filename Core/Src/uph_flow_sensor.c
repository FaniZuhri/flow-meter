/*
 * flow_sensor.c
 *
 *  Created on: Mar 8, 2025
 *      Author: Hardware2
 */

#include "uph_flow_sensor.h"

volatile uint32_t pulse_count = 0;
volatile float flow_rate = 0.0;
volatile float total_volume = 0.0;
volatile uint32_t last_captured = 0;
volatile uint32_t pulse_frequency = 0;

uint8_t is_test_started = 0;
