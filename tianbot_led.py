#!/usr/bin/env python

import numpy as np
import rospy
import serial
from std_msgs.msg import Int32

Number_of_leds = 24

# 设置串口
ser = serial.Serial('/dev/ttyACM1', 115200)  # 请根据实际情况修改串口名称和波特率

Led_Mode_state = 0
Led_RGB_state = 0


def Led_callback(led_values):
    decoded_data = Led_decode(led_values)
    led_list = Led_logic(decoded_data)
    Led_drive(led_list)


def led_mode_callback(data):
    global Led_Mode_state
    global Led_RGB_state
    Led_Mode_state = data.data
    if (not Led_RGB_state == 0):
        Led_receive_data = Led_RGB_state + Led_Mode_state << 32
        Led_callback(Led_receive_data)


def led_rgb_callback(data):
    global Led_Mode_state
    global Led_RGB_state
    Led_RGB_state = data.data
    if (not Led_Mode_state == 0):
        Led_receive_data = Led_RGB_state + Led_Mode_state << 32
        Led_callback(Led_receive_data)


def Led_drive(led_values):
    global Led_Mode_state
    global Led_RGB_state
    Led_index_list = []
    for i in led_values:
        Led_index, RGB = i
        Led_index = Led_index % Number_of_leds
        Led_index_list.append(Led_index)
        r, g, b = RGB
        message = f"l {Led_index} {r} {g} {b}\n"
        ser.write(message.encode('utf-8'))
        rospy.loginfo(f"Sent: {message}")
    # 使用numpy的集合操作来找出不在Led_index_list中的元素
    Led_off_index_list = np.setdiff1d(np.arange(Number_of_leds), Led_index_list)
    for i in Led_off_index_list:
        message = f"l {i} {0} {0} {0}\n"  # 关闭没有提到的led
        ser.write(message.encode('utf-8'))
    Led_Mode_state = 0
    Led_RGB_state = 0


def Led_decode(data):
    # 将64位数据分解成指定的位格式
    if data >= (1 << 64):  # 确保data是64位的
        raise ValueError("Input data must be a 64-bit number.")
    Led_mode = (data >> 56) & 0xFF  # led显示模式
    Led_start_position = Number_of_leds * ((data >> 48) & 0xFF) // 240  # led起始位置
    Led_reserved1 = (data >> 32) & 0xFFFF  # 第一个预留位，预留16位
    Led_decode_data = [Led_mode, Led_start_position, Led_reserved1]  # 解码得到的值以数组形式保存与返回
    if (Led_mode in [6, 7, 8, 9, 13]):  # 在6 7 8 9 13模式下解码有不同
        # 9bit 9bit 9bit 5bit
        Led_reserved2 = data & 0x1F  # 第二个预留位，此模式下预留5位
        data = data >> 5  # 把预留位排除
        for i in range(9):  # 循环遍历27位数据，每次处理3位
            three_bits = (data >> ((8 - i) * 3)) & 0x07  # 提取当前的三位值（从低位到高位） 0x07是二进制的0000 0111
            Led_decode_data.append(three_bits)  # 将三位值添加到数组中
        Led_decode_data.append(Led_reserved2)  # 把预留位加到数组里
    else:
        # 12bit 8bit 12bit
        LED_R = ((data >> 28) & 0x0F) * 16  # LED的R值
        LED_G = ((data >> 24) & 0x0F) * 16  # LED的G值
        LED_B = ((data >> 20) & 0x0F) * 16  # LED的B值
        Led_RGB_Mode = (data >> 12) & 0xFF  # RGB模式位
        LED2_R = ((data >> 8) & 0x0F) * 16  # LED的R值
        LED2_G = ((data >> 4) & 0x0F) * 16  # LED的G值
        LED2_B = (data & 0x0F) * 16  # LED的B值
        Led_decode_data.extend([LED_R, LED_G, LED_B, Led_RGB_Mode, LED2_R, LED2_G, LED2_B])
    return Led_decode_data


def Led_logic(decode_data):
    Led_list = []  # 建一个给初始用于传递的数组
    Led_mode = decode_data[0]
    Led_start_position = decode_data[1]
    if (Led_mode in [6, 7, 8, 9, 13]):  # 在6 7 8 9 13模式下解码有不同
        Led_RGB_1 = decode_data[3:6]
        Led_RGB_2 = decode_data[6:9]
        Led_RGB_3 = decode_data[9:12]
    else:
        Led_RGB = decode_data[3:6]
        Led_RGB_Mode = decode_data[6]
        Led_RGB2 = decode_data[7:10]  # 第二个RGB

    if (Led_start_position > Number_of_leds or Led_start_position < 0):
        print('Led_start_position no found')
        return Led_list

    if (Led_mode == 1):  # 单灯模式
        Led_list.append([Led_start_position, Led_RGB])  # 仅一个灯亮，将亮灯的位置赋予rgb值。
    if (Led_mode == 2):  # 双灯模式
        Led_end_position = Led_start_position + Number_of_leds // 2  # 计算尾灯位置
        if (Led_RGB_Mode == 0):  # 尾灯自定义
            Led_list.append([Led_start_position, Led_RGB])
            Led_list.append([Led_end_position, Led_RGB2])
        if (Led_RGB_Mode == 1):  # 双灯同色
            Led_list.append([Led_start_position, Led_RGB])
            Led_list.append([Led_end_position, Led_RGB])
        if (Led_RGB_Mode == 2):  # 尾灯白色
            Led_list.append([Led_start_position, Led_RGB])
            Led_list.append([Led_end_position, [255, 255, 255]])
        if (Led_RGB_Mode == 3):  # 尾灯黑色
            Led_list.append([Led_start_position, Led_RGB])
    if (Led_mode == 3):  # 正三角三灯模式
        Led_list.append([Led_start_position, Led_RGB])
        Led_list.append([Led_start_position + Number_of_leds // 3, Led_RGB2])
        Led_list.append([Led_start_position - Number_of_leds // 3, Led_RGB2])
    if (Led_mode == 4):  # 瘦三角三灯模式
        Led_list.append([Led_start_position, Led_RGB])
        Led_list.append([Led_start_position + 1, Led_RGB])
        Led_list.append([Led_start_position + Number_of_leds // 3, Led_RGB2])
        Led_list.append([Led_start_position + 1 + Number_of_leds // 3, Led_RGB2])
        Led_list.append([Led_start_position - Number_of_leds // 3, Led_RGB2])
        Led_list.append([Led_start_position - 1 - Number_of_leds // 3, Led_RGB2])
    if (Led_mode == 5):  # 胖三角三灯模式
        for i in range(4):
            Led_list.append([Led_start_position + i, Led_RGB])
            Led_list.append([Led_start_position + i + Number_of_leds // 3, Led_RGB2])
            Led_list.append([Led_start_position + i - Number_of_leds // 3, Led_RGB2])
    if (Led_mode == 6):  # 单灯三角模式
        Led_position_2 = (decode_data[2] >> 8) & 0xFF
        Led_position_3 = decode_data[2] & 0xFF
        Led_list.append([Led_start_position, Led_RGB_1])
        Led_list.append([Led_position_2, Led_RGB_2])
        Led_list.append([Led_position_3, Led_RGB_3])
    if (Led_mode == 7):  # 三角三灯模式
        Led_list.append([Led_start_position, Led_RGB_1])
        Led_list.append([Led_start_position + Number_of_leds // 3, Led_RGB_2])
        Led_list.append([Led_start_position - Number_of_leds // 3, Led_RGB_3])
    if (Led_mode == 8):  # 瘦角三灯模式
        Led_list.append([Led_start_position, Led_RGB_1])
        Led_list.append([Led_start_position + 1, Led_RGB_1])
        Led_list.append([Led_start_position + Number_of_leds // 3, Led_RGB_2])
        Led_list.append([Led_start_position + 1 + Number_of_leds // 3, Led_RGB_2])
        Led_list.append([Led_start_position - Number_of_leds // 3, Led_RGB_3])
        Led_list.append([Led_start_position - 1 - Number_of_leds // 3, Led_RGB_3])
    if (Led_mode == 9):  # 胖三角三灯模式
        for i in range(4):
            Led_list.append([Led_start_position + i, Led_RGB_1])
            Led_list.append([Led_start_position + i + Number_of_leds // 3, Led_RGB_2])
            Led_list.append([Led_start_position + i - Number_of_leds // 3, Led_RGB_3])
    if (Led_mode == 10):  # 区域模式
        Led_on_number = decode_data[2] & 0x0F
        for i in range(Led_on_number):
            Led_list.append([Led_start_position + i, Led_RGB])
    if (Led_mode == 11):  # 箭头模式
        Led_list.append([Led_start_position + Number_of_leds // 2, Led_RGB])
        for i in range(5):
            Led_list.append([Led_start_position + i - 2, Led_RGB])
    if (Led_mode == 12):  # 方形模式
        for i in range(4):
            Led_list.append([Led_start_position + i * Number_of_leds // 4, Led_RGB])
    if (Led_mode == 13):  # 方形（自定义）
        Led_list.append([Led_start_position, Led_RGB_1])
        Led_list.append([Led_start_position + Number_of_leds // 4, Led_RGB_2])
        Led_list.append([Led_start_position - Number_of_leds // 4, Led_RGB_3])
        Led_list.append([Led_start_position + Number_of_leds // 2, Led_RGB_1])
    if (Led_mode == 14):  # 渐变模式
        if (Led_RGB_Mode == 0):
            Led_range_color_list = np.linspace(Led_RGB, [0, 0, 0], (Number_of_leds // 2 + 1)).astype(
                np.uint8)  # 灯到起点的距离为索引
        else:
            Led_range_color_list = np.logspace(np.log10(Led_RGB), [0, 0, 0], (Number_of_leds // 2 + 1)).astype(
                np.uint8)  # 等比例衰减，有可能衰减的有点快
        for i in range(Number_of_leds):
            i_to_start = min(abs(i - Led_start_position), Number_of_leds - abs(i - Led_start_position))
            Led_list.append([i, Led_range_color_list[i_to_start]])
    return Led_list


def listener():
    rospy.init_node('leds_controller', anonymous=True)
    rospy.Subscriber('tianbot_01/led_mode', Int32, led_mode_callback)
    rospy.Subscriber('tianbot_01/led_rgb', Int32, led_rgb_callback)
    rospy.spin()


if __name__ == '__main__':
    try:
        listener()
    except rospy.ROSInterruptException:
        pass
    finally:
        ser.close()
