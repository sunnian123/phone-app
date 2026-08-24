[app]
title = 电话
package.name = virtualphone
package.domain = org.virtualphone

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,dat,ttc,ttf,wav,mp3
source.include_patterns = icon.png,phone.dat,phone_parser.py,audio_gen.py,msyh.ttc,ringback.wav,busy.wav,hangup.wav,voice_*.wav

version = 1.0

requirements = python3,kivy==2.3.0

# 安卓权限：网络（连接后台服务器）
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# 竖屏
android.orientation = portrait

# 最低安卓版本
android.minapi = 21
android.api = 34
android.buildtools = 34.0.0
android.ndk = 25b

# 应用图标
icon.filename = icon.png

# 启动画面（可选）
# presplash.filename = presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
