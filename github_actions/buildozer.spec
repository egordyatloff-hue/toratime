[app]
title = Планировщик заданий
package.name = toratime
package.domain = org.example
source.dir = .
source.include_exts = py,json
source.exclude_dirs = tests, .venv
version = 0.1
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.permissions = POST_NOTIFICATIONS,SCHEDULE_EXACT_ALARM,RECEIVE_BOOT_COMPLETED
android.add_src = java
p4a.hook = ./p4a_hook.py
android.api = 33
android.minapi = 21
android.ndk = 28c
android.build_tools = 33.0.1
android.archs = arm64-v8a
android.allow_backup = True
android.private_storage = True

[buildozer]
log_level = 2
warn_on_root = 0
