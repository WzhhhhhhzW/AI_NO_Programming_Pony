/* generated HAL header file - do not edit */
#ifndef HAL_DATA_H_
#define HAL_DATA_H_
#include <stdint.h>
#include "bsp_api.h"
#include "common_data.h"
#include "r_iic_master.h"
#include "r_i2c_master_api.h"
#include "r_sci_uart.h"
#include "r_uart_api.h"
#include "r_gpt.h"
#include "r_timer_api.h"
FSP_HEADER
/* I2C Master on IIC Instance. */
extern const i2c_master_instance_t OLED;

/** Access the I2C Master instance using these structures when calling API functions directly (::p_api is not used). */
extern iic_master_instance_ctrl_t OLED_ctrl;
extern const i2c_master_cfg_t OLED_cfg;

#ifndef OLED_callback
void OLED_callback(i2c_master_callback_args_t *p_args);
#endif
/** UART on SCI Instance. */
extern const uart_instance_t Blue_Tooth;

/** Access the UART instance using these structures when calling API functions directly (::p_api is not used). */
extern sci_uart_instance_ctrl_t Blue_Tooth_ctrl;
extern const uart_cfg_t Blue_Tooth_cfg;
extern const sci_uart_extended_cfg_t Blue_Tooth_cfg_extend;

#ifndef Blue_Tooth_Callback
void Blue_Tooth_Callback(uart_callback_args_t *p_args);
#endif
/** Timer on GPT Instance. */
extern const timer_instance_t Tail;

/** Access the GPT instance using these structures when calling API functions directly (::p_api is not used). */
extern gpt_instance_ctrl_t Tail_ctrl;
extern const timer_cfg_t Tail_cfg;

#ifndef NULL
void NULL(timer_callback_args_t *p_args);
#endif
/** Timer on GPT Instance. */
extern const timer_instance_t L_Rear_Foot;

/** Access the GPT instance using these structures when calling API functions directly (::p_api is not used). */
extern gpt_instance_ctrl_t L_Rear_Foot_ctrl;
extern const timer_cfg_t L_Rear_Foot_cfg;

#ifndef NULL
void NULL(timer_callback_args_t *p_args);
#endif
/** Timer on GPT Instance. */
extern const timer_instance_t R_Rear_Foot;

/** Access the GPT instance using these structures when calling API functions directly (::p_api is not used). */
extern gpt_instance_ctrl_t R_Rear_Foot_ctrl;
extern const timer_cfg_t R_Rear_Foot_cfg;

#ifndef NULL
void NULL(timer_callback_args_t *p_args);
#endif
/** Timer on GPT Instance. */
extern const timer_instance_t Front_Foot;

/** Access the GPT instance using these structures when calling API functions directly (::p_api is not used). */
extern gpt_instance_ctrl_t Front_Foot_ctrl;
extern const timer_cfg_t Front_Foot_cfg;

#ifndef NULL
void NULL(timer_callback_args_t *p_args);
#endif
void hal_entry(void);
void g_hal_init(void);
FSP_FOOTER
#endif /* HAL_DATA_H_ */
