#include "PWM.h"


//右前腿初始化
//void R_Front_Init(void)
//{
//    /* 初始化 GPT 模块 */
//    R_GPT_Open(&R_Front_Foot_ctrl, &R_Front_Foot_cfg);
 //   /* 启动 GPT 定时器 */
 //   R_GPT_Start(&R_Front_Foot_ctrl);
//}

//前腿初始化
void Front_Init(void)
{
    /* 初始化 GPT 模块 */
    R_GPT_Open(&Front_Foot_ctrl, &Front_Foot_cfg);
    /* 启动 GPT 定时器 */
    R_GPT_Start(&Front_Foot_ctrl);
}
//右后腿初始化
void R_Rear_Init(void)
{
    /* 初始化 GPT 模块 */
    R_GPT_Open(&R_Rear_Foot_ctrl, &R_Rear_Foot_cfg);
    /* 启动 GPT 定时器 */
    R_GPT_Start(&R_Rear_Foot_ctrl);
}
//左后腿初始化
void L_Rear_Init(void)
{
    /* 初始化 GPT 模块 */
    R_GPT_Open(&L_Rear_Foot_ctrl, &L_Rear_Foot_cfg);
    /* 启动 GPT 定时器 */
    R_GPT_Start(&L_Rear_Foot_ctrl);
}
//尾巴初始化
void Tail_Init(void)
{
    /* 初始化 GPT 模块 */
    R_GPT_Open(&Tail_ctrl, &Tail_cfg);
    /* 启动 GPT 定时器 */
    R_GPT_Start(&Tail_ctrl);
}



//设置右前腿的占空比
void R_Front_SetDuty(uint8_t duty)
{
    timer_info_t info1;
    uint32_t current_period_counts1;
    uint32_t duty_cycle_counts1;

    if (duty > 100)
        duty = 100; //限制占空比范围：0~100

    /* 获得GPT的信息 */
    R_GPT_InfoGet(&Front_Foot_ctrl, &info1);

    /* 获得计时器一个周期需要的计数次数 */
    current_period_counts1 = info1.period_counts;

    /* 根据占空比和一个周期的计数次数计算GTCCR寄存器的值 */
    duty_cycle_counts1 = (uint32_t)(((uint64_t) current_period_counts1 *(100 - duty)) / 100);

    /* 最后调用FSP库函数设置占空比 */
    R_GPT_DutyCycleSet(&Front_Foot_ctrl, duty_cycle_counts1, GPT_IO_PIN_GTIOCB);
}

//设置左前腿的占空比
void L_Front_SetDuty(uint8_t duty)
{
    timer_info_t info;
    uint32_t current_period_counts;
    uint32_t duty_cycle_counts;

    if (duty > 100)
        duty = 100; //限制占空比范围：0~100

    /* 获得GPT的信息 */
    R_GPT_InfoGet(&Front_Foot_ctrl, &info);

    /* 获得计时器一个周期需要的计数次数 */
    current_period_counts = info.period_counts;

    /* 根据占空比和一个周期的计数次数计算GTCCR寄存器的值 */
    duty_cycle_counts = (uint32_t)(((uint64_t) current_period_counts *(100 - duty)) / 100);

    /* 最后调用FSP库函数设置占空比 */
    R_GPT_DutyCycleSet(&Front_Foot_ctrl, duty_cycle_counts, GPT_IO_PIN_GTIOCA);
}

//设置左后腿的占空比
void L_Rear_SetDuty(uint8_t duty)
{
    timer_info_t info;
    uint32_t current_period_counts;
    uint32_t duty_cycle_counts;

    if (duty > 100)
        duty = 100; //限制占空比范围：0~100

    /* 获得GPT的信息 */
    R_GPT_InfoGet(&L_Rear_Foot_ctrl, &info);

    /* 获得计时器一个周期需要的计数次数 */
    current_period_counts = info.period_counts;

    /* 根据占空比和一个周期的计数次数计算GTCCR寄存器的值 */
    duty_cycle_counts = (uint32_t)(((uint64_t) current_period_counts *(100 - duty)) / 100);

    /* 最后调用FSP库函数设置占空比 */
    R_GPT_DutyCycleSet(&L_Rear_Foot_ctrl, duty_cycle_counts, GPT_IO_PIN_GTIOCA);
}
//设置右后腿的占空比
void R_Rear_SetDuty(uint8_t duty)
{
    timer_info_t info;
    uint32_t current_period_counts;
    uint32_t duty_cycle_counts;

    if (duty > 100)
        duty = 100; //限制占空比范围：0~100

    /* 获得GPT的信息 */
    R_GPT_InfoGet(&R_Rear_Foot_ctrl, &info);

    /* 获得计时器一个周期需要的计数次数 */
    current_period_counts = info.period_counts;

    /* 根据占空比和一个周期的计数次数计算GTCCR寄存器的值 */
    duty_cycle_counts = (uint32_t)(((uint64_t) current_period_counts *(100 - duty)) / 100);

    /* 最后调用FSP库函数设置占空比 */
    R_GPT_DutyCycleSet(&R_Rear_Foot_ctrl, duty_cycle_counts, GPT_IO_PIN_GTIOCA);
}
//设置尾巴的占空比
void Tail_SetDuty(uint8_t duty)
{
    timer_info_t info;
    uint32_t current_period_counts;
    uint32_t duty_cycle_counts;

    if (duty > 100)
        duty = 100; //限制占空比范围：0~100

    /* 获得GPT的信息 */
    R_GPT_InfoGet(&Tail_ctrl, &info);

    /* 获得计时器一个周期需要的计数次数 */
    current_period_counts = info.period_counts;

    /* 根据占空比和一个周期的计数次数计算GTCCR寄存器的值 */
    duty_cycle_counts = (uint32_t)(((uint64_t) current_period_counts *(100 - duty)) / 100);

    /* 最后调用FSP库函数设置占空比 */
    R_GPT_DutyCycleSet(&Tail_ctrl, duty_cycle_counts, GPT_IO_PIN_GTIOCA);
}


