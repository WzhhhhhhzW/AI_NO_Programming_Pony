#include "Face.h"
#include "oled.h"


void Face_Forward()
{
    OLED_Clear();//清屏
    OLED_ShowChinese(100,40,0,16,1);
    OLED_ShowChinese(100,10,1,16,1);
}

void Face_Sleep()
{
    OLED_Clear();
    OLED_ShowChinese(100,40,2,16,1);
    OLED_ShowChinese(100,10,3,16,1);
}
