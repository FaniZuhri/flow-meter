/*
 * usart_dma_handler.c
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */

#include <string.h>

#include "usart_dma_handler.h"
#include "uph_fsm.h"

USART_DMA_Handler_t h_usart1;
USART_DMA_Handler_t h_usart6;

uint8_t usart1_rx_buffer[USART_BUFFER_SIZE];
uint8_t usart1_tx_buffer[USART_BUFFER_SIZE];
uint8_t usart6_tx_buffer[USART_BUFFER_SIZE];

uint8_t app_rx_buffer[USART_BUFFER_SIZE];

void usart_dma_start(USART_DMA_Handler_t* huart) {
    huart->tx_cplt_flag = true;
    huart->rx_data_len = 0;
    huart->last_rx_dma_pos = 0;

    // Activates only necessary interrupts
    if (huart->dma_rx_stream != 0) {
		LL_USART_EnableIT_IDLE(huart->usart_instance);

		LL_DMA_SetPeriphAddress(huart->dma_instance, huart->dma_rx_stream, LL_USART_DMA_GetRegAddr(huart->usart_instance));
		LL_DMA_SetMemoryAddress(huart->dma_instance, huart->dma_rx_stream, (uint32_t) huart->rx_buffer);
		LL_DMA_SetDataLength(huart->dma_instance, huart->dma_rx_stream, huart->rx_buffer_size);
		LL_USART_EnableDMAReq_RX(huart->usart_instance);

		LL_DMA_EnableStream(huart->dma_instance, huart->dma_rx_stream);
    }

    if (huart->dma_tx_stream != 0) {
		LL_DMA_SetPeriphAddress(huart->dma_instance, huart->dma_tx_stream, LL_USART_DMA_GetRegAddr(huart->usart_instance));
		LL_DMA_EnableIT_TC(huart->dma_instance, huart->dma_tx_stream);
		LL_DMA_EnableIT_TE(huart->dma_instance, huart->dma_tx_stream);
    }
}

ErrorStatus usart_dma_transmit(USART_DMA_Handler_t* huart, const uint8_t* data, uint16_t len) {
    if (!huart->tx_cplt_flag || huart->dma_tx_stream == 0) {
        return ERROR;
    }
    huart->tx_cplt_flag = false;

    uint16_t len_to_copy = (len < huart->tx_buffer_size) ? len : huart->tx_buffer_size;
    memcpy(huart->tx_buffer, data, len_to_copy);

    LL_DMA_DisableStream(huart->dma_instance, huart->dma_tx_stream);

    LL_DMA_SetDataLength(huart->dma_instance, huart->dma_tx_stream, len_to_copy);
    LL_DMA_SetMemoryAddress(huart->dma_instance, huart->dma_tx_stream, (uint32_t) huart->tx_buffer);
    LL_USART_EnableDMAReq_TX(huart->usart_instance);

    LL_DMA_EnableStream(huart->dma_instance, huart->dma_tx_stream);

    while(!huart->tx_cplt_flag) __NOP();

    return SUCCESS;
}

void usart_dma_tx_isr_handler(USART_DMA_Handler_t* huart) {
    LL_USART_DisableDMAReq_TX(huart->usart_instance);
    LL_DMA_DisableStream(huart->dma_instance, huart->dma_tx_stream);
    huart->tx_cplt_flag = true;
}

void usart_idle_line_isr_handler(USART_DMA_Handler_t* huart) {
    uint16_t current_dma_pos = huart->rx_buffer_size - LL_DMA_GetDataLength(huart->dma_instance, huart->dma_rx_stream);

    if (current_dma_pos != huart->last_rx_dma_pos) {
        if (current_dma_pos > huart->last_rx_dma_pos) {
            huart->rx_data_len = current_dma_pos - huart->last_rx_dma_pos;
        } else {
            huart->rx_data_len = huart->rx_buffer_size - huart->last_rx_dma_pos + current_dma_pos;
        }
        fsm_set_state(FSM_STATE_USER_COMM_RCV_DONE);
    }
    huart->last_rx_dma_pos = current_dma_pos;
}

void usart_dma_init(void) {
    h_usart1.usart_instance = USART1;
    h_usart1.dma_instance   = DMA2;
    h_usart1.dma_rx_stream  = LL_DMA_STREAM_2;
    h_usart1.dma_tx_stream  = LL_DMA_STREAM_7;
    h_usart1.rx_buffer      = usart1_rx_buffer;
    h_usart1.rx_buffer_size = sizeof(usart1_rx_buffer);
    h_usart1.tx_buffer      = usart1_tx_buffer;
    h_usart1.tx_buffer_size = sizeof(usart1_tx_buffer);
    usart_dma_start(&h_usart1);

    h_usart6.usart_instance = USART6;
    h_usart6.dma_instance   = DMA2;
    h_usart6.dma_tx_stream  = LL_DMA_STREAM_6;
    h_usart6.dma_rx_stream  = 0;
    h_usart6.tx_buffer      = usart6_tx_buffer;
    h_usart6.tx_buffer_size = sizeof(usart6_tx_buffer);
    usart_dma_start(&h_usart6);
}
