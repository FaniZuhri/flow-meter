/*
 * uph_scp.c
 *
 *  Created on: Apr 12, 2025
 *      Author: Hardware2
 */

#include <string.h>
#include <stdio.h>
#include <stdbool.h>

#include "uph_scp.h"
#include "uph_flow_sensor.h"
#include "uph_user_data.h"
#include "tim_handler.h"
#include "adc_handler.h"

#define USE_SPRINTF		1U

int scp_test_getter(uint8_t *rx_cmd_buf);
int scp_test_setter(uint8_t *rx_cmd_buf);
int scp_sensor_set_sensing(uint8_t *rx_cmd_buf);
int scp_sensor_get_sensing_flag(uint8_t *rx_cmd_buf);
int scp_user_set_solenoid(uint8_t *rx_cmd_buf);
int scp_user_get_solenoid(uint8_t *rx_cmd_buf);

const scp_command_table_t scp_cmd_tbl[SCP_COMMAND_TABLE_SIZE] = {
    //Command code      get functions       			set functions
	{'P',               NULL,							NULL},
	{'Z',				scp_test_getter,				scp_test_setter},
	{'S',				scp_sensor_get_sensing_flag,	scp_sensor_set_sensing},
	{'D',				scp_user_get_all_data,			NULL},
	{'B',				scp_user_set_solenoid,			scp_user_get_solenoid},
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

int scp_user_set_solenoid(uint8_t *rx_cmd_buf) {
	uint8_t sol1_state = (*rx_cmd_buf) - 48;
	uint8_t sol2_state = (*(rx_cmd_buf + 1)) - 48;

	UserData_SetSolenoidState(sol1_state, sol2_state);
	return 0;
}

int scp_user_get_solenoid(uint8_t *rx_cmd_buf) {
	uint8_t sol_state[2];
	sol_state[SOLENOID_1] = UserData_GetSolenoidState(SOLENOID_1);
	sol_state[SOLENOID_2] = UserData_GetSolenoidState(SOLENOID_1);

	send_response_fn(*rx_cmd_buf, SCP_ACK_RESPONSE, sol_state, 2);
	return SCP_DATA_RESPPONSE;
}

int scp_sensor_get_sensing_flag(uint8_t *rx_cmd_buf) {
	uint8_t is_started = h_flow_sensor.is_running;
	send_response_fn(*rx_cmd_buf, SCP_ACK_RESPONSE, &is_started, 1);
	return SCP_DATA_RESPPONSE;
}

int scp_sensor_set_sensing(uint8_t *rx_cmd_buf) {
	bool val = (*rx_cmd_buf) - 48;

	FlowSensor_Set_Started(&h_flow_sensor, val);

	if (val) {
		FlowSensor_Init(&h_flow_sensor, 500);
		TIM_Handler_Start(&h_tim11, h_flow_sensor.calculation_interval_ms);
		TIM_Handler_Start(&h_tim10, 200);
	}
	else {
		TIM_Handler_Stop(&h_tim11);
		TIM_Handler_Stop(&h_tim10);
	}

	return 0;
}

int scp_user_get_all_data(uint8_t *rx_cmd_buf) {
	UserData_Calculate_Pres_Bar(adc_dma_buffer[0]);
	UserData_Calculate_Temp_Celsius(adc_dma_buffer[1]);
	sprintf(
			(char *) h_usart1.tx_buffer,
			"{D:%ld,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%d}\r\n",
			user_data.flow_sensor->pulse_count,
			user_data.flow_sensor->frequency_hz,
			user_data.flow_sensor->flow_rate_lpm,
			user_data.flow_sensor->total_volume_liters,
			user_data.pres_val_bar,
			user_data.temp_val_celcius,
			user_data.solenoid_states[0],
			user_data.solenoid_states[1]
	);
	usart_dma_transmit(&h_usart1, h_usart1.tx_buffer, strlen((char *) h_usart1.tx_buffer));
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
	switch(id) {
	case SCP_ACK_RESPONSE:
		uint8_t ack_resp[4U] = "OK!\0";
		if (data_size == 0) {
			sprintf(
				(char *) h_usart1.tx_buffer, "{%c:%s}\r\n", command, ack_resp
			);
		}
		else {
			sprintf(
				(char *) h_usart1.tx_buffer, "{%c:%d}\r\n", command, (int) *data
			);
		}
		break;
	case SCP_NAK_RESPONSE:
		uint8_t nak_resp[4U] = "NAK\0";
		sprintf(
			(char *) h_usart1.tx_buffer, "{%c:%s}\r\n", command, nak_resp
		);
		break;
	case SCP_ERR_RESPONSE:
		uint8_t err_resp[4U] = "ERR\0";
		sprintf(
			(char *) h_usart1.tx_buffer, "{%c:%s}\r\n", command, err_resp
		);
		break;
	default:
		break;
	}
	usart_dma_transmit(&h_usart1, h_usart1.tx_buffer, strlen((char *) h_usart1.tx_buffer));
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

