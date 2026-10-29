# Reassure or Guide? - study chatbot (local, Ollama)

A single Streamlit app that runs all four conditions of the 2x2
(support style x memory) study on your own machine. Participant data
stays local. No API keys.

## What it does
- Participant logs in with an ID -> app looks up (or block-randomizes) their condition.
- Days 1-3: a pre-mood survey, a chat with their assigned bot (>= 5 min), a post-mood survey.
- Day 4: the no-AI transfer task, then the final questionnaires.
- Everything is logged to CSV files under `data/logs/`.

The 2x2 is produced by ONE app:
- **Style** = which system prompt loads (Reassure vs Guide) - see `prompts.py`.
- **Memory** = whether earlier transcripts are fed back into the prompt (Persistent) or not (Fresh).
The model, opening message, and reply cap are identical across all conditions (your controlled variables).

## Setup (one time)

1. Install Ollama: https://ollama.com/download
2. Pull a model:
   ```
   ollama pull llama3.1:8b
   ```
   Bigger = warmer/smarter but needs more VRAM. Rough guide (4-bit):
   - `llama3.1:8b` ~ 6 GB VRAM (safe default)
   - `qwen2.5:14b` ~ 10 GB
   - `gemma2:27b` ~ 18 GB
   - `llama3.1:70b` ~ 40 GB (only on a very large GPU)
   Change the `MODEL` line at the top of `app.py` to match what you pulled.
3. Install Python deps:
   ```
   pip install -r requirements.txt
   ```

## Run

1. Make sure Ollama is running (it starts on install; `ollama serve` if not).
2. Start the app:
   ```
   streamlit run app.py
   ```
3. It opens in your browser. Participants enter their ID and go.

## Assigning participants
- Easiest: just hand out IDs (P001, P002, ...). The first time an unknown ID logs in,
  the app block-randomizes it to a condition and saves it to `data/participants.csv`.
  Blocks of four keep the cells balanced (5 each for N=20).
- Or pre-assign: copy `data/participants_template.csv` to `data/participants.csv`
  and fill in `style` (reassure/guide) and `memory` (persistent/fresh) yourself.

## The data you get (under data/logs/)
- `<ID>_messages.csv` - every message, with timestamps (your transcripts + usage).
- `<ID>_sessions.csv` - per day: duration, distress pre/post, I-PANAS-SF pre/post.
- `<ID>_final.csv` - Day-4 written answer + all final 7-point scales + manipulation checks.

## Scoring (after collection)
Two raters open each `<ID>_final.csv`, read `day4_answer`, and score it 0-3
on the rubric (multiple explanations? concrete next step? no catastrophizing?),
blind to the `style`/`memory` columns. Then compute Cohen's kappa for agreement.

## Notes
- The sidebar "Researcher panel" lets you force a chat day or the Day-4 test while piloting.
  Hide or ignore it during real runs.
- A simple crisis-word check shows support resources and stops the chat if someone
  mentions self-harm. Edit the list and resources in `prompts.py` / `app.py`.
- One real session per calendar day per participant is enforced by date.
"# hci-chat" 
