/*
 * uph_fsm.c
 *
 *  Created on: May 1, 2025
 *      Author: Hardware2
 */

#include "uph_fsm.h"
#include "uph_scp.h"

volatile fsm_state_t fsm_state;

void fsm_run(void) {
	if (is_active_state(FSM_STATE_LPUART_RCV_DONE)) {
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
}
