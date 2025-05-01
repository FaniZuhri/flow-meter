/*
 * uph_scp.h
 *
 *  Created on: Apr 12, 2025
 *      Author: Hardware2
 */

#ifndef INC_UPH_SCP_H_
#define INC_UPH_SCP_H_

#include "stm32g0xx_ll_usart.h"
#include "usart.h"

#define SCP_COMMAND_TABLE_SIZE	2U

typedef int (*volatile scp_func_ptr) (uint8_t *);

typedef struct scp_handle_s {
	uint8_t scp_buf[LPUART_RX_DATA_SIZE];
	uint8_t *start_address;
	uint8_t *stop_address;
	uint8_t *buf_ptr;
	uint8_t rcv_done;
	uint8_t is_busy;
} scp_handle_t;

typedef enum scp_action_command_e {
	SCP_ACTION_COMMAND_GET,
	SCP_ACTION_COMMAND_SET,
	SCP_ACTION_COMMAND_INVALID,
} scp_action_command_t;

typedef enum scp_exec_return_code_e {
	SCP_ACK_RESPONSE,
	SCP_NAK_RESPONSE,
	SCP_ERR_RESPONSE,
	SCP_DATA_RESPPONSE,
	SCP_SOLENOID_RESPONSE,
	SCP_TEMP_SENS_RESPONSE,
	SCP_PRES_SENS_RESPONSE,
} scp_exec_return_code_t;

typedef struct scp_command_table_s {
	unsigned char command_code;
	scp_func_ptr getter_fn;
	scp_func_ptr setter_fn;
} scp_command_table_t;

void scp_cmd_process(void);
int scp_exec_command(uint8_t *from_data_filtered, int from_data_action_command);

extern scp_handle_t scp_handle;

__STATIC_INLINE uint8_t *scp_handle_get_start_address(void) {
	return scp_handle.start_address;
}

__STATIC_INLINE void scp_handle_set_start_address(uint8_t *addr) {
	scp_handle.start_address = addr;
}

__STATIC_INLINE uint8_t *scp_handle_get_stop_address(void) {
	return scp_handle.stop_address;
}

__STATIC_INLINE void scp_handle_set_stop_address(uint8_t *addr) {
	scp_handle.stop_address = addr;
}

__STATIC_INLINE uint8_t scp_handle_is_busy(void) {
	return scp_handle.is_busy;
}

__STATIC_INLINE void scp_handle_set_busy(uint8_t val) {
	scp_handle.is_busy = val;
}

__STATIC_INLINE uint8_t scp_handle_is_rcv_done(void) {
	return scp_handle.rcv_done;
}

__STATIC_INLINE void scp_handle_set_rcv_done(uint8_t val) {
	scp_handle.rcv_done = val;
}

void ack_response_fn(uint8_t command);
void err_response_fn(uint8_t command);
void nak_response_fn(uint8_t command);
uint8_t *itoa(uint16_t value, uint8_t *buffer, uint8_t base);

#endif /* INC_UPH_SCP_H_ */
