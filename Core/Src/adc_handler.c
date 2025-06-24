/*
 * adc_handler.c
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */
#include <string.h>
#include <stdio.h>

#include "adc_handler.h"

ADC_Handler_t h_adc1;
uint16_t adc_dma_buffer[ADC_DMA_BUFFER_SIZE];

void ADC_Handler_Init(ADC_Handler_t* hadc, ADC_TypeDef* instance, DMA_TypeDef* dma_instance, uint32_t dma_stream) {
    if (!hadc) return;
    hadc->instance = instance;
    hadc->dma_instance = dma_instance;
    hadc->dma_stream = dma_stream;
    hadc->scan_cplt_callback = NULL;
    hadc->overrun_callback = NULL;

    LL_ADC_Enable(hadc->instance);
    LL_mDelay(2);

    LL_ADC_REG_SetFlagEndOfConversion(hadc->instance, LL_ADC_REG_FLAG_EOC_SEQUENCE_CONV);

    LL_ADC_EnableIT_EOCS(hadc->instance);
    LL_ADC_EnableIT_OVR(hadc->instance);
}

void ADC_Handler_Register_Callbacks(ADC_Handler_t* hadc, void (*scan_cb)(volatile uint16_t*, uint8_t), void (*ovr_cb)(void)) {
    if(hadc) {
        hadc->scan_cplt_callback = scan_cb;
        hadc->overrun_callback = ovr_cb;
    }
}

bool ADC_Handler_Start(ADC_Handler_t* hadc, TIM_TypeDef* tim_trigger, uint16_t* buffer, uint32_t buffer_size) {
    if (!hadc || !tim_trigger || !buffer || buffer_size == 0) return false;

    hadc->trigger_timer = tim_trigger;
    hadc->dma_buffer = buffer;
    hadc->dma_buffer_size_samples = buffer_size;

    LL_DMA_ConfigAddresses(hadc->dma_instance, hadc->dma_stream,
                           LL_ADC_DMA_GetRegAddr(hadc->instance, LL_ADC_DMA_REG_REGULAR_DATA),
                           (uint32_t)buffer, LL_DMA_GetDataTransferDirection(hadc->dma_instance, hadc->dma_stream));
    LL_DMA_SetDataLength(hadc->dma_instance, hadc->dma_stream, buffer_size);
    LL_DMA_EnableIT_TE(hadc->dma_instance, hadc->dma_stream);
    LL_DMA_EnableStream(hadc->dma_instance, hadc->dma_stream);

    LL_ADC_REG_SetDMATransfer(hadc->instance, LL_ADC_REG_DMA_TRANSFER_UNLIMITED);

    LL_TIM_EnableCounter(hadc->trigger_timer);

    return true;
}

void ADC_Handler_Stop(ADC_Handler_t* hadc) {
	if (hadc->trigger_timer) {
		LL_TIM_DisableCounter(hadc->trigger_timer);
	}
	// Untuk mematikan, kita set ke NONE
	LL_ADC_REG_SetDMATransfer(hadc->instance, LL_ADC_REG_DMA_TRANSFER_NONE);
	LL_DMA_DisableStream(hadc->dma_instance, hadc->dma_stream);
	LL_DMA_DisableIT_TE(hadc->dma_instance, hadc->dma_stream);
	ADC_Handler_Start(&h_adc1, TIM2, adc_dma_buffer, ADC_DMA_BUFFER_SIZE);
}

uint16_t ADC_Handler_GetLatestValue(ADC_Handler_t* hadc, uint8_t channel_index) {
    if (channel_index >= ADC_MAX_CHANNELS) return 0;
    return hadc->latest_values[channel_index];
}

void ADC_Handler_ADC_IRQHandler(ADC_Handler_t* hadc) {
    if (LL_ADC_IsActiveFlag_EOCS(hadc->instance)) {
        LL_ADC_ClearFlag_EOCS(hadc->instance);

        uint32_t dma_current_pos = hadc->dma_buffer_size_samples - LL_DMA_GetDataLength(hadc->dma_instance, hadc->dma_stream);

        for (uint8_t i = 0; i < ADC_MAX_CHANNELS; i++) {
            int32_t idx = dma_current_pos - (ADC_MAX_CHANNELS - i);
            if (idx < 0) {
                idx += hadc->dma_buffer_size_samples;
            }
            hadc->latest_values[i] = hadc->dma_buffer[idx];
        }

        if (hadc->scan_cplt_callback) {
            hadc->scan_cplt_callback(hadc->latest_values, ADC_MAX_CHANNELS);
        }
    }

    if (LL_ADC_IsActiveFlag_OVR(hadc->instance)) {
        LL_ADC_ClearFlag_OVR(hadc->instance);
        if (hadc->overrun_callback) {
            hadc->overrun_callback();
        }
    }
}

void ADC_Handler_DMA_IRQHandler(ADC_Handler_t* hadc) {
    if (LL_DMA_IsActiveFlag_TE0(hadc->dma_instance)) {
        LL_DMA_ClearFlag_TE0(hadc->dma_instance);
    }
}

void On_ADC_Scan_Complete(volatile uint16_t* data, uint8_t num_ch) {
    char msg[64];
    sprintf(msg, "ADC -> IN1: %u, IN2: %u\r\n", data[0], data[1]);
//    usart_dma_transmit(&h_usart1, (uint8_t*)msg, strlen(msg));
}

void On_ADC_Overrun(void) {
    ADC_Handler_Stop(&h_adc1);
}
