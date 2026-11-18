import csv, json
import config
from storage import KGStore

def export_all():
    config.OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    store=KGStore(config.DB_PATH)
    try:
        triples=store.fetch_triples(); rejected=store.fetch_rejected(); statuses=store.fetch_chunk_status(); stats=store.stats()
        stats["rejected_records"] = len(rejected)
        outputs={
            "triples.json":triples,
            "rejected_triples.json":rejected,
            "chunk_status.json":statuses,
            "extraction_stats.json":stats,
        }
        for name,data in outputs.items():
            (config.OUTPUT_DIR/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        with (config.OUTPUT_DIR/"triples.jsonl").open("w",encoding="utf-8") as f:
            for row in triples: f.write(json.dumps(row,ensure_ascii=False)+"\n")
        fields=["triple_id","subject","subject_type","predicate","object","object_type","evidence","confidence","qualifiers","source","crop","chunk_id","chunk_key","metadata","model"]
        with (config.OUTPUT_DIR/"triples.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader()
            for item in triples:
                row=dict(item); row["qualifiers"]=json.dumps(row["qualifiers"],ensure_ascii=False); row["metadata"]=json.dumps(row["metadata"],ensure_ascii=False); w.writerow(row)
        print(f"Exported {len(triples)} accepted triples and {len(rejected)} rejected records to {config.OUTPUT_DIR}")
    finally: store.close()

if __name__=="__main__": export_all()
