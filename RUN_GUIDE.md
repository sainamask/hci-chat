# Run the study chatbot and share it with participants (Mac)

Your Mac is the server. Participants open a link from any device; the model
runs on your GPU. Your Mac must be ON and online while people are doing sessions.

## 0. One-time setup

1. Ollama is already installed on this Mac. Make sure it's running:
   - Open the Ollama app (menu-bar icon), OR in Terminal run: `ollama serve`
   - Pull a model (once):  `ollama pull llama3.1:8b`
     (Bigger model = warmer replies but more VRAM. Edit MODEL in app.py to match.)
2. Install the Python packages. In Terminal:
   ```
   cd ~/Documents/"hci chatbot"
   pip3 install -r requirements.txt
   ```

## 1. Set your codes (do this before sharing)

Open `app.py` and change these two lines near the top:
```
STUDY_CODE = "dreamteam2026"   # the shared code every participant types
RESEARCHER_KEY = "letmein"     # secret for opening the researcher panel
```

## 2. Start the app

```
cd ~/Documents/"hci chatbot"
streamlit run app.py
```
It opens at http://localhost:8501 on your Mac.

## 3. Make it reachable from anywhere (tunnel)

In a SECOND Terminal window, run ONE of these:

- Cloudflare (free, no signup):
  ```
  brew install cloudflared
  cloudflared tunnel --url http://localhost:8501
  ```
- or ngrok (free account):
  ```
  brew install ngrok
  ngrok http 8501
  ```

Either prints a public https link (e.g. https://xxxx.trycloudflare.com).
That link is what you send to participants.

## 4. What you send participants

- The link (above)
- The study code (STUDY_CODE)
- Their personal participant ID (P001, P002, ...)

They open the link -> type the study code + their ID -> chat.
The ID silently assigns them to one of the 4 conditions.

## 5. You, the researcher

- To open the control panel (see conditions, force a session while piloting):
  add `?researcher=letmein` to the link, e.g.
  `https://xxxx.trycloudflare.com/?researcher=letmein`
  Participants who don't have this never see it.
- Data lands in `~/Documents/hci chatbot/data/logs/` as CSV files.

## 6. Daily reality check
- Keep the Mac awake during collection (System Settings > Lock Screen /
  Energy: never sleep, or run during set hours and tell participants the window).
- The tunnel link can change each time you restart cloudflared; re-send if so
  (ngrok paid / cloudflare named tunnels give a fixed URL if you want permanence).
