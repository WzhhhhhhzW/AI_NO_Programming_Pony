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
void Face_Stand()
{
    OLED_Clear();
    OLED_ShowChinese(100,40,4,16,1);
    OLED_ShowChinese(100,10,5,16,1);
}
void Face_Hand()
{
    OLED_Clear();
    OLED_ShowChinese(100,40,6,16,1);
    OLED_ShowChinese(100,10,7,16,1);
}
void Face_Turnleft()
{
    OLED_Clear();
    OLED_ShowChinese(100,40,8,16,1);
    OLED_ShowChinese(100,10,9,16,1);
}
void Face_TurnRight()
{
    OLED_Clear();
    OLED_ShowChinese(100,40,10,16,1);
    OLED_ShowChinese(100,10,11,16,1);
}
void Face_Tail()
{
    OLED_Clear();
    OLED_ShowChinese(100,40,12,16,1);
    OLED_ShowChinese(100,25,13,16,1);
    OLED_ShowChinese(100,10,14,16,1);
}






