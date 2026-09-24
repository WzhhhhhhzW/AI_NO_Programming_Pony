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
void Tail_Init(void);

//占空比设置
void Tail_SetDuty(uint8_t duty);

#endif /* PWM_PWM_H_ */
