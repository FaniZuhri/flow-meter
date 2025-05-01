/*
 * uph_fsm.h
 *
 *  Created on: May 1, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_FSM_H_
#define INC_UPH_FSM_H_

#include "stm32g0xx_ll_system.h"
#include "stm32g0xx_ll_pwr.h"
#include "stm32g0xx_ll_cortex.h"

typedef enum fsm_state_e {
	FSM_STATE_IDLE,
	FSM_STATE_LPUART_RCV_DONE,
	FSM_STATE_SENS_INC_COUNTER,
} fsm_state_t;

extern volatile fsm_state_t fsm_state;

__STATIC_INLINE void fsm_set_state(fsm_state_t state) {
	fsm_state |= (1 << state);
}

__STATIC_INLINE void fsm_reset_state(fsm_state_t state) {
	fsm_state &= ~(1 << state);
}

__STATIC_INLINE fsm_state_t fsm_get_state(void) {
	return fsm_state;
}

__STATIC_INLINE uint8_t is_active_state(fsm_state_t state) {
	return fsm_get_state() & (1 << state);
}

void fsm_run(void);

#endif /* INC_UPH_FSM_H_ */
