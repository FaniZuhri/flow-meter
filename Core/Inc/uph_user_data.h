/*
 * uph_user_data.h
 *
 *  Created on: Jun 5, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_USER_DATA_H_
#define INC_UPH_USER_DATA_H_

typedef struct user_data_s {
	uint8_t solenoid_state;
	float pressure_sensor;
	float temp_sensor;
	float volume;
	float speed;
} user_data_t;

extern user_data_t user_data;

__STATIC_INLINE void user_data_reset(void) {
	user_data.pressure_sensor = 0;
	user_data.speed = 0;
	user_data.temp_sensor = 0;
	user_data.volume = 0;
}

#endif /* INC_UPH_USER_DATA_H_ */
