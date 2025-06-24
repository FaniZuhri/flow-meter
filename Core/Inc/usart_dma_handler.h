/*
 * usart_dma_handler.h
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */

#ifndef INC_USART_DMA_HANDLER_H_
#define INC_USART_DMA_HANDLER_H_

#include "main.h"
#include <stdbool.h>
#include <stdint.h>

#define USART_BUFFER_SIZE	128U

typedef struct {
    // Peripheral instance (from CubeMX)
    USART_TypeDef* usart_instance;
    DMA_TypeDef* dma_instance;
    uint32_t       dma_rx_stream;
    uint32_t       dma_tx_stream;

    // Buffer (provided from user)
    uint8_t* rx_buffer;
    uint16_t rx_buffer_size;
    uint8_t* tx_buffer;
    uint16_t tx_buffer_size;

    // Internal state
    volatile bool       tx_cplt_flag;
    volatile uint16_t   rx_data_len;
    uint16_t            last_rx_dma_pos;

} USART_DMA_Handler_t;

extern USART_DMA_Handler_t h_usart1, h_usart6;

void usart_dma_start(USART_DMA_Handler_t* huart);

ErrorStatus usart_dma_transmit(USART_DMA_Handler_t* huart, const uint8_t* data, uint16_t len);
void usart_dma_tx_isr_handler(USART_DMA_Handler_t* huart);
void usart_idle_line_isr_handler(USART_DMA_Handler_t* huart);
void usart_dma_init(void);

#endif /* INC_USART_DMA_HANDLER_H_ */
