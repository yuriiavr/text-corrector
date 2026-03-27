import os
import sys
import threading
import time
import keyboard
import pyperclip
import winreg
import ctypes
from google import genai
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon, QAction, QKeyEvent, QKeySequence

user32 = ctypes.WinDLL('user32', use_last_error=True)
VK_CONTROL = 0x11
VK_C = 0x43
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002

def send_key_event(vk, up=False):
    flags = KEYEVENTF_KEYUP if up else 0
    user32.keybd_event(vk, 0, flags, 0)

PROMPTS = {
    "fix": "Fix grammar and punctuation. Return ONLY the corrected text.",
    "polite": "Rewrite this text to be professional, polite, and formal for business communication. Return ONLY the text.",
    "translate": "Translate this text to English, ensuring natural flow and correct grammar. Return ONLY the translation.",
}

class HotkeyLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background: #2d2d2d; border: 2px solid #3e3e42; color: #0078d4; 
            font-weight: bold; text-transform: uppercase;
        """)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
            return
        modifiers = event.modifiers()
        sequence = []
        if modifiers & Qt.KeyboardModifier.ControlModifier: sequence.append("ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier: sequence.append("shift")
        if modifiers & Qt.KeyboardModifier.AltModifier: sequence.append("alt")
        key_text = QKeySequence(key).toString().lower()
        if key_text:
            sequence.append(key_text)
            self.setText("+".join(sequence))

class AIFixerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("AI_Fixer_Company", "AI_Fixer_App")
        self.is_processing = False
        self.client = None
        self.init_ui()
        self.setup_ai()
        self.setup_hotkey()

    def get_app_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)

    def init_ui(self):
        self.setWindowTitle("AI Fixer Settings")
        self.setWindowIcon(self.get_app_icon())
        self.setFixedSize(350, 600)
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI'; }
            QLabel { color: #aaaaaa; font-size: 11px; font-weight: bold; margin-top: 10px; }
            QLineEdit, QComboBox { 
                background: #252526; border: 1px solid #333; border-radius: 6px; 
                padding: 8px; color: white; 
            }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d4, stop:1 #005a9e);
                border: none; border-radius: 6px; padding: 12px; color: white; font-weight: bold; margin-top: 20px;
            }
            QPushButton:hover { background: #0086f0; }
        """)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("GEMINI API KEY"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setText(self.settings.value("apiKey", ""))
        layout.addWidget(self.key_input)
        
        layout.addWidget(QLabel("AI MODEL"))
        self.model_select = QComboBox()
        self.model_select.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite-preview"])
        self.model_select.setCurrentText(self.settings.value("model", "gemini-2.5-flash"))
        layout.addWidget(self.model_select)

        layout.addWidget(QLabel("HOTKEY"))
        self.hotkey_input = HotkeyLineEdit()
        self.hotkey_input.setText(self.settings.value("hotkey", "alt+shift+g"))
        layout.addWidget(self.hotkey_input)
        
        layout.addWidget(QLabel("AI MODE"))
        self.mode_select = QComboBox()
        self.mode_select.addItems(["fix", "polite", "translate", "custom"])
        current_mode = self.settings.value("mode", "fix")
        self.mode_select.setCurrentText(current_mode)
        self.mode_select.currentTextChanged.connect(self.toggle_custom_input)
        layout.addWidget(self.mode_select)
        
        self.custom_label = QLabel("CUSTOM PROMPT")
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("e.g. Summarize this text...")
        self.custom_input.setText(self.settings.value("custom_prompt", ""))
        layout.addWidget(self.custom_label)
        layout.addWidget(self.custom_input)
        
        self.toggle_custom_input(current_mode)

        self.autolaunch_cb = QCheckBox("Launch on startup")
        self.autolaunch_cb.setChecked(self.settings.value("autolaunch", False, type=bool))
        layout.addWidget(self.autolaunch_cb)
        
        save_btn = QPushButton("SAVE SETTINGS")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def toggle_custom_input(self, mode):
        is_custom = (mode == "custom")
        self.custom_label.setVisible(is_custom)
        self.custom_input.setVisible(is_custom)

    def set_autostart(self, state):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = f'"{os.path.realpath(sys.argv[0])}"'
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if state: winreg.SetValueEx(key, "AIFixer", 0, winreg.REG_SZ, exe_path)
            else:
                try: winreg.DeleteValue(key, "AIFixer")
                except FileNotFoundError: pass
            winreg.CloseKey(key)
        except: pass

    def setup_ai(self):
        api_key = self.settings.value("apiKey")
        if api_key: self.client = genai.Client(api_key=api_key)

    def setup_hotkey(self):
        keyboard.unhook_all()
        hk = self.settings.value("hotkey", "alt+shift+g")
        try: keyboard.add_hotkey(hk, self.trigger_fix)
        except: pass

    def save_settings(self):
        self.settings.setValue("apiKey", self.key_input.text())
        self.settings.setValue("model", self.model_select.currentText())
        self.settings.setValue("hotkey", self.hotkey_input.text())
        self.settings.setValue("mode", self.mode_select.currentText())
        self.settings.setValue("custom_prompt", self.custom_input.text())
        self.settings.setValue("autolaunch", self.autolaunch_cb.isChecked())
        self.set_autostart(self.autolaunch_cb.isChecked())
        self.setup_ai()
        self.setup_hotkey()
        self.hide()

    def trigger_fix(self):
        threading.Thread(target=self.fix_text, daemon=True).start()

    def fix_text(self):
        if self.is_processing or not self.client: return
        self.is_processing = True
        try:
            time.sleep(0.5)
            pyperclip.copy("")
            
            send_key_event(VK_CONTROL, False)
            send_key_event(VK_C, False)
            time.sleep(0.1)
            send_key_event(VK_C, True)
            send_key_event(VK_CONTROL, True)
            
            original_text = ""
            for _ in range(15):
                time.sleep(0.1)
                original_text = pyperclip.paste()
                if original_text.strip(): break
            
            if not original_text.strip():
                self.is_processing = False
                return

            mode = self.settings.value("mode", "fix")
            if mode == "custom":
                instructions = self.settings.value("custom_prompt", "Return only corrected text.")
            else:
                instructions = PROMPTS.get(mode, PROMPTS["fix"])

            response = self.client.models.generate_content(
                model=self.settings.value("model", "gemini-2.5-flash"),
                contents=f"{instructions}\n\nText: {original_text}"
            )
            
            if response.text:
                pyperclip.copy(response.text.strip())
                time.sleep(0.2)
                send_key_event(VK_CONTROL, False)
                send_key_event(VK_V, False)
                time.sleep(0.1)
                send_key_event(VK_V, True)
                send_key_event(VK_CONTROL, True)
        except: pass
        finally: self.is_processing = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = AIFixerApp()
    
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    
    if os.path.exists(icon_path):
        tray_icon = QIcon(icon_path)
    else:
        tray_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        
    tray = QSystemTrayIcon(tray_icon, win)
    menu = QMenu()
    s_act = QAction("⚙️ Settings", win)
    s_act.triggered.connect(win.show)
    q_act = QAction("Exit", win)
    q_act.triggered.connect(app.quit)
    menu.addAction(s_act)
    menu.addSeparator()
    menu.addAction(q_act)
    tray.setContextMenu(menu)
    tray.show()
    
    if not win.settings.value("apiKey"): win.show()
    sys.exit(app.exec())