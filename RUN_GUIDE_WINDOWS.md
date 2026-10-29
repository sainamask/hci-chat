# Run the study chatbot on Windows and share it with participants

Your Windows PC is the server. Participants open a link from any device; the
model runs on your GPU. Your PC must be ON and online while people do sessions.

## 0. One-time setup

1. Install Ollama for Windows: https://ollama.com/download
   After install it runs in the background (system tray). 
2. Open PowerShell (or Command Prompt) and pull a model:
   ```
   ollama pull llama3.1:8b
   ```
   Bigger = warmer replies but more VRAM (NVIDIA). Rough 4-bit guide:
   llama3.1:8b ~6 GB · qwen2.5:14b ~10 GB · gemma2:27b ~18 GB · llama3.1:70b ~40 GB.
   Change the MODEL line at the top of app.py to whatever you pulled.
3. Install Python 3 from python.org if you don't have it (tick "Add to PATH").
4. Install the packages. In PowerShell, inside the project folder:
   ```
   cd "C:\path\to\hci chatbot"
   python -m pip install -r requirements.txt
   ```

## 1. Set your codes (before sharing)

Open app.py and change these two lines near the top:
```
STUDY_CODE = "dreamteam2026"   # the shared code every participant types
RESEARCHER_KEY = "letmein"     # secret for the researcher panel
```

## 2. Start the app

```
cd "C:\path\to\hci chatbot"
python -m streamlit run app.py
```
It opens at http://localhost:8501

## 3. Make it reachable from anywhere (tunnel)

In a SECOND PowerShell window, run ONE of these:

- Cloudflare (free, no signup):
  ```
  winget install --id Cloudflare.cloudflared
  cloudflared tunnel --url http://localhost:8501
  ```
- or ngrok (free account at ngrok.com):
  ```
  winget install --id ngrok.ngrok
  ngrok http 8501
  ```

It prints a public https link (e.g. https://xxxx.trycloudflare.com).
Send THAT link to participants.

## 4. What you send participants
- The link (above)
- The study code (STUDY_CODE)
- Their personal participant ID (P001, P002, ...)

They open the link -> type the study code + their ID -> chat.
The ID silently assigns them to one of the 4 conditions.

## 5. You, the researcher
- Open the control panel by adding ?researcher=letmein to the link:
  https://xxxx.trycloudflare.com/?researcher=letmein
  Participants without this never see it.
- Data lands in the data\logs\ folder as CSV files.

## 6. Keep it running
- Keep the PC awake during collection (Settings > System > Power: never sleep),
  or run during set hours and tell participants the window.
- A free cloudflared/ngrok link can change when you restart it; re-send if so.
