/*
 * tim_handler.h
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */

#ifndef INC_TIM_HANDLER_H_
#define INC_TIM_HANDLER_H_

#include "main.h"
#include <stdbool.h>

typedef struct {
    TIM_TypeDef* instance;
    void (*callback)(void);
} TIM_Handler_t;

extern TIM_Handler_t h_tim10, h_tim11;

void TIM_Handler_Setup(TIM_Handler_t* htimer, TIM_TypeDef* instance, void (*callback)(void));
void TIM_Handler_Start(TIM_Handler_t* htimer, uint32_t period_ms);
void TIM_Handler_Stop(TIM_Handler_t* htimer);
void TIM_Handler_IRQHandler(TIM_Handler_t* htimer);

void Timer10_Callback(void);
void Timer11_Callback(void);

#endif /* INC_TIM_HANDLER_H_ */
