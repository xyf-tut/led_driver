#!/usr/bin/env python
import time
import serial
import numpy as np

Number_of_leds = 24

# 设置串口
ser = serial.Serial('/dev/ttyACM1', 115200)  # 请根据实际情况修改串口名称和波特率

def Led_drive(led_values):
    for i in range(Number_of_leds):
        r = led_values[i * 3]
        g = led_values[i * 3 + 1]
        b = led_values[i * 3 + 2]
        message = f"l {i} {r} {g} {b}\n"
        ser.write(message.encode('utf-8'))
        print(message)
        #rospy.loginfo(f"Sent: {message}")

def Led_decode(data):
    # 将64位数据分解成指定的位格式
    if data >= (1 << 64):  # 确保data是64位的
        raise ValueError("Input data must be a 64-bit number.")
    Led_mode = (data >> 56) & 0xFF  # led显示模式
    Led_start_position = (data >> 48) & 0xFF  # led起始位置
    Led_reserved1 = (data >> 32) & 0xFFFF  # 第一个预留位，预留16位
    Led_decode_data = [Led_mode, Led_start_position, Led_reserved1]  # 解码得到的值以数组形式保存与返回
    if (Led_mode in [6, 7, 8, 9, 13]):  # 在6 7 8 9 13模式下解码有不同
        # 8bit 8bit 16bit 9bit 9bit 9bit 5bit
        Led_reserved2 = data & 0x1F  # 第二个预留位，此模式下预留5位
        data = data >> 5  # 把预留位排除
        for i in range(9):  # 循环遍历27位数据，每次处理3位
            three_bits = (data >> ((8 - i) * 3)) & 0x07  # 提取当前的三位值（从低位到高位） 0x07是二进制的0000 0111
            Led_decode_data.append(three_bits)  # 将三位值添加到数组中
        Led_decode_data.append(Led_reserved2)  # 把预留位加到数组里
    else:
        # 8bit 8bit 16bit 12bit 8bit 12bit
        LED_R = ((data >> 28) & 0x0F) * 16  # LED的R值
        LED_G = ((data >> 24) & 0x0F) * 16  # LED的G值
        LED_B = ((data >> 20) & 0x0F) * 16  # LED的B值
        Led_RGB_Mode = (data >> 12) & 0xFF  # RGB模式位
        Led_reserved2 = data & 0xFFF  # 第二个预留位，此模式下预留12位
        Led_decode_data.extend([LED_R, LED_G, LED_B, Led_RGB_Mode, Led_reserved2])
    return Led_decode_data


def Led_logic(decode_data):
    Led_list = np.zeros(Number_of_leds * 3).astype(np.uint8)  # 建一个给回调函数的数组
    Led_mode = decode_data[0]
    Led_start_position = decode_data[1]
    if (Led_start_position > Number_of_leds or Led_start_position < 0):
        print('Led_start_position no found')
        return Led_list
    Led_RGB = decode_data[3:6]
    Led_reserved2 = decode_data[7]
    if (Led_mode == 1):  # 单灯模式
        Led_list[3 * Led_start_position:3 * Led_start_position + 3] = Led_RGB  # 仅一个灯亮，将亮灯的位置赋予rgb值。
    if (Led_mode == 2):  # 双灯模式
        Led_RGB_Mode = decode_data[6]
        Led_end_position = (Led_start_position + int(Number_of_leds / 2)) % Number_of_leds  # 计算尾灯位置
        if (Led_RGB_Mode == 1):  # 双灯同色
            Led_list[3 * Led_start_position:3 * Led_start_position + 3] = Led_RGB
            Led_list[3 * Led_end_position:3 * Led_end_position + 3] = Led_RGB
        if (Led_RGB_Mode == 2):  # 尾灯白色
            Led_list[3 * Led_start_position:3 * Led_start_position + 3] = Led_RGB
            Led_list[3 * Led_end_position:3 * Led_end_position + 3] = [255, 255, 255]
        if (Led_RGB_Mode == 3):  # 尾灯黑色
            Led_list[3 * Led_start_position:3 * Led_start_position + 3] = Led_RGB
    if (Led_mode == 12):  # 方形模式
        step = int(Number_of_leds / 4)
        Led_start_position = Led_start_position % step
        for i in range(4):
            print(i)
            Led_list[3 * (Led_start_position + i * step):3 * (Led_start_position + i * step) + 3] = Led_RGB
    Led_drive(Led_list)

datelist=[0x0112000012103000,0x0C12000012103000,0x0212000012101000,0x0212000012102000,0x0212000012103000,0x0112000000003000]
while(True):
    for i in range(6):
        led_values=datelist[i]
        decoded_data = Led_decode(led_values)
        Led_logic(decoded_data)
        time.sleep(2)
    break

