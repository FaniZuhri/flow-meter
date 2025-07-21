/*
 * uph_user_data.c
 *
 *  Created on: Jun 5, 2025
 *      Author: Hardware2
 */

#include "gpio.h"
#include "lptim.h"
#include "adc.h"

#include "uph_user_data.h"

user_data_t user_data = {
		.pressure_sensor = 0,
		.solenoid_state = 0,
		.speed = 0,
		.temp_sensor = 0,
		.volume = 0
};

