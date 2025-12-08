/*
 * uph_fsm.h
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_FSM_H_
#define INC_UPH_FSM_H_

#include "main.h"

typedef enum fsm_state_e {
	FSM_STATE_IDLE,
	FSM_STATE_USER_COMM_RCV_DONE,
	FSM_STATE_SENS_INC_COUNTER,
	FSM_STATE_SENS_PRES_TEMP_DONE,
	FSM_STATE_PERIODIC_SENS_REACHED,
	FSM_STATE_PERIODIC_PRES_TEMP_REACHED,
} fsm_state_t;

extern uint32_t fsm_state;

__STATIC_INLINE void fsm_set_state(fsm_state_t state) {
	fsm_state |= (1 << state);
}

__STATIC_INLINE void fsm_reset_state(fsm_state_t state) {
	fsm_state &= ~(1 << state);
}

__STATIC_INLINE fsm_state_t fsm_get_state(void) {
	return fsm_state;
}

__STATIC_INLINE uint8_t fsm_is_active_state(fsm_state_t state) {
	return fsm_get_state() & (1 << state);
}

void fsm_run(void);
void fsm_init(void);

#endif /* INC_UPH_FSM_H_ */
