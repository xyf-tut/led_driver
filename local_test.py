#!/usr/bin/env python
import time

import numpy as np
import serial

NUMBER_OF_LEDS = 24
SPECIAL_DECODE_MODE = [6, 7, 8, 9, 13]
# 设置串口
ser = serial.Serial('/dev/ttyACM0', 115200)  # 请根据实际情况修改串口名称和波特率


class light_mode():
    single_light = 1
    double_light = 2
    regular_triangle = 3
    thin_triangle = 4
    fat_triangle = 5
    single_light_triangle = 6
    triangle_three_light = 7
    thin_triangle_three_light = 8
    fat_triangle_three_light = 9
    zone_light = 10
    arrow_light = 11
    square_light = 12
    custom_square = 13
    gradualistic_light = 14


def led_drive(led_values):
    led_index_list = []
    for i in led_values:
        led_index, rgb = i
        led_index = led_index % NUMBER_OF_LEDS
        led_index_list.append(led_index)
        r, g, b = rgb
        message = f"l {led_index} {r} {g} {b}\n"
        ser.write(message.encode('utf-8'))
        print(message)
        # rospy.loginfo(f"Sent: {message}")
    # 使用numpy的集合操作来找出不在Led_index_list中的元素
    led_off_index_list = np.setdiff1d(np.arange(NUMBER_OF_LEDS), led_index_list)
    for i in led_off_index_list:
        message = f"l {i} {0} {0} {0}\n"  # 关闭没有提到的led
        ser.write(message.encode('utf-8'))


def led_decode(data):
    # 将64位数据分解成指定的位格式
    if data >= (1 << 64):  # 确保data是64位的
        raise ValueError("Input data must be a 64-bit number.")
    led_mode = (data >> 56) & 0xFF  # led显示模式
    led_start_position = (NUMBER_OF_LEDS * ((data >> 48) & 0xFF)) // 240  # led起始位置
    led_reserved1 = (data >> 32) & 0xFFFF  # 第一个预留位，预留16位
    led_decode_data = [led_mode, led_start_position, led_reserved1]  # 解码得到的值以数组形式保存与返回
    if (led_mode in SPECIAL_DECODE_MODE):  # 在6 7 8 9 13模式下解码有不同
        # 9bit 9bit 9bit 5bit
        led_reserved2 = data & 0x1F  # 第二个预留位，此模式下预留5位
        data = data >> 5  # 把预留位排除
        for i in range(9):  # 循环遍历27位数据，每次处理3位
            three_bits = (data >> ((8 - i) * 3)) & 0x07  # 提取当前的三位值（从低位到高位） 0x07是二进制的0000 0111
            led_decode_data.append(three_bits)  # 将三位值添加到数组中
        led_decode_data.append(led_reserved2)  # 把预留位加到数组里
    else:
        # 12bit 8bit 12bit
        led_r = ((data >> 28) & 0x0F) * 16  # LED的R值
        led_g = ((data >> 24) & 0x0F) * 16  # LED的G值
        led_b = ((data >> 20) & 0x0F) * 16  # LED的B值
        led_rgb_mode = (data >> 12) & 0xFF  # RGB模式位
        led2_r = ((data >> 8) & 0x0F) * 16  # LED的R值
        led2_g = ((data >> 4) & 0x0F) * 16  # LED的G值
        led2_b = (data & 0x0F) * 16  # LED的B值
        led_decode_data.extend([led_r, led_g, led_b, led_rgb_mode, led2_r, led2_g, led2_b])
    return led_decode_data


def led_logic(decode_data):
    led_list = []  # 建一个给初始用于传递的数组
    led_mode = decode_data[0]
    led_start_position = decode_data[1]
    if (led_mode in SPECIAL_DECODE_MODE):  # 在6 7 8 9 13模式下解码有不同
        led_rgb_1 = decode_data[3:6]
        led_rgb_2 = decode_data[6:9]
        led_rgb_3 = decode_data[9:12]
    else:
        led_rgb = decode_data[3:6]
        led_rgb_mode = decode_data[6]
        led_rgb2 = decode_data[7:10]  # 第二个RGB
    if (led_start_position > NUMBER_OF_LEDS or led_start_position < 0):
        print('Led_start_position no found')
        return led_list
    if (led_mode == light_mode.single_light):  # 单灯模式
        led_list.append([led_start_position, led_rgb])  # 仅一个灯亮，将亮灯的位置赋予rgb值。
    if (led_mode == light_mode.double_light):  # 双灯模式
        Led_end_position = led_start_position + NUMBER_OF_LEDS // 2  # 计算尾灯位置
        if (led_rgb_mode == 0):  # 尾灯自定义
            led_list.append([led_start_position, led_rgb])
            led_list.append([Led_end_position, led_rgb2])
        if (led_rgb_mode == 1):  # 双灯同色
            led_list.append([led_start_position, led_rgb])
            led_list.append([Led_end_position, led_rgb])
        if (led_rgb_mode == 2):  # 尾灯白色
            led_list.append([led_start_position, led_rgb])
            led_list.append([Led_end_position, [255, 255, 255]])
        if (led_rgb_mode == 3):  # 尾灯黑色
            led_list.append([led_start_position, led_rgb])
    if (led_mode == light_mode.regular_triangle):  # 正三角三灯模式
        led_list.append([led_start_position, led_rgb])
        led_list.append([led_start_position + NUMBER_OF_LEDS // 3, led_rgb2])
        led_list.append([led_start_position - NUMBER_OF_LEDS // 3, led_rgb2])
    if (led_mode == light_mode.thin_triangle):  # 瘦三角三灯模式
        led_list.append([led_start_position, led_rgb])
        led_list.append([led_start_position + 1, led_rgb])
        led_list.append([led_start_position + NUMBER_OF_LEDS // 3, led_rgb2])
        led_list.append([led_start_position + 1 + NUMBER_OF_LEDS // 3, led_rgb2])
        led_list.append([led_start_position - NUMBER_OF_LEDS // 3, led_rgb2])
        led_list.append([led_start_position - 1 - NUMBER_OF_LEDS // 3, led_rgb2])
    if (led_mode == light_mode.fat_triangle):  # 胖三角三灯模式
        for i in range(4):
            led_list.append([led_start_position + i, led_rgb])
            led_list.append([led_start_position + i + NUMBER_OF_LEDS // 3, led_rgb2])
            led_list.append([led_start_position + i - NUMBER_OF_LEDS // 3, led_rgb2])
    if (led_mode == light_mode.single_light_triangle):  # 单灯三角模式
        Led_position_2 = (decode_data[2] >> 8) & 0xFF
        Led_position_3 = decode_data[2] & 0xFF
        led_list.append([led_start_position, led_rgb_1])
        led_list.append([Led_position_2, led_rgb_2])
        led_list.append([Led_position_3, led_rgb_3])
        print('a', led_start_position, 'b', Led_position_2, 'c', Led_position_3)
    if (led_mode == light_mode.triangle_three_light):  # 三角三灯模式
        led_list.append([led_start_position, led_rgb_1])
        led_list.append([led_start_position + NUMBER_OF_LEDS // 3, led_rgb_2])
        led_list.append([led_start_position - NUMBER_OF_LEDS // 3, led_rgb_3])
    if (led_mode == light_mode.thin_triangle_three_light):  # 瘦角三灯模式
        led_list.append([led_start_position, led_rgb_1])
        led_list.append([led_start_position + 1, led_rgb_1])
        led_list.append([led_start_position + NUMBER_OF_LEDS // 3, led_rgb_2])
        led_list.append([led_start_position + 1 + NUMBER_OF_LEDS // 3, led_rgb_2])
        led_list.append([led_start_position - NUMBER_OF_LEDS // 3, led_rgb_3])
        led_list.append([led_start_position - 1 - NUMBER_OF_LEDS // 3, led_rgb_3])
    if (led_mode == light_mode.fat_triangle_three_light):  # 胖三角三灯模式
        for i in range(4):
            led_list.append([led_start_position + i, led_rgb_1])
            led_list.append([led_start_position + i + NUMBER_OF_LEDS // 3, led_rgb_2])
            led_list.append([led_start_position + i - NUMBER_OF_LEDS // 3, led_rgb_3])
    if (led_mode == light_mode.zone_light):  # 区域模式
        Led_on_number = decode_data[2] & 0x0F
        for i in range(Led_on_number):
            led_list.append([led_start_position + i, led_rgb])
    if (led_mode == light_mode.arrow_light):  # 箭头模式
        led_list.append([led_start_position + NUMBER_OF_LEDS // 2, led_rgb])
        for i in range(5):
            led_list.append([led_start_position + i - 2, led_rgb])
    if (led_mode == light_mode.square_light):  # 方形模式
        for i in range(4):
            led_list.append([led_start_position + i * NUMBER_OF_LEDS // 4, led_rgb])
    if (led_mode == light_mode.custom_square):  # 方形（自定义）
        led_list.append([led_start_position, led_rgb_1])
        led_list.append([led_start_position + NUMBER_OF_LEDS // 4, led_rgb_2])
        led_list.append([led_start_position - NUMBER_OF_LEDS // 4, led_rgb_3])
        led_list.append([led_start_position + NUMBER_OF_LEDS // 2, led_rgb_1])
    if (led_mode == light_mode.gradualistic_light):  # 渐变模式
        if (led_rgb_mode == 0):
            led_range_color_list = np.linspace(led_rgb, [0, 0, 0], (NUMBER_OF_LEDS // 2 + 1)).astype(
                np.uint8)  # 灯到起点的距离为索引
        else:
            led_range_color_list = np.logspace(np.log10(led_rgb), [0, 0, 0], (NUMBER_OF_LEDS // 2 + 1)).astype(
                np.uint8)  # 等比例衰减，有可能衰减的有点快
        for i in range(NUMBER_OF_LEDS):
            i_to_start = min(abs(i - led_start_position), NUMBER_OF_LEDS - abs(i - led_start_position))
            led_list.append([i, led_range_color_list[i_to_start]])
    return led_list


datelist = [0x01EF000011101000,
            0x0212000012101000,
            0x0312000012103242,
            0x0412000012103242,
            0x0512000012103242,
            0x0612334212103242,
            0x0712314112103242,
            0x0812314112103242,
            0x0912314112103242,
            0x0A12000412103000,
            0x0B12000412103000,
            0x0C12000012103000,
            0x0D12314112103242,
            0x0E12000012100000,
            0x0E12000012101000,
            0x0112000000003000]  # 本地测试数据

while (True):
    for i in range(len(datelist)):
        led_values = datelist[i]
        decoded_data = led_decode(led_values)
        led_list = led_logic(decoded_data)
        led_drive(led_list)
        time.sleep(1.5)
