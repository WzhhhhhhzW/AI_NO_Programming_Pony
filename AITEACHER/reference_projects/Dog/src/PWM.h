/*
 * PWM.h
 *
 *  Created on: 2026年2月5日
 *      Author: lenovo
 */

#ifndef PWM_PWM_H_
#define PWM_PWM_H_


#include "hal_data.h"
//模块初始化
void Front_Init(void);
void R_Rear_Init(void);
void L_Rear_Init(void);
void Tail_Init(void);

//占空比设置
void R_Front_SetDuty(uint8_t duty);
void L_Front_SetDuty(uint8_t duty);
void R_Rear_SetDuty(uint8_t duty);
void L_Rear_SetDuty(uint8_t duty);
void Tail_SetDuty(uint8_t duty);

#endif /* PWM_PWM_H_ */
