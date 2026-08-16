# -*- coding: utf-8 -*-
import os


def after_apk_build(toolchain_cl):
    manifest = os.path.join(toolchain_cl.build_dir, "src", "main", "AndroidManifest.xml")
    if not os.path.exists(manifest):
        return
    with open(manifest, "r", encoding="utf-8") as f:
        text = f.read()
    if "org.example.toratime.AlarmReceiver" in text:
        return
    receiver = (
        '<receiver android:name="org.example.toratime.AlarmReceiver" '
        'android:enabled="true" android:exported="false">\n'
        '        <intent-filter>\n'
        '            <action android:name="org.example.toratime.ALARM"/>\n'
        '        </intent-filter>\n'
        '        <intent-filter>\n'
        '            <action android:name="android.intent.action.BOOT_COMPLETED"/>\n'
        '        </intent-filter>\n'
        '    </receiver>'
    )
    idx = text.rfind("</application>")
    if idx == -1:
        return
    text = text[:idx] + "    " + receiver + "\n" + text[idx:]
    with open(manifest, "w", encoding="utf-8") as f:
        f.write(text)
    print("AlarmReceiver injected into AndroidManifest.xml")
