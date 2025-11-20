/*
 * tim_handler.c
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */

#include "tim_handler.h"
#include "uph_fsm.h"

TIM_Handler_t h_tim10;
TIM_Handler_t h_tim11;

uint32_t htim10_counter, htim11_counter;

void TIM_Handler_Setup(TIM_Handler_t* htimer, TIM_TypeDef* instance, void (*callback)(void)) {
    if (htimer) {
        htimer->instance = instance;
        htimer->callback = callback;
    }
}

void TIM_Handler_Start(TIM_Handler_t* htimer, uint32_t period_ms) {
    if (htimer && htimer->instance) {
    	LL_TIM_SetAutoReload(htimer->instance, period_ms - 1);
        LL_TIM_EnableIT_UPDATE(htimer->instance);
        LL_TIM_EnableCounter(htimer->instance);
    }
}

void TIM_Handler_Stop(TIM_Handler_t* htimer) {
	if (htimer && htimer->instance) {
		LL_TIM_DisableCounter(htimer->instance);
	}
}

void TIM_Handler_IRQHandler(TIM_Handler_t* htimer) {
    if (LL_TIM_IsActiveFlag_UPDATE(htimer->instance)) {
        LL_TIM_ClearFlag_UPDATE(htimer->instance);

        if (htimer->callback) {
            htimer->callback();
        }
    }
}

void Timer10_Callback(void) {
	htim10_counter++;
	fsm_set_state(FSM_STATE_PERIODIC_SENS_REACHED);
}

void Timer11_Callback(void) {
	htim11_counter++;
}
