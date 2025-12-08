/*
 * uph_fsm.c
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */
#include <string.h>
#include <stdio.h>

#include "uph_fsm.h"
#include "uph_flow_sensor.h"
#include "usart_dma_handler.h"
#include "tim_handler.h"
#include "adc_handler.h"
#include "uph_user_data.h"
#include "uph_scp.h"

uint32_t fsm_state;

void fsm_init(void) {
	usart_dma_init();
	FlowSensor_Init(&h_flow_sensor, 500);

	TIM_Handler_Setup(&h_tim11, TIM11, Periodic_Calculation_Callback);

	TIM_Handler_Setup(&h_tim10, TIM10, Timer10_Callback);

	ADC_Handler_Init(&h_adc1, ADC1, DMA2, LL_DMA_STREAM_0);
	ADC_Handler_Register_Callbacks(&h_adc1, On_ADC_Scan_Complete, On_ADC_Overrun);
	ADC_Handler_Start(&h_adc1, TIM2, adc_dma_buffer, ADC_DMA_BUFFER_SIZE);

	UserData_Init(&h_flow_sensor, adc_dma_buffer);
}

void fsm_run(void) {
	if (fsm_is_active_state(FSM_STATE_USER_COMM_RCV_DONE)) {
		scp_handle_set_busy(1);

		if ((int32_t) h_usart1.last_rx_dma_pos - (int32_t) h_usart1.rx_data_len < 0) {
			uint16_t rx_prev_idx = (int32_t) h_usart1.last_rx_dma_pos - (int32_t) h_usart1.rx_data_len + h_usart1.rx_buffer_size;
			memcpy(
					(char *) scp_handle.scp_buf,
					(char *) h_usart1.rx_buffer + rx_prev_idx,
					h_usart1.rx_data_len - h_usart1.last_rx_dma_pos
			);
		}
		else {
			memcpy(
					(char *) scp_handle.scp_buf,
					(char *) h_usart1.rx_buffer + (h_usart1.last_rx_dma_pos - h_usart1.rx_data_len),
					h_usart1.rx_data_len
			);
		}

		scp_cmd_process();

		scp_handle_set_busy(0);
		fsm_reset_state(FSM_STATE_USER_COMM_RCV_DONE);
	}

	if (fsm_is_active_state(FSM_STATE_PERIODIC_PRES_TEMP_REACHED)) {
		fsm_reset_state(FSM_STATE_PERIODIC_PRES_TEMP_REACHED);
	}

	if (fsm_is_active_state(FSM_STATE_SENS_PRES_TEMP_DONE)) {
		fsm_reset_state(FSM_STATE_SENS_PRES_TEMP_DONE);
	}

	if (fsm_is_active_state(FSM_STATE_PERIODIC_SENS_REACHED)) {

//		if (!h_flow_sensor.is_running) {
//			TIM_Handler_Stop(&h_tim11);
//			TIM_Handler_Stop(&h_tim10);
//		}

		scp_user_get_all_data(NULL);

		fsm_reset_state(FSM_STATE_PERIODIC_SENS_REACHED);
	}

	if (fsm_is_active_state(FSM_STATE_IDLE)) {
		fsm_reset_state(FSM_STATE_IDLE);
	}
}

