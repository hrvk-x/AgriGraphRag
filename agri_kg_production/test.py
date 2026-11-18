import json
from pathlib import Path

output_dir = Path("output")

for filename in [
    "triples.json",
    "extraction_stats.json",
]:
    path = output_dir / filename

    print(f"\n{'=' * 60}")
    print(filename)

    if not path.exists():
        print("File not found")
        continue

    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        print("Records:", len(data))

        for i, record in enumerate(data[:3], start=1):
            print(f"\nRecord {i}:")
            print(json.dumps(record, indent=2, ensure_ascii=False))

    elif isinstance(data, dict):
        print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])
    else:
        print(data)