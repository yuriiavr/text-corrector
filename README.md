# AI Fixer: Low-Level System Text Processor

A high-performance Windows utility built with **Python 3.10+** and **PyQt6** that leverages **Google Gemini 2.0/3.1** models for real-time text transformation via global hotkeys.

## 🛠 Technical Architecture
- **Input Interception:** Uses `keyboard` for global hook listeners and `ctypes` (Win32 API) for low-level event injection.
- **Buffer Management:** Implements `pyperclip` for clipboard I/O with automated buffer clearing to prevent race conditions.
- **Process Injection:** Utilizes `user32.keybd_event` to bypass high-level driver interference (e.g., multimedia key conflicts like Volume +/-).
- **Asynchronous Execution:** All API calls are handled in `threading.Thread` (daemon mode) to ensure the UI remains responsive during network latency.
- **Persistence:** Configuration management via `QSettings` (Registry-based on Windows) and `winreg` for HKCU Run-key autostart integration.

## 🚀 Key Features
* **Zero-UI Workflow:** Process text directly in any active window without switching context.
* **Low-Level Simulation:** Virtual key-code injection (`VK_CONTROL`, `VK_C`, `VK_V`) ensures compatibility with sandboxed applications.
* **Prompt Engineering:** Specialized system instructions for three distinct modes: `Grammar Fix`, `Professional Rewrite`, and `EN Translation`.
* **Dynamic Model Switching:** Support for `gemini-2.5-flash`, `gemini-2.5-flash-lite`, and `gemini-3.1-flash-lite-preview`.

## 📦 Installation & Build
1. Install dependencies: `pip install PyQt6 google-genai keyboard pyperclip`
2. Build executable:
   ```bash
   pyinstaller --noconsole --onefile --icon=icon.ico main.py