#include "action.h"
#include "PWM.h"

void Shake_Tail()
    {
        for(int i = 0;i<5;i++)
        {
            Tail_SetDuty(3);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
            Tail_SetDuty(11);
            R_BSP_SoftwareDelay(250, BSP_DELAY_UNITS_MILLISECONDS);
        }
    }












