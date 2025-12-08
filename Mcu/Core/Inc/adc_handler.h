/*
 * adc_handler.h
 *
 *  Created on: Jun 23, 2025
 *      Author: Hardware2
 */

#ifndef INC_ADC_HANDLER_H_
#define INC_ADC_HANDLER_H_

#include "main.h"
#include <stdbool.h>
#include <stdint.h>

#define ADC_MAX_CHANNELS 	2
#define ADC_DMA_BUFFER_SIZE 2

typedef struct {
    ADC_TypeDef* instance;
    DMA_TypeDef* dma_instance;
    uint32_t       dma_stream;
    TIM_TypeDef* trigger_timer;

    uint16_t* dma_buffer;
    uint32_t       dma_buffer_size_samples;

    volatile uint16_t latest_values[ADC_MAX_CHANNELS];

    void (*scan_cplt_callback)(volatile uint16_t* data, uint8_t num_ch);
    void (*overrun_callback)(void);

} ADC_Handler_t;

extern ADC_Handler_t h_adc1;
extern uint16_t adc_dma_buffer[ADC_DMA_BUFFER_SIZE];


void ADC_Handler_Init(ADC_Handler_t* hadc, ADC_TypeDef* instance, DMA_TypeDef* dma_instance, uint32_t dma_stream);
void ADC_Handler_Register_Callbacks(ADC_Handler_t* hadc, void (*scan_cb)(volatile uint16_t*, uint8_t), void (*ovr_cb)(void));
bool ADC_Handler_Start(ADC_Handler_t* hadc, TIM_TypeDef* tim_trigger, uint16_t* buffer, uint32_t buffer_size);
uint16_t ADC_Handler_GetLatestValue(ADC_Handler_t* hadc, uint8_t channel_index);
void ADC_Handler_ADC_IRQHandler(ADC_Handler_t* hadc);
void ADC_Handler_DMA_IRQHandler(ADC_Handler_t* hadc);

void On_ADC_Scan_Complete(volatile uint16_t* data, uint8_t num_ch);
void On_ADC_Overrun(void);

#endif /* INC_ADC_HANDLER_H_ */
