/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    usart.h
  * @brief   This file contains all the function prototypes for
  *          the usart.c file
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __USART_H__
#define __USART_H__

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* USER CODE BEGIN Includes */
#include <string.h>
#define LPUART_RX_DATA_SIZE		256U
#define LPUART_TX_DATA_SIZE		128U
#define UART_DBG_TX_DATA_SIZE	128U

typedef enum {
	UART_SCP_DMA_TX_UNCOMPLETE,
	UART_SCP_DMA_TX_COMPLETE,
} uart_scp_dma_status_t;
/* USER CODE END Includes */

/* USER CODE BEGIN Private defines */
extern uint8_t uart_tx_buf[UART_DBG_TX_DATA_SIZE], uart_start_byte_idx;
extern uint8_t lpuart_rx_buf[LPUART_RX_DATA_SIZE], lpuart_tx_buf[LPUART_TX_DATA_SIZE];
extern volatile uart_scp_dma_status_t lpuart_scp_tx_status, uart_tx_status;
/* USER CODE END Private defines */

void MX_LPUART1_UART_Init(void);
void MX_USART1_UART_Init(void);

/* USER CODE BEGIN Prototypes */
__STATIC_INLINE uint8_t lpuart_get_rx_buf(uint8_t idx) {
	return lpuart_rx_buf[idx];
}

__STATIC_INLINE void lpuart_set_rx_buf(uint8_t idx, uint8_t data) {
	lpuart_rx_buf[idx] = data;
}

void uart_debug_print(uint8_t *buf, uint32_t size);
void lpuart_dma_transmit(uint8_t *tx_buf, uint8_t tx_size);
void lpuart_dma_receive(void);

/* USER CODE END Prototypes */

#ifdef __cplusplus
}
#endif

#endif /* __USART_H__ */

