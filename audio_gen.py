# -*- coding: utf-8 -*-
"""
生成回铃音wav文件（中国标准回铃音：440Hz，响1秒停3秒）
APP启动时自动调用，无需手动运行
"""
import wave
import struct
import math
import os


def 生成回铃音(文件路径, 时长秒=20):
    """生成中国标准回铃音：450Hz，响1秒停4秒（周期5秒）"""
    if os.path.exists(文件路径):
        return True
    try:
        采样率 = 8000
        振幅 = 14000
        频率 = 450  # 中国回铃音标准频率
        with wave.open(文件路径, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(采样率)
            for i in range(int(采样率 * 时长秒)):
                t = i / 采样率
                周期位置 = t % 5  # 5秒周期：响1秒，停4秒
                if 周期位置 < 1:
                    if 周期位置 < 0.05: 音量 = 周期位置 / 0.05
                    elif 周期位置 > 0.95: 音量 = (1 - 周期位置) / 0.05
                    else: 音量 = 1.0
                    # 方波（真实电话音是方波，比正弦波更像）
                    样本 = int(振幅 * 音量) if math.sin(2 * math.pi * 频率 * t) >= 0 else int(-振幅 * 音量)
                else:
                    样本 = 0
                wf.writeframes(struct.pack('<h', 样本))
        print(f"回铃音已生成: {文件路径}")
        return True
    except Exception as e:
        print(f"回铃音生成失败: {e}")
        return False


def 生成忙音(文件路径, 时长秒=10):
    """生成中国标准忙音：450Hz，响0.5秒停0.5秒（周期1秒），节奏规律"""
    if os.path.exists(文件路径):
        return True
    try:
        采样率 = 8000
        振幅 = 12000
        频率 = 450  # 中国忙音标准频率
        with wave.open(文件路径, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(采样率)
            for i in range(int(采样率 * 时长秒)):
                t = i / 采样率
                周期位置 = t % 1  # 1秒周期：响0.5秒，停0.5秒
                if 周期位置 < 0.5:
                    # 方波
                    样本 = 振幅 if math.sin(2 * math.pi * 频率 * t) >= 0 else -振幅
                else:
                    样本 = 0
                wf.writeframes(struct.pack('<h', 样本))
        print(f"忙音已生成: {文件路径}")
        return True
    except Exception as e:
        print(f"忙音生成失败: {e}")
        return False


def 生成挂断音(文件路径):
    """生成短促挂断音：450Hz方波，响0.2秒（咔哒一声）"""
    if os.path.exists(文件路径):
        return True
    try:
        采样率 = 8000
        振幅 = 12000
        频率 = 450
        时长秒 = 0.25
        with wave.open(文件路径, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(采样率)
            for i in range(int(采样率 * 时长秒)):
                t = i / 采样率
                # 淡入淡出
                if t < 0.02: 音量 = t / 0.02
                elif t > 时长秒 - 0.02: 音量 = (时长秒 - t) / 0.02
                else: 音量 = 1.0
                样本 = int(振幅 * 音量) if math.sin(2 * math.pi * 频率 * t) >= 0 else int(-振幅 * 音量)
                wf.writeframes(struct.pack('<h', 样本))
        print(f"挂断音已生成: {文件路径}")
        return True
    except Exception as e:
        print(f"挂断音生成失败: {e}")
        return False


if __name__ == "__main__":
    目录 = os.path.dirname(os.path.abspath(__file__))
    生成回铃音(os.path.join(目录, "ringback.wav"))
    生成忙音(os.path.join(目录, "busy.wav"))
    print("音频生成完成")
