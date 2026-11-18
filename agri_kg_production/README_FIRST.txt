AGRICULTURAL KNOWLEDGE GRAPH EXTRACTION — OPENROUTER PACKAGE

This is the updated OpenRouter version, not the older Ollama ZIP you originally uploaded.
Model: openai/gpt-oss-120b (provisional selection from the existing benchmark).
There is no fixed maximum number of triples per passage.

WHAT THIS VERSION FIXES
1. Checks chunk length before sending; starts around 4,000 characters.
2. Splits at paragraph/line boundaries; long table segments retain their header and rows are not sliced mid-row.
3. If the model still reaches its output limit, it recursively splits that passage and retries the smaller pieces. Truncated JSON is never saved as complete.
4. Does not spend a second request just to resend the same passage with a bigger output budget after truncation.
5. Evidence must be one continuous source excerpt. Unicode punctuation/whitespace is normalized, but fuzzy paraphrase matching is not allowed.
6. Saves both accepted triples and rejected model outputs/reasons for later inspection.
7. Uses SQLite checkpoints and resumes pending/failed work after interruption.
8. Counts every API attempt before sending it. The previous benchmark log ended at 83 attempts on 2026-10-26; the new ledger carries that count forward for that UTC date.

STEP 1 — EXTRACT THIS ZIP
Extract the folder agri_kg_production to:
C:\AgriKG\agri_kg_production

STEP 2 — OPEN POWERSHELL IN THE FOLDER
Open that folder in File Explorer, click the address bar, type powershell, press Enter.

STEP 3 — CREATE THE ENVIRONMENT (run one line at a time)
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

If activation is blocked, run this once, then activate again:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

STEP 4 — SET THE OPENROUTER KEY
Run this in the same PowerShell window (replace YOUR_KEY; never send me the key):
$env:OPENROUTER_API_KEY="YOUR_KEY"

STEP 5 — RUN THE FREE PREFLIGHT CHECK
python preflight.py
This sends ZERO API requests. It checks that the JSON file exists and reports original chunks, prepared work items, and maximum chunk length.
If it says INPUT NOT FOUND, STOP and paste that exact error here. Do not start extraction.

STEP 6 — START THE REAL EXTRACTION
python extractor.py
Do not run benchmark.py again. Do not open a second extractor window.

STEP 7 — IF YOU NEED TO STOP
Press Ctrl+C once and wait for the program to exit. Later, reopen PowerShell in the same folder, activate the environment, set the API key again, then run:
python extractor.py
Do not delete the output folder or database.

STEP 8 — OUTPUTS
The output folder is created automatically:
output\kg_extraction_openrouter_final.db  (database/checkpoints)
output\triples.json
output\triples.jsonl
output\triples.csv
output\rejected_triples.json
output\chunk_status.json
output\extraction_stats.json
output\extraction.log
To refresh exports without making API calls:
python export_data.py

IMPORTANT
- The 850/day setting is a local ceiling, not a guarantee that OpenRouter will allow 850 requests. Provider rate limits and available credits still apply.
- If HTTP 429 or insufficient credits occurs, the process pauses safely; resume later with python extractor.py.
- Extraction can take multiple days because the local ceiling is 850 API attempts/day and the dataset has roughly 2,200 source chunks. The actual work-item count appears in preflight.
- Evidence matching confirms that a quotation occurs in the source; it does NOT prove logical entailment. Review rejected records and evaluate a gold sample before claiming final KG quality.
