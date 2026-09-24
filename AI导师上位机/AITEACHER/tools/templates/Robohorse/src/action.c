#include "action.h"
#include "PWM.h"

int R_Front_Goal = 0;
int L_Front_Goal = 0;
int R_Rear_Goal = 0;
int L_Rear_Goal = 0;

void stand()//站起来
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


void Turn_Right()
{
    L_Front_SetDuty(4);
    for(int i = 0;i<5;i++)
    {
        R_Front_SetDuty(5);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(8);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(9);
        R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);

        R_Front_SetDuty(9);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(5);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(6);
        R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
    }
}

    void Turn_Left()
    {
        R_Front_SetDuty(10);
        for(int i = 0;i<5;i++)
        {
            L_Front_SetDuty(4);
            R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
            R_Rear_SetDuty(9);
            R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
            L_Rear_SetDuty(10);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);

            L_Front_SetDuty(10);
            R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
            R_Rear_SetDuty(4);
            R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
            L_Rear_SetDuty(5);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
        }
    }

    void Shake_Tail()
    {
        R_Front_SetDuty(11);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(3);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        for(int i = 0;i<5;i++)
        {
            Tail_SetDuty(3);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
            Tail_SetDuty(11);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
        }
    }

    void Shake_Hand()
    {
        R_Rear_SetDuty(3);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(11);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        for(int i = 0;i<5;i++)
        {
            R_Front_SetDuty(12);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
            R_Front_SetDuty(9);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
        }

    }

    void Gasp()
    {
        R_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Rear_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        R_Front_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);
        L_Front_SetDuty(7);
        R_BSP_SoftwareDelay(20, BSP_DELAY_UNITS_MILLISECONDS);

    }


















