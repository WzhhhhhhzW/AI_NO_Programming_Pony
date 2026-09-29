#include "action.h"
#include "PWM.h"

int R_Front_Goal = 0;
int L_Front_Goal = 0;
int R_Rear_Goal = 0;
int L_Rear_Goal = 0;

void stand()//内部姿态复位：用于上电及前进结束，不提供独立遥控指令
{
    R_Rear_SetDuty(7);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
    L_Rear_SetDuty(7);
    R_BSP_SoftwareDelay(500, BSP_DELAY_UNITS_MILLISECONDS);

    R_Front_SetDuty(7);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
    L_Front_SetDuty(7);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);


}

void sleep()//趴下
{
    R_Front_SetDuty(11);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
    L_Front_SetDuty(3);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
    R_Rear_SetDuty(3);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
    L_Rear_SetDuty(11);
    R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
}

void Forward_OLD()//前进
{
    for(int i = 0;i<5;i++)
    {
        R_Front_SetDuty(9);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(5);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(9);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(5);
        R_BSP_SoftwareDelay(150, BSP_DELAY_UNITS_MILLISECONDS);

        R_Front_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(9);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(5);
        R_BSP_SoftwareDelay(150, BSP_DELAY_UNITS_MILLISECONDS);

        R_Front_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(7);
        R_BSP_SoftwareDelay(150, BSP_DELAY_UNITS_MILLISECONDS);

        R_Front_SetDuty(9);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(5);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(7);
        R_BSP_SoftwareDelay(150, BSP_DELAY_UNITS_MILLISECONDS);
    }
}
