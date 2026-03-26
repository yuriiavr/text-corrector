const {
  app,
  globalShortcut,
  clipboard,
  Notification,
  Menu,
  Tray,
  BrowserWindow,
  ipcMain,
} = require("electron");
const { exec } = require("child_process");
const path = require("path");

const ElectronStore = require("electron-store");
const store = new (ElectronStore.default || ElectronStore)();

let client;
let tray = null;
let settingsWindow = null;
let isProcessing = false;
let isQuitting = false;

const prompts = {
  fix: "Fix grammar and punctuation. Return ONLY the corrected text.",
  pro: "Rewrite this text to be professional, polite, and formal for business communication. Return ONLY the text.",
  translate:
    "Translate this text to English, ensuring natural flow and correct grammar. Return ONLY the translation.",
};

async function initAI() {
  const apiKey = store.get("apiKey");
  if (!apiKey) return false;
  try {
    const genaiModule = await import("@google/genai");
    const GAI = genaiModule.GoogleGenAI || genaiModule.default?.GoogleGenAI;
    client = new GAI({ apiKey: apiKey });
    return true;
  } catch (err) {
    return false;
  }
}

function createSettingsWindow() {
  if (settingsWindow) {
    settingsWindow.show();
    return;
  }

  settingsWindow = new BrowserWindow({
    width: 400,
    height: 550,
    title: "AI Fixer Settings",
    resizable: false,
    autoHideMenuBar: true,
    backgroundColor: "#1e1e1e",
    webPreferences: { nodeIntegration: true, contextIsolation: false },
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });


  settingsWindow.setIcon(path.join(__dirname, 'icon.png'));

  settingsWindow.on("close", (e) => {
    if (!isQuitting) {
      e.preventDefault();
      settingsWindow.hide();
    }
  });

  const currentMode = store.get("mode") || "fix";

  const html = `
    <html>
    <head>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 30px;
                background: #121212;
                color: #e0e0e0;
                margin: 0;
                overflow: hidden;
            }
            h2 {
                font-weight: 600;
                margin-bottom: 25px;
                color: #ffffff;
                text-align: center;
                letter-spacing: 0.5px;
            }
            .field-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-size: 13px;
                color: #aaaaaa;
                font-weight: 500;
            }
            input[type="password"], input[type="text"], select {
                width: 100%;
                padding: 12px;
                background: #252526;
                border: 1px solid #333;
                border-radius: 8px;
                color: #fff;
                font-size: 14px;
                box-sizing: border-box;
                outline: none;
                transition: border-color 0.2s;
            }
            input:focus, select:focus {
                border-color: #0078d4;
            }
            #hotkey {
                cursor: pointer;
                background: #2d2d2d;
                border: 2px solid #3e3e42;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .checkbox-group {
                display: flex;
                align-items: center;
                gap: 10px;
                margin: 25px 0;
                cursor: pointer;
                font-size: 14px;
            }
            input[type="checkbox"] {
                width: 18px;
                height: 18px;
                accent-color: #0078d4;
            }
            button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #0078d4, #005a9e);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.1s, opacity 0.2s;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }
            button:hover {
                opacity: 0.9;
            }
            button:active {
                transform: scale(0.98);
            }
            .footer {
                margin-top: 20px;
                text-align: center;
                font-size: 11px;
                color: #555;
            }
        </style>
    </head>
    <body>
        <h2>AI Fixer</h2>
        
        <div class="field-group">
            <label>GEMINI API KEY</label>
            <input id="key" type="password" placeholder="••••••••••••••••" value="${store.get("apiKey") || ""}">
        </div>

        <div class="field-group">
            <label>HOTKEY</label>
            <input id="hotkey" type="text" readonly value="${store.get("hotkey") || "Alt+Shift+G"}">
        </div>

        <div class="field-group">
            <label>AI MODE</label>
            <select id="mode">
                <option value="fix" ${currentMode === "fix" ? "selected" : ""}>Standard Fix</option>
                <option value="pro" ${currentMode === "pro" ? "selected" : ""}>Professional Tone</option>
                <option value="translate" ${currentMode === "translate" ? "selected" : ""}>Translate to English</option>
            </select>
        </div>

        <label class="checkbox-group">
            <input type="checkbox" id="autolaunch" ${store.get("autolaunch") ? "checked" : ""}>
            Launch on startup
        </label>

        <button onclick="save()">Save Settings</button>

        <div class="footer">v1.2 | Active & Running</div>

        <script>
            const { ipcRenderer } = require('electron');
            const hotkeyInput = document.getElementById('hotkey');

            hotkeyInput.addEventListener('keydown', (e) => {
                e.preventDefault();
                const keys = [];
                if (e.ctrlKey) keys.push('Ctrl');
                if (e.shiftKey) keys.push('Shift');
                if (e.altKey) keys.push('Alt');
                if (e.metaKey) keys.push('Cmd');
                if (!['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) keys.push(e.key.toUpperCase());
                if (keys.length > 0) hotkeyInput.value = keys.join('+');
            });

            function save() {
                ipcRenderer.send('save-settings', {
                    apiKey: document.getElementById('key').value,
                    hotkey: hotkeyInput.value,
                    mode: document.getElementById('mode').value,
                    autolaunch: document.getElementById('autolaunch').checked
                });
            }
        </script>
    </body>
    </html>
`;
  settingsWindow.loadURL(
    `data:text/html;charset=utf-8,${encodeURIComponent(html)}`,
  );
}

ipcMain.on("save-settings", (event, data) => {
  store.set("apiKey", data.apiKey);
  store.set("hotkey", data.hotkey);
  store.set("mode", data.mode);
  store.set("autolaunch", data.autolaunch);

  app.setLoginItemSettings({
    openAtLogin: data.autolaunch,
    path: app.getPath("exe"),
  });
  isQuitting = true;
  app.relaunch();
  app.exit();
});

async function fixSelectedText() {
  if (isProcessing) return;

  if (!client) {
    new Notification({
      title: "AI Fixer: Missing API Key",
      body: "Please open Settings and enter your Gemini API Key.",
    }).show();
    createSettingsWindow();
    return;
  }

  isProcessing = true;
  try {
    exec(
      `powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^c')"`,
    );
    await new Promise((r) => setTimeout(r, 350));

    const selectedText = clipboard.readText();
    if (!selectedText || !selectedText.trim()) {
      isProcessing = false;
      return;
    }

    const currentMode = store.get("mode") || "fix";
    const systemPrompt = prompts[currentMode];

    const result = await client.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: `${systemPrompt}\n\nText: ${selectedText}`,
    });

    const fixedText = result.text || result.value?.text();

    if (fixedText) {
      clipboard.writeText(fixedText.trim());
      exec(
        `powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')"`,
      );
    }
  } catch (e) {
    console.error(e);
    new Notification({
      title: "AI Fixer: Error",
      body: "An error occurred while processing text. Check your key or connection.",
    }).show();
  } finally {
    isProcessing = false;
  }
}

app.whenReady().then(async () => {
  await initAI();
  const userHotkey = store.get("hotkey") || "Alt+Shift+G";

  globalShortcut.register(userHotkey, fixSelectedText);

  try {
    tray = new Tray(path.join(__dirname, "icon.png"));

    const contextMenu = Menu.buildFromTemplate([
      {
        label: "✨ Fix Selected Text",
        click: fixSelectedText,
      },
      {
        label: "⚙️ Settings",
        click: createSettingsWindow,
      },
      { type: "separator" },
      {
        label: "Quit",
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);
    tray.setToolTip("AI Fixer");
    tray.on("double-click", createSettingsWindow);
  } catch (e) {
    console.log("[Tray Error]: Icon not found or failed to load");
  }

  console.log(`[Ready]: App is running. Shortcut: ${userHotkey}`);
});
app.on("window-all-closed", (e) => e.preventDefault());
