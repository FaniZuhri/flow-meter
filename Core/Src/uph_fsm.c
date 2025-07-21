/*
 * uph_fsm.c
 *
 *  Created on: May 1, 2025
 *      Author: Hardware2
 */

#include "dma.h"
#include "adc.h"
#include "gpio.h"
#include "usart.h"

#include "uph_fsm.h"
#include "uph_scp.h"
#include "uph_user_data.h"
#include "uph_flow_sensor.h"
#include <string.h>

uint32_t fsm_state;

void fsm_run(void) {
	if (fsm_is_active_state(FSM_STATE_LPUART_RCV_DONE)) {
		LL_DMA_DisableChannel(DMA1, LL_DMA_CHANNEL_2);
		scp_handle_set_busy(1);

		memcpy(
				(char *) scp_handle.scp_buf,
				(char *) lpuart_rx_buf,
				LPUART_RX_DATA_SIZE - LL_DMA_GetDataLength(DMA1, LL_DMA_CHANNEL_2)
		);

		scp_cmd_process();

		lpuart_dma_receive();

		fsm_reset_state(FSM_STATE_LPUART_RCV_DONE);
		scp_handle_set_busy(0);
	}

	if (fsm_is_active_state(FSM_STATE_PERIODIC_PRES_TEMP_REACHED)) {
		user_start_adc();

		fsm_reset_state(FSM_STATE_PERIODIC_PRES_TEMP_REACHED);
	}

	if (fsm_is_active_state(FSM_STATE_SENS_PRES_TEMP_DONE)) {
//		I think stop the dma would be optional since its periodically called
		adc_dma_stop();
//		TODO: get ADC data from sen_buf. make sure the data is valid
		user_data.pressure_sensor = sen_buf[SEN_ID_PRESSURE];
		user_data.temp_sensor = sen_buf[SEN_ID_TEMP];

		fsm_reset_state(FSM_STATE_SENS_PRES_TEMP_DONE);
	}

	if (fsm_is_active_state(FSM_STATE_PERIODIC_SENS_REACHED)) {
		flow_sensor_stop_timer();
		
		user_data.speed = flow_sensor_get_speed_litre_min(flow_get_pulse_count());
		user_data.volume = flow_sensor_get_volume_litre(flow_get_flow_rate());

//		TODO: get user_data to be sent via uart, and then send them
		scp_user_get_all_data(NULL);

		user_start_sensors_timer();
		flow_sensor_start_timer();

		fsm_reset_state(FSM_STATE_PERIODIC_SENS_REACHED);
	}

	if (fsm_is_active_state(FSM_STATE_IDLE)) {
		if (user_data.solenoid_state) {
			LL_GPIO_ResetOutputPin(SOL1_OUT_GPIO_Port, SOL1_OUT_Pin);
			user_data.solenoid_state = 0;
		}
		fsm_reset_state(FSM_STATE_IDLE);
	}
}
