/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
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
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/

#include "stm32g0xx_ll_adc.h"
#include "stm32g0xx_ll_dma.h"
#include "stm32g0xx_ll_lptim.h"
#include "stm32g0xx_ll_lpuart.h"
#include "stm32g0xx_ll_rcc.h"
#include "stm32g0xx_ll_bus.h"
#include "stm32g0xx_ll_system.h"
#include "stm32g0xx_ll_exti.h"
#include "stm32g0xx_ll_cortex.h"
#include "stm32g0xx_ll_utils.h"
#include "stm32g0xx_ll_pwr.h"
#include "stm32g0xx_ll_tim.h"
#include "stm32g0xx_ll_usart.h"
#include "stm32g0xx_ll_gpio.h"

#if defined(USE_FULL_ASSERT)
#include "stm32_assert.h"
#endif /* USE_FULL_ASSERT */

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define DATA_OUT_Pin LL_GPIO_PIN_2
#define DATA_OUT_GPIO_Port GPIOA
#define DATA_IN_Pin LL_GPIO_PIN_3
#define DATA_IN_GPIO_Port GPIOA
#define SOL1_OUT_Pin LL_GPIO_PIN_4
#define SOL1_OUT_GPIO_Port GPIOA
#define SOL2_OUT_Pin LL_GPIO_PIN_5
#define SOL2_OUT_GPIO_Port GPIOA
#define TEMP_SEN_IN_Pin LL_GPIO_PIN_6
#define TEMP_SEN_IN_GPIO_Port GPIOA
#define PRES_SEN_IN_Pin LL_GPIO_PIN_7
#define PRES_SEN_IN_GPIO_Port GPIOA
#define SEN_IN_OPT_Pin LL_GPIO_PIN_8
#define SEN_IN_OPT_GPIO_Port GPIOA
#define SEN_IN_Pin LL_GPIO_PIN_12
#define SEN_IN_GPIO_Port GPIOA
#define SEN_IN_EXTI_IRQn EXTI4_15_IRQn
#define DBG_OUT_Pin LL_GPIO_PIN_6
#define DBG_OUT_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
