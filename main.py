import os
import sys
import threading
import time
import keyboard
import pyperclip
import winreg
from google import genai
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon, QAction, QKeyEvent, QKeySequence

PROMPTS = {
    "fix": "Fix grammar and punctuation. Return ONLY the corrected text.",
    "pro": "Rewrite this text to be professional, polite, and formal for business communication. Return ONLY the text.",
    "translate": "Translate this text to English, ensuring natural flow and correct grammar. Return ONLY the translation.",
}

class HotkeyLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background: #2d2d2d; 
            border: 2px solid #3e3e42; 
            color: #0078d4; 
            font-weight: bold;
            text-transform: uppercase;
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

    def init_ui(self):
        self.setWindowTitle("AI Fixer Settings")
        self.setFixedSize(350, 550)
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
        self.model_options = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite-preview"]
        self.model_select.addItems(self.model_options)
        self.model_select.setCurrentText(self.settings.value("model", "gemini-2.5-flash"))
        layout.addWidget(self.model_select)

        layout.addWidget(QLabel("HOTKEY"))
        self.hotkey_input = HotkeyLineEdit()
        self.hotkey_input.setText(self.settings.value("hotkey", "alt+shift+g"))
        layout.addWidget(self.hotkey_input)
        
        layout.addWidget(QLabel("AI MODE"))
        self.mode_select = QComboBox()
        self.mode_select.addItems(["fix", "pro", "translate"])
        self.mode_select.setCurrentText(self.settings.value("mode", "fix"))
        layout.addWidget(self.mode_select)
        
        self.autolaunch_cb = QCheckBox("Launch on startup")
        self.autolaunch_cb.setChecked(self.settings.value("autolaunch", False, type=bool))
        layout.addWidget(self.autolaunch_cb)
        
        save_btn = QPushButton("SAVE SETTINGS")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def set_autostart(self, state):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "AIFixer"
        exe_path = f'"{os.path.realpath(sys.argv[0])}"'
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if state:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except:
            pass

    def setup_ai(self):
        api_key = self.settings.value("apiKey")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def setup_hotkey(self):
        keyboard.unhook_all()
        hk = self.settings.value("hotkey", "alt+shift+g")
        try:
            keyboard.add_hotkey(hk, self.trigger_fix)
        except:
            pass

    def save_settings(self):
        self.settings.setValue("apiKey", self.key_input.text())
        self.settings.setValue("model", self.model_select.currentText())
        self.settings.setValue("hotkey", self.hotkey_input.text())
        self.settings.setValue("mode", self.mode_select.currentText())
        self.settings.setValue("autolaunch", self.autolaunch_cb.isChecked())
        
        self.set_autostart(self.autolaunch_cb.isChecked())
        self.setup_ai()
        self.setup_hotkey()
        self.hide()

    def trigger_fix(self):
        threading.Thread(target=self.fix_text, daemon=True).start()

    def fix_text(self):
        if self.is_processing or not self.client:
            return

        self.is_processing = True
        
        try:
            time.sleep(0.4) 
            pyperclip.copy("") 
            
            keyboard.press('ctrl')
            keyboard.press('c')
            time.sleep(0.1)
            keyboard.release('c')
            keyboard.release('ctrl')
            
            time.sleep(0.5) 
            original_text = pyperclip.paste()
            
            if not original_text.strip():
                keyboard.press_and_release('ctrl+c')
                time.sleep(0.5)
                original_text = pyperclip.paste()
                if not original_text.strip():
                    return

            mode = self.settings.value("mode", "fix")
            active_model = self.settings.value("model", "gemini-2.5-flash")
            
            response = self.client.models.generate_content(
                model=active_model,
                contents=f"{PROMPTS[mode]}\n\nText: {original_text}"
            )
            
            fixed = response.text
            if fixed:
                pyperclip.copy(fixed.strip())
                time.sleep(0.2)
                keyboard.press_and_release('ctrl+v')

        except:
            pass
        finally:
            self.is_processing = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = AIFixerApp()
    
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        tray_icon = QIcon(icon_path)
    else:
        tray_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        
    tray = QSystemTrayIcon(tray_icon, win)
    menu = QMenu()
    
    settings_action = QAction("⚙️ Settings", win)
    settings_action.triggered.connect(win.show)
    
    quit_action = QAction("Exit", win)
    quit_action.triggered.connect(app.quit)
    
    menu.addAction(settings_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    
    tray.setContextMenu(menu)
    tray.show()
    
    if not win.settings.value("apiKey"): 
        win.show()
        
    sys.exit(app.exec())