import json
import config
from extractor import load_input_chunks, prepare_work_items

if __name__ == "__main__":
    if not config.INPUT_JSON.exists():
        raise SystemExit(f"INPUT NOT FOUND: {config.INPUT_JSON}\nSet AGRI_INPUT_JSON or edit config.py.")
    chunks=load_input_chunks(config.INPUT_JSON)
    work=prepare_work_items(chunks)
    lengths=[len(x["page_content"]) for x in work]
    print("PREFLIGHT ONLY — no OpenRouter requests will be sent")
    print(f"Input file: {config.INPUT_JSON}")
    print(f"Original chunks: {len(chunks)}")
    print(f"Prepared work items: {len(work)}")
    print(f"Longest prepared item: {max(lengths, default=0)} characters")
    print(f"Average prepared item: {sum(lengths)/len(lengths):.0f} characters" if lengths else "No work items")
    print(f"Model: {config.ACTIVE_MODEL}")
    print(f"Daily request budget: {config.DAILY_REQUEST_BUDGET}")
    print("No paid API calls were made.")
