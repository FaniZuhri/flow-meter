/*
 * uph_scp.c
 *
 *  Created on: Apr 12, 2025
 *      Author: Hardware2
 */

#include <string.h>
#include <stdio.h>

#include "uph_scp.h"
#include "uph_flow_sensor.h"
#include "uph_user_data.h"

#define USE_SPRINTF		1U

int scp_test_getter(uint8_t *rx_cmd_buf);
int scp_test_setter(uint8_t *rx_cmd_buf);
int scp_sensor_set_sensing(uint8_t *rx_cmd_buf);
int scp_sensor_get_sensing_flag(uint8_t *rx_cmd_buf);

const scp_command_table_t scp_cmd_tbl[SCP_COMMAND_TABLE_SIZE] = {
    //Command code      get functions       			set functions
	{'P',               NULL,							NULL},
	{'Z',				scp_test_getter,				scp_test_setter},
	{'S',				scp_sensor_get_sensing_flag,	scp_sensor_set_sensing},
	{'D',				scp_user_get_all_data,			NULL},
};

scp_handle_t scp_handle;
uint8_t scp_exec_command_status, scp_is_busy;

static uint8_t *scp_buffer_read(scp_handle_t handle);
static scp_action_command_t scp_check_action_command(uint8_t *from_data_received);
static void send_response_fn(uint8_t command, scp_exec_return_code_t id, uint8_t *data, uint8_t data_size);

#if defined (USE_SPRINTF) && (!USE_SPRINTF)
static uint8_t fill_data_to_send_buff(uint8_t *data_sensor, uint8_t *data_buffer, uint8_t parser, int i);
#endif

#if defined(USE_ITOA) && (USE_ITOA)
static void itoa_swap(uint8_t *num1, uint8_t *num2);
static uint8_t *itoa_reverse(uint8_t *buffer, int i, int j);
#endif

int scp_test_getter(uint8_t *rx_cmd_buf) {
	return 0;
}

int scp_test_setter(uint8_t *rx_cmd_buf) {
	return 0;
}

int scp_sensor_get_sensing_flag(uint8_t *rx_cmd_buf) {
	uint8_t is_started = flow_get_test_started();
	send_response_fn(*rx_cmd_buf, SCP_ACK_RESPONSE, &is_started, 1);
	return SCP_DATA_RESPPONSE;
}

int scp_sensor_set_sensing(uint8_t *rx_cmd_buf) {
	uint8_t val = (*rx_cmd_buf) - 48;

	if (val) {
		flow_sensor_reset();
		flow_sensor_stop_sensing();
		user_data_reset();

		flow_sensor_start_sensing();
		user_start_sensors_timer();
	}
	else {
		flow_sensor_stop_sensing();
		user_stop_sensors_timer();
	}

	return 0;
}

int scp_user_get_all_data(uint8_t *rx_cmd_buf) {
//	for periodic send, we need to prepare this dummy var
	uint8_t dummy_cmd_id = 'D';
	memset(lpuart_tx_buf, 0x0, LPUART_TX_DATA_SIZE);
	sprintf(
			(char *) lpuart_tx_buf,
			"{%c:%d,%lu,%lu,%.3f,%.3f}\r\n",
			dummy_cmd_id, user_data.solenoid_state, user_data.temp_sensor, user_data.pressure_sensor, user_data.speed, user_data.volume
	);
	lpuart_dma_transmit(lpuart_tx_buf, strlen((char *) lpuart_tx_buf));
	return SCP_DATA_RESPPONSE;
}

#if defined(USE_ITOA) && (USE_ITOA)
static void itoa_swap(uint8_t *num1, uint8_t *num2) {
	uint8_t new_num = *num1;

	*num1 = *num2;
	*num2 = new_num;
}

static uint8_t *itoa_reverse(uint8_t *buffer, int i, int j) {
    while (i < j) {
        itoa_swap(&buffer[i++], &buffer[j--]);
    }

    return buffer;
}

uint8_t *itoa(uint16_t value, uint8_t *buffer, uint8_t base) {
    // consider the absolute value of the number
    int num = value;
    int num_len = 0U;

    while (num) {
        int r = num % base;

        if (r >= 10U) {
            buffer[num_len++] = 65U + (r - 10U);
        }
        else {
            buffer[num_len++] = 48U + r;
        }

        num = num / base;
    }

    // if the number is 0
    if (num_len == 0) {
        buffer[num_len++] = '0';
    }

    buffer[num_len] = '\0'; // null terminate string

    // reverse the string and return it
    return itoa_reverse(buffer, 0, num_len - 1);
}
#endif

#if defined (USE_SPRINTF) && (!USE_SPRINTF)
static uint8_t fill_data_to_send_buff(uint8_t *data_sensor, uint8_t *data_buffer, uint8_t parser, int i)
{
        // int i = 0;
    while(*data_sensor)
    {
        if (*(data_sensor) == '\0') break;
        data_buffer[i] = *(data_sensor);
        i++;
        data_sensor++;
    }

    if (!parser) return i;

    data_buffer[i] = parser;

    return i + 1;
}
#endif

static uint8_t *scp_buffer_read(scp_handle_t handle)
{
    uint8_t *data_rcvd;
    /* declare start and end pointer that have same address as s pointer */
    handle.buf_ptr = handle.scp_buf;
    handle.start_address = handle.buf_ptr;
    handle.stop_address = handle.buf_ptr;
    data_rcvd = handle.buf_ptr;
    /* check if *s is true */
    while(*handle.buf_ptr)
    {
    	if(*handle.buf_ptr != '{' && *handle.buf_ptr != '}') handle.buf_ptr++;
    	/* check if there is bracket { inside of buffer pointer */
        if(*handle.buf_ptr == '{') handle.start_address = handle.buf_ptr;
        /* check if there is bracket } inside of buffer pointer */
        if(*handle.buf_ptr == '}') handle.stop_address = handle.buf_ptr;
        /* make sure that start address is before end address */
        if(handle.start_address < handle.stop_address && (*(handle.start_address)))
        {
            (*(handle.stop_address)) = 0x0;
            /* address of pointer data_rcv is address of pointer start, +1 */
            data_rcvd = handle.start_address+1;
            handle.start_address = handle.buf_ptr = handle.stop_address;
        };
        handle.buf_ptr++;
    }
    return data_rcvd;
}

static scp_action_command_t scp_check_action_command(uint8_t *from_data_received)
{
	if ( (*(from_data_received+1)) != '?' && (*(from_data_received+1)) != ':' ) return SCP_ACTION_COMMAND_INVALID;

	if ( (*(from_data_received+1)) == '?' && (*(from_data_received+2)) ) return SCP_ACTION_COMMAND_INVALID;

	if ( (*(from_data_received+1)) == '?' )
    {
        return SCP_ACTION_COMMAND_GET;
    }

	else if ( (*(from_data_received+1)) == ':' )
    {
        return SCP_ACTION_COMMAND_SET;
    }

	return SCP_ACTION_COMMAND_INVALID;
}

void send_response_fn(uint8_t command, scp_exec_return_code_t id, uint8_t *data, uint8_t data_size) {
	memset(lpuart_tx_buf, 0x0, LPUART_TX_DATA_SIZE);

	switch(id) {
	case SCP_ACK_RESPONSE:
		uint8_t ack_resp[4U] = "OK!\0";
		if (data_size == 0) {
			sprintf(
				(char *) lpuart_tx_buf, "{%c:%s}\r\n", command, ack_resp
			);
		}
		else {
			sprintf(
				(char *) lpuart_tx_buf, "{%c:%d}\r\n", command, (int) *data
			);
		}
		break;
	case SCP_NAK_RESPONSE:
		uint8_t nak_resp[4U] = "NAK\0";
		sprintf(
			(char *) lpuart_tx_buf, "{%c:%s}\r\n", command, nak_resp
		);
		break;
	case SCP_ERR_RESPONSE:
		uint8_t err_resp[4U] = "ERR\0";
		sprintf(
			(char *) lpuart_tx_buf, "{%c:%s}\r\n", command, err_resp
		);
		break;
	default:
		break;
	}
	lpuart_dma_transmit(lpuart_tx_buf, strlen((char *) lpuart_tx_buf));
}

static ErrorStatus is_command_invalid(uint8_t *command) {
	for (int i = 0; i < sizeof(scp_cmd_tbl)/sizeof(struct scp_command_table_s); i++) {
		if (*command == scp_cmd_tbl[i].command_code) return SUCCESS;
	}
	return ERROR;
}

int scp_exec_command(uint8_t *from_data_filtered, int from_data_action_command) {
    uint8_t exec_fn_status;

    // variable fpr indexing scp_cmd_tbl
    uint8_t function_table_index;

    // size of scp_cmd_tbl
    uint16_t function_table_len = sizeof(scp_cmd_tbl)/sizeof(struct scp_command_table_s);

    // loop inside the jump table to check the command
    for (function_table_index = 0; function_table_index < function_table_len; function_table_index++) {
        if ((*(from_data_filtered)) == scp_cmd_tbl[function_table_index].command_code) break;
    }

    if (function_table_index >= function_table_len) return SCP_ERR_RESPONSE;

    if (from_data_action_command == SCP_ACTION_COMMAND_SET) {
    	// return error if setter function is not found
    	if (!scp_cmd_tbl[function_table_index].setter_fn) return SCP_ERR_RESPONSE;
		// if found
		exec_fn_status = scp_cmd_tbl[function_table_index].setter_fn(from_data_filtered+2);

        return exec_fn_status;
    }

    else if (from_data_action_command == SCP_ACTION_COMMAND_GET) {
    	// verify the getter function is found
    	if (!scp_cmd_tbl[function_table_index].getter_fn) return SCP_ERR_RESPONSE;
		// if found
    	exec_fn_status = scp_cmd_tbl[function_table_index].getter_fn(from_data_filtered);

		return exec_fn_status;
    }

    return SCP_ERR_RESPONSE;
}

void scp_cmd_process(void) {
	uint8_t *data_received;
	int data_action_command;

//	Get Data inside the bracket
	data_received = scp_buffer_read(scp_handle);

//	Get command type
	data_action_command = scp_check_action_command(data_received);

	if (data_action_command == SCP_ACTION_COMMAND_INVALID) {
		if(is_command_invalid(data_received)) send_response_fn('Z', SCP_ERR_RESPONSE, NULL, 0);
		else send_response_fn(*(data_received), SCP_ERR_RESPONSE, NULL, 0);
	}
	else {
		scp_exec_command_status = scp_exec_command(data_received, data_action_command);

		if (scp_exec_command_status == SCP_ERR_RESPONSE) {
			send_response_fn(*(data_received), SCP_ERR_RESPONSE, NULL, 0);
		}

		else if (scp_exec_command_status == SCP_ACK_RESPONSE) {
			send_response_fn(*(data_received), SCP_ACK_RESPONSE, NULL, 0);
			scp_handle.is_busy = 1;
		}

		else if(scp_exec_command_status == SCP_DATA_RESPPONSE) {
			scp_handle.is_busy = 1;
		}

		else {
			scp_handle.is_busy = 1;
			send_response_fn(*(data_received), SCP_NAK_RESPONSE, NULL, 0);
		}
	}
}

