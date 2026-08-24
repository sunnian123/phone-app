# -*- coding: utf-8 -*-
"""
虚拟电话APP - 仿vivo拨号界面（模拟通话版）
- 永远不接通，响铃到点自动挂断
- 回铃音（滴滴声）+ 运营商语音提示
- vivo风格深色通话界面（静音/键盘/免提/录音/挂断）
"""

import json
import os
import threading
import time

# ========== 全局中文字体配置 ==========
项目目录 = os.path.dirname(os.path.abspath(__file__))
字体候选路径 = [
    os.path.join(项目目录, "msyh.ttc"),
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/system/fonts/NotoSansCJK-Regular.ttc",
]
中文字体路径 = None
for 路径 in 字体候选路径:
    if os.path.exists(路径):
        中文字体路径 = 路径
        break

if 中文字体路径:
    from kivy.config import Config
    Config.set('kivy', 'default_font', ['中文字体', 中文字体路径, 中文字体路径, 中文字体路径, 中文字体路径])

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Ellipse
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest

try:
    from phone_parser import 手机号归属地解析器
except ImportError:
    手机号归属地解析器 = None

# ========== 音频 ==========
try:
    from audio_gen import 生成回铃音, 生成忙音, 生成挂断音
except ImportError:
    生成回铃音 = None
    生成忙音 = None
    生成挂断音 = None

try:
    from kivy.core.audio import SoundLoader
    音频可用 = True
except ImportError:
    音频可用 = False

回铃音对象 = None
忙音对象 = None
挂断音对象 = None
回铃音已播放 = False  # 防止重复调用play()导致声音被重置
语音正在播放 = False  # 防止语音重复播放
免提模式 = False  # 免提状态，控制音量


def 初始化音频():
    global 回铃音对象, 忙音对象, 挂断音对象
    回铃音路径 = os.path.join(项目目录, "ringback.wav")
    忙音路径 = os.path.join(项目目录, "busy.wav")
    挂断音路径 = os.path.join(项目目录, "hangup.wav")
    if 生成回铃音:
        生成回铃音(回铃音路径)
        生成忙音(忙音路径)
        生成挂断音(挂断音路径)
    if 音频可用:
        try:
            if os.path.exists(回铃音路径):
                回铃音对象 = SoundLoader.load(回铃音路径)
                if 回铃音对象:
                    回铃音对象.loop = True
                    回铃音对象.volume = 0.5
            if os.path.exists(忙音路径):
                忙音对象 = SoundLoader.load(忙音路径)
                if 忙音对象:
                    忙音对象.loop = True
                    忙音对象.volume = 0.4
            if os.path.exists(挂断音路径):
                挂断音对象 = SoundLoader.load(挂断音路径)
                if 挂断音对象:
                    挂断音对象.volume = 0.6
            print("音频初始化完成")
        except Exception as e:
            print(f"音频初始化失败: {e}")


def 播放回铃音():
    global 回铃音已播放
    if 回铃音已播放: return  # 已经在播放了，不重复调用
    if 回铃音对象:
        try:
            回铃音对象.volume = 0.9 if 免提模式 else 0.5
            回铃音对象.play()
            回铃音已播放 = True
        except Exception: pass


def 停止回铃音():
    global 回铃音已播放
    if 回铃音对象:
        try: 回铃音对象.stop()
        except Exception: pass
    回铃音已播放 = False


def 播放忙音():
    if 忙音对象:
        try: 忙音对象.play()
        except Exception: pass


def 停止忙音():
    if 忙音对象:
        try: 忙音对象.stop()
        except Exception: pass


def 播放挂断音():
    if 挂断音对象:
        try: 挂断音对象.play()
        except Exception: pass


# ========== 配置 ==========
配置文件路径 = os.path.join(项目目录, "电话配置.json")
默认配置 = {"服务器地址": "http://127.0.0.1:5000", "自动播报语音": True}

语音提示库 = {
    "无人接听": "您拨打的电话无人接听，请稍后再拨。",
    "已关机": "您拨打的电话已关机，请稍后再拨。",
    "正在通话中": "您拨打的电话正在通话中，请稍后再拨。",
    "暂时无法接通": "您拨打的电话暂时无法接通，请稍后再拨。",
    "空号": "您拨打的号码是空号，请核对后再拨。",
    "已停机": "您拨打的电话已停机。",
    "主动挂断": "通话结束。",
}

# 提示原因 → 预生成wav文件名映射（中文+英文双语）
语音文件映射 = {
    "无人接听": "voice_no_answer.wav",
    "已关机": "voice_power_off.wav",
    "正在通话中": "voice_busy.wav",
    "暂时无法接通": "voice_unreachable.wav",
    "空号": "voice_empty.wav",
    "已停机": "voice_out_of_service.wav",
}


def 播放语音文件(文件名):
    """播放预生成的wav语音文件"""
    global 语音正在播放
    if 语音正在播放: return False  # 防止重复播放
    if not 音频可用: return False
    路径 = os.path.join(项目目录, 文件名)
    if not os.path.exists(路径): return False
    try:
        声音 = SoundLoader.load(路径)
        if 声音:
            声音.volume = 1.0 if 免提模式 else 0.8
            声音.play()
            语音正在播放 = True
            # 15秒后重置标志（语音最长约12秒）
            def 重置标志(dt):
                global 语音正在播放
                语音正在播放 = False
            Clock.schedule_once(重置标志, 15)
            return True
    except Exception as e:
        print(f"播放语音文件失败: {e}")
    return False


def 语音播报(原因):
    """优先播放预生成mp3，没有则降级pyttsx3"""
    # 先尝试预生成的mp3文件
    if 原因 in 语音文件映射:
        if 播放语音文件(语音文件映射[原因]):
            return

    # 降级到pyttsx3实时播报
    文字 = 语音提示库.get(原因, "通话结束。")
    def 播报():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            for 语音 in engine.getProperty('voices'):
                if 'chinese' in 语音.id.lower() or '中文' in 语音.name or 'zh' in 语音.id.lower():
                    engine.setProperty('voice', 语音.id)
                    break
            engine.setProperty('rate', 175)
            engine.say(文字)
            engine.runAndWait()
        except Exception as e:
            print(f"语音播报失败（运行 python generate_voices.py 生成语音文件）: {e}")
    t = threading.Thread(target=播报, daemon=True)
    t.start()


# ========== 归属地数据 ==========
国家代码表 = {"1":"美国/加拿大","7":"俄罗斯","44":"英国","81":"日本","82":"韩国","65":"新加坡","61":"澳大利亚","49":"德国","33":"法国","39":"意大利","34":"西班牙","90":"土耳其","91":"印度","60":"马来西亚","66":"泰国","84":"越南","62":"印度尼西亚","63":"菲律宾","86":"中国","852":"中国香港","853":"中国澳门","886":"中国台湾","971":"阿联酋","966":"沙特阿拉伯","20":"埃及","27":"南非","55":"巴西","52":"墨西哥","31":"荷兰","32":"比利时","41":"瑞士","43":"奥地利","45":"丹麦","46":"瑞典","47":"挪威","48":"波兰","351":"葡萄牙","353":"爱尔兰","354":"冰岛","358":"芬兰","359":"保加利亚","370":"立陶宛","371":"拉脱维亚","372":"爱沙尼亚","375":"白俄罗斯","380":"乌克兰","381":"塞尔维亚","385":"克罗地亚","386":"斯洛文尼亚","420":"捷克","421":"斯洛伐克","36":"匈牙利","40":"罗马尼亚"}
移动号段 = {"134","135","136","137","138","139","147","148","150","151","152","157","158","159","172","178","182","183","184","187","188","195","197","198"}
联通号段 = {"130","131","132","145","146","155","156","166","167","171","175","176","185","186","196"}
电信号段 = {"133","149","153","173","174","177","180","181","189","190","191","193","199"}
广电号段 = {"192"}


def 识别运营商(前缀3位):
    if 前缀3位 in 移动号段: return "中国移动"
    if 前缀3位 in 联通号段: return "中国联通"
    if 前缀3位 in 电信号段: return "中国电信"
    if 前缀3位 in 广电号段: return "中国广电"
    return "未知运营商"


def 识别国家(号码):
    if not 号码.startswith("+"): return None, 号码
    纯数字 = 号码[1:]
    for 长度 in [4,3,2,1]:
        if len(纯数字) >= 长度:
            区号 = 纯数字[:长度]
            if 区号 in 国家代码表:
                return 国家代码表[区号], 纯数字[长度:]
    return "未知国家/地区", 纯数字


def 读取配置():
    if os.path.exists(配置文件路径):
        try:
            with open(配置文件路径, "r", encoding="utf-8") as f:
                配置 = json.load(f)
                if "服务器地址" not in 配置: 配置["服务器地址"] = "http://127.0.0.1:5000"
                if "自动播报语音" not in 配置: 配置["自动播报语音"] = True
                return 配置
        except Exception: pass
    return 默认配置.copy()


def 保存配置(配置字典):
    try:
        with open(配置文件路径, "w", encoding="utf-8") as f:
            json.dump(配置字典, f, ensure_ascii=False, indent=2)
    except Exception as e: print("保存配置失败:", e)


# ========== 圆形拨号按键 ==========
class 圆形按键(Button):
    def __init__(self, 主文字="", 副文字="", **kwargs):
        super().__init__(**kwargs)
        self.主文字 = 主文字
        self.副文字 = 副文字
        self.background_normal = ""
        self.background_down = ""
        self.color = (0.15,0.15,0.15,1)
        self.markup = True
        self.halign = "center"
        self.valign = "middle"
        self.更新文字()
        with self.canvas.before:
            self.按键颜色 = Color(0.93,0.93,0.95,1)
            self.按键背景 = RoundedRectangle(pos=self.pos, size=self.size, radius=[min(self.width,self.height)/2])
        self.bind(pos=self.更新背景, size=self.更新背景)

    def 更新文字(self):
        if self.副文字:
            self.text = f"[size=36]{self.主文字}[/size]\n[size=14][color=#999999]{self.副文字}[/color][/size]"
        else:
            self.text = f"[size=36]{self.主文字}[/size]"

    def 更新背景(self, *args):
        self.按键背景.pos = self.pos
        self.按键背景.size = self.size
        self.按键背景.radius = [min(self.width,self.height)/2]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos): self.按键颜色.rgba = (0.80,0.80,0.83,1)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self.按键颜色.rgba = (0.93,0.93,0.95,1)
        return super().on_touch_up(touch)


# ========== 功能圆形按钮（vivo风格深色）==========
class 功能圆形按钮(Button):
    def __init__(self, 文字="", 激活文字="", **kwargs):
        super().__init__(**kwargs)
        self.默认文字 = 文字
        self.激活文字 = 激活文字
        self.是否激活 = False
        self.text = 文字
        self.font_size = 12
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # 关键：移除默认矩形背景
        self.color = (1, 1, 1, 0.95)
        self.size_hint = (None, None)
        self.size = (64, 64)
        with self.canvas.before:
            self.按钮颜色 = Color(1, 1, 1, 0.18)
            self.按钮圆 = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self.更新背景, size=self.更新背景)
        self.bind(on_press=self.切换状态)

    def 更新背景(self, *args):
        self.按钮圆.pos = self.pos
        self.按钮圆.size = self.size

    def 切换状态(self, instance):
        self.是否激活 = not self.是否激活
        if self.是否激活:
            self.按钮颜色.rgba = (1, 1, 1, 0.95)
            self.color = (0.1, 0.1, 0.1, 1)
            self.text = self.激活文字 if self.激活文字 else self.默认文字
        else:
            self.按钮颜色.rgba = (1, 1, 1, 0.18)
            self.color = (1, 1, 1, 0.95)
            self.text = self.默认文字


# ========== 通话中界面（vivo深色风格）==========
class 通话中界面(BoxLayout):
    def __init__(self, 号码, 归属地, 挂断回调, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [30,40,30,30]
        self.spacing = 8
        self.挂断回调 = 挂断回调
        self.通话秒数 = 0
        self.状态 = "dialing"

        with self.canvas.before:
            self.背景色 = Color(0.10,0.10,0.12,1)
            self.背景矩形 = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i,v: setattr(self.背景矩形,'pos',v), size=lambda i,v: setattr(self.背景矩形,'size',v))

        self.add_widget(Label(size_hint_y=0.06))
        # 处理号码显示：去掉+86前缀
        显示号码 = 号码
        if 显示号码.startswith("+86"):
            显示号码 = 显示号码[3:]
        self.号码标签 = Label(text=显示号码, font_size=34, color=(1,1,1,1), size_hint_y=0.1, halign="center")
        self.add_widget(self.号码标签)
        self.归属地标签 = Label(text=归属地, font_size=13, color=(0.55,0.55,0.55,1), size_hint_y=0.04, halign="center")
        self.add_widget(self.归属地标签)
        self.add_widget(Label(size_hint_y=0.10))
        self.状态标签 = Label(text="正在拨号...", font_size=17, color=(0.75,0.75,0.75,1), size_hint_y=0.06, halign="center")
        self.add_widget(self.状态标签)
        # 键盘容器（默认隐藏，点击键盘按钮弹出DTMF键盘）
        self.键盘已弹出 = False
        self.键盘输入 = ""
        self.键盘父容器 = BoxLayout(orientation="vertical", size_hint_y=0, opacity=0, disabled=True, spacing=6)
        self.键盘输入栏 = Label(text="", font_size=20, color=(1,1,1,1), size_hint_y=0.15, halign="center")
        self.键盘父容器.add_widget(self.键盘输入栏)
        # 3x4 DTMF键盘
        键盘网格 = BoxLayout(orientation="vertical", spacing=5, size_hint_y=0.85)
        for 行 in [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]:
            行布局 = BoxLayout(spacing=8, padding=[20,0,20,0])
            for 数字 in 行:
                按键 = Button(text=数字, font_size=22, background_normal="", background_color=(0.25,0.25,0.28,1), color=(1,1,1,1), size_hint=(1/3,1))
                with 按键.canvas.before:
                    按键圆角 = RoundedRectangle(pos=按键.pos, size=按键.size, radius=[8])
                按键.bind(pos=lambda i,v,r=按键圆角: setattr(r,'pos',v), size=lambda i,v,r=按键圆角: setattr(r,'size',v))
                按键.bind(on_press=lambda btn,d=数字: self.输入键盘数字(d))
                行布局.add_widget(按键)
            键盘网格.add_widget(行布局)
        self.键盘父容器.add_widget(键盘网格)
        self.add_widget(self.键盘父容器)

        功能区 = BoxLayout(orientation="horizontal", size_hint_y=0.13, spacing=12, padding=[5,0,5,0])
        功能区.add_widget(Label())
        self.静音按钮 = 功能圆形按钮(文字="静音", 激活文字="已静音")
        功能区.add_widget(self.静音按钮)
        self.键盘按钮 = 功能圆形按钮(文字="键盘", 激活文字="键盘")
        self.键盘按钮.bind(on_press=self.切换键盘)
        功能区.add_widget(self.键盘按钮)
        self.免提按钮 = 功能圆形按钮(文字="免提", 激活文字="免提开")
        self.免提按钮.bind(on_press=self.切换免提模式)
        功能区.add_widget(self.免提按钮)
        self.录音按钮 = 功能圆形按钮(文字="录音", 激活文字="录音中")
        功能区.add_widget(self.录音按钮)
        功能区.add_widget(Label())
        self.add_widget(功能区)

        功能说明 = Label(text="静音      键盘      免提      录音", font_size=10, color=(0.45,0.45,0.45,1), size_hint_y=0.035, halign="center")
        self.add_widget(功能说明)
        self.add_widget(Label(size_hint_y=0.05))

        挂断容器 = BoxLayout(size_hint_y=0.13)
        挂断容器.add_widget(Label(size_hint_x=0.35))
        self.挂断按钮 = Button(text="挂断", font_size=15, size_hint_x=0.3, background_normal="", background_color=(0.88,0.16,0.16,1), color=(1,1,1,1))
        self.挂断按钮.bind(on_press=lambda btn: self.挂断回调())
        with self.挂断按钮.canvas.before:
            self.挂断圆角 = RoundedRectangle(pos=self.挂断按钮.pos, size=self.挂断按钮.size, radius=[32])
        self.挂断按钮.bind(pos=lambda i,v: setattr(self.挂断圆角,'pos',v), size=lambda i,v: setattr(self.挂断圆角,'size',v))
        挂断容器.add_widget(self.挂断按钮)
        挂断容器.add_widget(Label(size_hint_x=0.35))
        self.add_widget(挂断容器)

    def 更新状态(self, 状态, 状态文字, 通话秒数=0):
        self.状态 = 状态
        self.通话秒数 = 通话秒数
        if 状态 == "ringing":
            self.状态标签.text = "正在呼叫..."
            self.状态标签.color = (0.95,0.75,0.3,1)
        elif 状态 == "dialing":
            self.状态标签.text = "正在拨号..."
            self.状态标签.color = (0.5,0.7,0.95,1)
        else:
            self.状态标签.text = 状态文字
            self.状态标签.color = (0.65,0.65,0.65,1)

    def 切换免提模式(self, instance):
        """免提按钮：激活时放大音量，取消时恢复"""
        global 免提模式
        免提模式 = not 免提模式
        # 实时调整回铃音音量
        if 回铃音对象:
            try:
                回铃音对象.volume = 0.9 if 免提模式 else 0.5
            except Exception: pass

    def 切换键盘(self, instance):
        """点击键盘按钮：弹出/收起DTMF数字键盘"""
        if self.键盘已弹出:
            # 收起键盘
            self.键盘父容器.size_hint_y = 0
            self.键盘父容器.opacity = 0
            self.键盘父容器.disabled = True
            self.键盘已弹出 = False
        else:
            # 弹出键盘
            self.键盘父容器.size_hint_y = 0.32
            self.键盘父容器.opacity = 1
            self.键盘父容器.disabled = False
            self.键盘已弹出 = True

    def 输入键盘数字(self, 数字):
        """DTMF键盘输入数字"""
        self.键盘输入 += 数字
        self.键盘输入栏.text = self.键盘输入
        # 简单的DTMF音效果（可选，这里只做视觉）


# ========== 主界面 ==========
class 拨号主界面(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [15,8,15,12]
        self.spacing = 6
        self.当前号码 = ""
        self.配置 = 读取配置()
        self.归属地查询定时器 = None
        self.当前呼叫ID = None
        self.状态轮询事件 = None
        self.通话弹窗 = None

        self.离线解析器 = None
        if 手机号归属地解析器:
            try:
                self.离线解析器 = 手机号归属地解析器(os.path.join(项目目录, "phone.dat"))
            except Exception as e: print(f"离线库加载失败: {e}")

        顶栏 = BoxLayout(size_hint_y=0.05, orientation="horizontal")
        顶栏.add_widget(Label())
        设置按钮 = Button(text="设置", font_size=14, size_hint_x=0.18, background_normal="", background_color=(1,1,1,1), color=(0.3,0.3,0.3,1))
        设置按钮.bind(on_press=self.打开设置弹窗)
        顶栏.add_widget(设置按钮)
        self.add_widget(顶栏)

        self.号码标签 = Label(text="", font_size=44, color=(0.1,0.1,0.1,1), size_hint_y=0.16, halign="center", valign="middle")
        self.号码标签.bind(width=lambda i,v: setattr(self.号码标签,'text_size',(v,None)))
        self.add_widget(self.号码标签)

        self.归属地标签 = Label(text="", font_size=16, color=(0.5,0.5,0.5,1), size_hint_y=0.05, halign="center")
        self.add_widget(self.归属地标签)

        键盘容器 = BoxLayout(orientation="vertical", size_hint_y=0.56, spacing=8)
        for 行 in [[("1",""),("2","ABC"),("3","DEF")],[("4","GHI"),("5","JKL"),("6","MNO")],[("7","PQRS"),("8","TUV"),("9","WXYZ")],[("*",""),("0","+"),("#","")]]:
            行布局 = BoxLayout(spacing=10, padding=[5,0,5,0])
            for 主,副 in 行:
                按键 = 圆形按键(主文字=主, 副文字=副, size_hint=(1/3,1))
                按键.bind(on_press=lambda btn,m=主: self.输入数字(m))
                行布局.add_widget(按键)
            键盘容器.add_widget(行布局)
        self.add_widget(键盘容器)

        底部栏 = BoxLayout(size_hint_y=0.18, spacing=10, padding=[10,5,10,5])
        底部栏.add_widget(Label(size_hint_x=0.25))
        self.拨打按钮 = Button(text="拨打", font_size=22, size_hint_x=0.5, background_normal="", background_color=(0.18,0.72,0.38,1), color=(1,1,1,1))
        with self.拨打按钮.canvas.before:
            self.拨打圆角 = RoundedRectangle(pos=self.拨打按钮.pos, size=self.拨打按钮.size, radius=[25])
        self.拨打按钮.bind(pos=lambda i,v: setattr(self.拨打圆角,'pos',v), size=lambda i,v: setattr(self.拨打圆角,'size',v))
        self.拨打按钮.bind(on_press=self.执行拨打)
        底部栏.add_widget(self.拨打按钮)
        删除按钮 = Button(text="删除", font_size=16, size_hint_x=0.25, background_normal="", background_color=(0.93,0.93,0.95,1), color=(0.3,0.3,0.3,1))
        删除按钮.bind(on_press=self.删除一位)
        底部栏.add_widget(删除按钮)
        self.add_widget(底部栏)

    def 输入数字(self, 数字):
        self.当前号码 += 数字
        self.更新号码显示()
        self.更新归属地显示()

    def 删除一位(self, instance):
        self.当前号码 = self.当前号码[:-1]
        self.更新号码显示()
        self.更新归属地显示()

    def 更新号码显示(self):
        长度 = len(self.当前号码)
        字号 = 44 if 长度<=7 else (38 if 长度<=10 else (32 if 长度<=13 else 26))
        self.号码标签.font_size = 字号
        self.号码标签.text = self.当前号码

    def 更新归属地显示(self):
        号码 = self.当前号码.strip()
        if not 号码: self.归属地标签.text = ""; return
        if self.归属地查询定时器: self.归属地查询定时器.cancel(); self.归属地查询定时器 = None
        if 号码.startswith("+"):
            国家名,_ = 识别国家(号码)
            if 国家名: self.归属地标签.text = 国家名
            return
        if len(号码)==11 and 号码.startswith("1"):
            if self.离线解析器:
                try:
                    结果 = self.离线解析器.查询(号码)
                    if 结果:
                        省=结果.get("省份",""); 市=结果.get("城市",""); 运营商=结果.get("运营商","")
                        地点 = 市 if 省==市 else f"{省} {市}"
                        if 地点 and 运营商: self.归属地标签.text = f"{地点} · {运营商}"; return
                except Exception: pass
            self.归属地标签.text = f"{识别运营商(号码[:3])} · 查询中..."
            self.归属地查询定时器 = Clock.schedule_once(lambda dt: self.在线查询归属地(号码,0), 0.3)
            return
        if 号码.startswith("1") and len(号码)<11 and len(号码)>=3:
            self.归属地标签.text = 识别运营商(号码[:3]); return
        self.归属地标签.text = ""

    def 在线查询归属地(self, 号码, 接口序号):
        接口列表 = [f"https://cx.shouji.360.cn/phonearea.php?number={号码}", f"https://uapis.cn/api/v1/misc/phoneinfo?phone={号码}"]
        if 接口序号 >= len(接口列表): self.归属地标签.text = 识别运营商(号码[:3]); return
        自 = self
        def 成功(req, 结果):
            try:
                数据 = json.loads(结果) if isinstance(结果,str) else 结果
                省=数据.get("province") or ""; 市=数据.get("city") or ""; 运营商=数据.get("isp") or ""
                if not 省 and "data" in 数据:
                    d=数据["data"]; 省=d.get("province",""); 市=d.get("city",""); 运营商=d.get("sp","")
                if 省 or 市:
                    地点 = 市 if 省==市 else f"{省} {市}"
                    自.归属地标签.text = f"{地点} · {运营商 or 识别运营商(号码[:3])}"
                else: raise ValueError()
            except Exception: 自.在线查询归属地(号码, 接口序号+1)
        def 失败(req, error): 自.在线查询归属地(号码, 接口序号+1)
        UrlRequest(接口列表[接口序号], on_success=成功, on_error=失败, on_failure=失败, method="GET", timeout=4)

    def 执行拨打(self, instance):
        if not self.当前号码: self.提示弹窗("提示","请先输入电话号码"); return
        服务器 = self.配置.get("服务器地址","http://114cl6nq32524.vicp.fun").rstrip("/")
        目标号码 = self.当前号码
        if not 目标号码.startswith("+"): 目标号码 = "+86" + 目标号码.lstrip("0")
        self.拨打按钮.disabled = True; self.拨打按钮.text = "连接中..."
        自 = self
        def 成功(req, 结果):
            try:
                数据 = json.loads(结果) if isinstance(结果,str) else 结果
                if 数据.get("成功"):
                    自.当前呼叫ID = 数据["call_id"]
                    自.显示通话界面(目标号码)
                    自.开始状态轮询()
                else:
                    自.拨打按钮.disabled=False; self.拨打按钮.text="拨打"
                    自.提示弹窗("拨打失败", 数据.get("错误","未知错误"))
            except Exception as e:
                自.拨打按钮.disabled=False; self.拨打按钮.text="拨打"
                自.提示弹窗("错误", f"解析失败: {e}")
        def 失败(req, error):
            自.拨打按钮.disabled=False; self.拨打按钮.text="拨打"
            自.提示弹窗("连接失败", f"无法连接后台服务器: {服务器}\n\n请先启动 call_server.py\n或检查服务器地址配置")
        UrlRequest(f"{服务器}/api/call", on_success=成功, on_error=失败, on_failure=失败,
                   req_body=json.dumps({"号码":目标号码}), req_headers={"Content-Type":"application/json"}, method="POST")

    def 显示通话界面(self, 号码):
        归属地 = self.归属地标签.text
        self.通话界面 = 通话中界面(号码, 归属地, self.主动挂断)
        self.通话弹窗 = Popup(title="", content=self.通话界面, size_hint=(1,1), background_color=(0.1,0.1,0.12,1), separator_height=0, auto_dismiss=False)
        self.通话弹窗.open()

    def 开始状态轮询(self):
        self.状态轮询事件 = Clock.schedule_interval(self.查询呼叫状态, 0.5)

    def 停止状态轮询(self):
        if self.状态轮询事件: self.状态轮询事件.cancel(); self.状态轮询事件 = None

    def 查询呼叫状态(self, dt):
        if not self.当前呼叫ID: self.停止状态轮询(); return
        服务器 = self.配置.get("服务器地址","http://127.0.0.1:5000").rstrip("/")
        自 = self
        def 成功(req, 结果):
            try:
                数据 = json.loads(结果) if isinstance(结果,str) else 结果
                if not 数据.get("成功"): 自.停止状态轮询(); return
                状态 = 数据["状态"]; 状态文字 = 数据.get("状态文字",""); 结束原因 = 数据.get("结束原因")

                if 自.通话界面: 自.通话界面.更新状态(状态, 状态文字)

                # ringing时播放回铃音
                if 状态 == "ringing": 播放回铃音()
                elif 状态 != "ringing": 停止回铃音()

                if 状态 == "ended":
                    自.停止状态轮询()
                    自.当前呼叫ID = None
                    停止回铃音()
                    # 播放中英文语音提示（中文一遍+英文一遍）
                    if 结束原因 and 结束原因 in 语音提示库 and 自.配置.get("自动播报语音",True):
                        语音播报(结束原因)
                    # 等语音读完再关界面（中英文约8-10秒，给12秒）
                    Clock.schedule_once(lambda dt: 自.关闭通话界面(), 12)
                elif 状态 == "canceled":
                    自.停止状态轮询(); 自.当前呼叫ID = None; 停止回铃音()
                    Clock.schedule_once(lambda dt: 自.关闭通话界面(), 1.5)
            except Exception as e: print(f"状态查询异常: {e}")
        def 失败(req, error): pass
        UrlRequest(f"{服务器}/api/status/{self.当前呼叫ID}", on_success=成功, on_error=失败, on_failure=失败, method="GET", timeout=3)

    def 主动挂断(self):
        if not self.当前呼叫ID: self.关闭通话界面(); return
        服务器 = self.配置.get("服务器地址","http://114cl6nq32524.vicp.fun").rstrip("/")
        自 = self
        停止回铃音()
        def 成功(req, 结果):
            自.停止状态轮询(); 自.当前呼叫ID = None
            # 主动挂断只播短促挂断音，不播语音
            if 挂断音对象:
                try: 挂断音对象.play()
                except Exception: pass
            Clock.schedule_once(lambda dt: 自.关闭通话界面(), 1.2)
        def 失败(req, error): 自.关闭通话界面()
        UrlRequest(f"{服务器}/api/hangup/{self.当前呼叫ID}", on_success=成功, on_error=失败, on_failure=失败, method="POST", timeout=3)

    def 关闭通话界面(self):
        if self.通话弹窗: self.通话弹窗.dismiss(); self.通话弹窗 = None
        self.拨打按钮.disabled = False; self.拨打按钮.text = "拨打"
        self.当前号码 = ""; self.更新号码显示(); self.归属地标签.text = ""

    def 打开设置弹窗(self, instance):
        内容 = BoxLayout(orientation="vertical", spacing=10, padding=15)
        配置 = self.配置
        self.输入服务器 = TextInput(text=配置.get("服务器地址","http://127.0.0.1:5000"), hint_text="后台服务器地址", multiline=False, size_hint_y=None, height=45)
        内容.add_widget(Label(text="虚拟电话配置", font_size=18, size_hint_y=None, height=28))
        内容.add_widget(self.输入服务器)
        说明 = Label(text="[size=13][color=#888888]使用步骤：\n1. 启动后台：python call_server.py\n2. 浏览器打开 http://127.0.0.1:5000 配置参数\n3. APP拨号后自动模拟呼叫\n4. 响铃到点自动挂断并播报语音[/color][/size]", markup=True, size_hint_y=None, height=140, halign="left")
        内容.add_widget(说明)
        保存按钮 = Button(text="保存", size_hint_y=None, height=48, background_normal="", background_color=(0.18,0.72,0.38,1))
        内容.add_widget(保存按钮)
        self.设置弹窗 = Popup(title="设置", content=内容, size_hint=(0.9,0.65))
        保存按钮.bind(on_press=self.保存设置)
        self.设置弹窗.open()

    def 保存设置(self, instance):
        self.配置["服务器地址"] = self.输入服务器.text.strip().rstrip("/")
        保存配置(self.配置)
        self.设置弹窗.dismiss()
        self.提示弹窗("已保存", f"服务器地址：{self.配置['服务器地址']}")

    def 提示弹窗(self, 标题, 内容文字):
        内容 = BoxLayout(orientation="vertical", padding=15, spacing=12)
        内容.add_widget(Label(text=内容文字, font_size=15, halign="center"))
        关闭按钮 = Button(text="知道了", size_hint_y=None, height=44, background_normal="", background_color=(0.18,0.72,0.38,1))
        内容.add_widget(关闭按钮)
        弹窗 = Popup(title=标题, content=内容, size_hint=(0.8,0.45))
        关闭按钮.bind(on_press=弹窗.dismiss)
        弹窗.open()


class 虚拟电话App(App):
    def build(self):
        Window.clearcolor = (1,1,1,1)
        初始化音频()
        return 拨号主界面()


if __name__ == "__main__":
    虚拟电话App().run()
