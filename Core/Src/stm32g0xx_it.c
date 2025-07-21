/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    stm32g0xx_it.c
  * @brief   Interrupt Service Routines.
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

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "stm32g0xx_it.h"
/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "usart.h"

#include "uph_flow_sensor.h"
#include "uph_fsm.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN TD */

/* USER CODE END TD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/* External variables --------------------------------------------------------*/

/* USER CODE BEGIN EV */

/* USER CODE END EV */

/******************************************************************************/
/*           Cortex-M0+ Processor Interruption and Exception Handlers          */
/******************************************************************************/
/**
  * @brief This function handles Non maskable interrupt.
  */
void NMI_Handler(void)
{
  /* USER CODE BEGIN NonMaskableInt_IRQn 0 */

  /* USER CODE END NonMaskableInt_IRQn 0 */
  /* USER CODE BEGIN NonMaskableInt_IRQn 1 */
   while (1)
  {
  }
  /* USER CODE END NonMaskableInt_IRQn 1 */
}

/**
  * @brief This function handles Hard fault interrupt.
  */
void HardFault_Handler(void)
{
  /* USER CODE BEGIN HardFault_IRQn 0 */

  /* USER CODE END HardFault_IRQn 0 */
  while (1)
  {
    /* USER CODE BEGIN W1_HardFault_IRQn 0 */
    /* USER CODE END W1_HardFault_IRQn 0 */
  }
}

/**
  * @brief This function handles System service call via SWI instruction.
  */
void SVC_Handler(void)
{
  /* USER CODE BEGIN SVC_IRQn 0 */

  /* USER CODE END SVC_IRQn 0 */
  /* USER CODE BEGIN SVC_IRQn 1 */

  /* USER CODE END SVC_IRQn 1 */
}

/**
  * @brief This function handles Pendable request for system service.
  */
void PendSV_Handler(void)
{
  /* USER CODE BEGIN PendSV_IRQn 0 */

  /* USER CODE END PendSV_IRQn 0 */
  /* USER CODE BEGIN PendSV_IRQn 1 */

  /* USER CODE END PendSV_IRQn 1 */
}

/**
  * @brief This function handles System tick timer.
  */
void SysTick_Handler(void)
{
  /* USER CODE BEGIN SysTick_IRQn 0 */

  /* USER CODE END SysTick_IRQn 0 */

  /* USER CODE BEGIN SysTick_IRQn 1 */

  /* USER CODE END SysTick_IRQn 1 */
}

/******************************************************************************/
/* STM32G0xx Peripheral Interrupt Handlers                                    */
/* Add here the Interrupt Handlers for the used peripherals.                  */
/* For the available peripheral interrupt handler names,                      */
/* please refer to the startup file (startup_stm32g0xx.s).                    */
/******************************************************************************/

/**
  * @brief This function handles EXTI line 4 to 15 interrupts.
  */
void EXTI4_15_IRQHandler(void)
{
  /* USER CODE BEGIN EXTI4_15_IRQn 0 */

  /* USER CODE END EXTI4_15_IRQn 0 */
  if (LL_EXTI_IsActiveRisingFlag_0_31(LL_EXTI_LINE_12) != RESET)
  {
    LL_EXTI_ClearRisingFlag_0_31(LL_EXTI_LINE_12);
    /* USER CODE BEGIN LL_EXTI_LINE_12_RISING */
    flow_inc_pulse_count();
    /* USER CODE END LL_EXTI_LINE_12_RISING */
  }
  /* USER CODE BEGIN EXTI4_15_IRQn 1 */

  /* USER CODE END EXTI4_15_IRQn 1 */
}

/**
  * @brief This function handles DMA1 channel 1 interrupt.
  */
void DMA1_Channel1_IRQHandler(void)
{
  /* USER CODE BEGIN DMA1_Channel1_IRQn 0 */
	if (LL_DMA_IsActiveFlag_TE1(DMA1)) {
		LL_DMA_ClearFlag_TE1(DMA1);
	}

	if(LL_DMA_IsActiveFlag_TC1(DMA1)) {
		LL_DMA_ClearFlag_TC1(DMA1);
		lpuart_scp_tx_status = UART_SCP_DMA_TX_COMPLETE;
	}
  /* USER CODE END DMA1_Channel1_IRQn 0 */
  /* USER CODE BEGIN DMA1_Channel1_IRQn 1 */

  /* USER CODE END DMA1_Channel1_IRQn 1 */
}

/**
  * @brief This function handles DMA1 channel 2 and channel 3 interrupts.
  */
void DMA1_Channel2_3_IRQHandler(void)
{
  /* USER CODE BEGIN DMA1_Channel2_3_IRQn 0 */
	if (LL_DMA_IsActiveFlag_TE2(DMA1)) {
		LL_DMA_ClearFlag_TE2(DMA1);
	}

	if (LL_DMA_IsActiveFlag_TE3(DMA1)) {
		LL_DMA_ClearFlag_TE3(DMA1);
	}

	if (LL_DMA_IsActiveFlag_TC3(DMA1)) {
		LL_DMA_ClearFlag_TC3(DMA1);
		fsm_set_state(FSM_STATE_SENS_PRES_TEMP_DONE);
	}
  /* USER CODE END DMA1_Channel2_3_IRQn 0 */
  /* USER CODE BEGIN DMA1_Channel2_3_IRQn 1 */

  /* USER CODE END DMA1_Channel2_3_IRQn 1 */
}

/**
  * @brief This function handles DMA1 channel 4, channel 5 and DMAMUX1 interrupts.
  */
void DMA1_Ch4_5_DMAMUX1_OVR_IRQHandler(void)
{
  /* USER CODE BEGIN DMA1_Ch4_5_DMAMUX1_OVR_IRQn 0 */
	if (LL_DMA_IsActiveFlag_TE4(DMA1)) {
		LL_DMA_ClearFlag_TE4(DMA1);
	}

	if(LL_DMA_IsActiveFlag_TC4(DMA1)) {
		LL_DMA_ClearFlag_TC4(DMA1);
		uart_tx_status = UART_SCP_DMA_TX_COMPLETE;
	}
  /* USER CODE END DMA1_Ch4_5_DMAMUX1_OVR_IRQn 0 */
  /* USER CODE BEGIN DMA1_Ch4_5_DMAMUX1_OVR_IRQn 1 */

  /* USER CODE END DMA1_Ch4_5_DMAMUX1_OVR_IRQn 1 */
}

/**
  * @brief This function handles ADC1 interrupt.
  */
void ADC1_IRQHandler(void)
{
  /* USER CODE BEGIN ADC1_IRQn 0 */
//	TODO: ADC temperature and pressure sensing done action
  /* USER CODE END ADC1_IRQn 0 */
  /* USER CODE BEGIN ADC1_IRQn 1 */

  /* USER CODE END ADC1_IRQn 1 */
}

/**
  * @brief This function handles LPTIM1 interrupt through EXTI line 29.
  */
void LPTIM1_IRQHandler(void)
{
  /* USER CODE BEGIN LPTIM1_IRQn 0 */
	if (LL_LPTIM_IsActiveFlag_CMPM(LPTIM1)) {
		LL_LPTIM_ClearFlag_CMPM(LPTIM1);
		fsm_set_state(FSM_STATE_PERIODIC_SENS_REACHED);
	}
  /* USER CODE END LPTIM1_IRQn 0 */
  /* USER CODE BEGIN LPTIM1_IRQn 1 */

  /* USER CODE END LPTIM1_IRQn 1 */
}

/**
  * @brief This function handles LPTIM2 interrupt through EXTI line 30.
  */
void LPTIM2_IRQHandler(void)
{
  /* USER CODE BEGIN LPTIM2_IRQn 0 */
	if (LL_LPTIM_IsActiveFlag_CMPM(LPTIM2)) {
		LL_LPTIM_ClearFlag_CMPM(LPTIM2);
		fsm_set_state(FSM_STATE_PERIODIC_PRES_TEMP_REACHED);
	}
  /* USER CODE END LPTIM2_IRQn 0 */
  /* USER CODE BEGIN LPTIM2_IRQn 1 */

  /* USER CODE END LPTIM2_IRQn 1 */
}

/**
  * @brief This function handles LPUART1 interrupt / LPUART1 wake-up interrupt through EXTI line 28.
  */
void LPUART1_IRQHandler(void)
{
  /* USER CODE BEGIN LPUART1_IRQn 0 */
	if (LL_LPUART_IsActiveFlag_FE(LPUART1)) {
		LL_LPUART_ClearFlag_FE(LPUART1);
	}

	if (LL_LPUART_IsActiveFlag_ORE(LPUART1)) {
		LL_LPUART_ClearFlag_ORE(LPUART1);
	}

	if(LL_LPUART_IsActiveFlag_IDLE(LPUART1)) {
		LL_LPUART_ClearFlag_IDLE(LPUART1);
		if(LL_LPUART_ReceiveData8(LPUART1)) {
//			NOTE: some bytes received in Rx Data Register
			fsm_set_state(FSM_STATE_LPUART_RCV_DONE);
		}
	}
  /* USER CODE END LPUART1_IRQn 0 */
  /* USER CODE BEGIN LPUART1_IRQn 1 */

  /* USER CODE END LPUART1_IRQn 1 */
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
