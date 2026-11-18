import hashlib, json, logging, os, random, re, time
from pathlib import Path
import requests
import config
from prompts import SYSTEM_PROMPT, TRIPLE_SCHEMA, build_user_prompt
from storage import DailyBudgetExceeded, KGStore
from validators import validate_and_clean_triples

class GenerationError(RuntimeError): pass
class GenerationTruncatedError(GenerationError): pass
class RateLimitStop(RuntimeError): pass
class InsufficientCreditsStop(RuntimeError): pass
class PermanentAPIError(RuntimeError): pass


def setup_logging():
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(config.LOG_PATH, encoding="utf-8"), logging.StreamHandler()], force=True)


def load_input_chunks(path):
    with open(path, "r", encoding="utf-8") as f: data=json.load(f)
    if isinstance(data,list): raw=data
    elif isinstance(data,dict) and "page_content" in data: raw=[data]
    elif isinstance(data,dict):
        raw=next((data[k] for k in ("chunks","data","documents","records") if isinstance(data.get(k),list)),None)
        if raw is None: raise ValueError("Input JSON must be a list or contain chunks/data/documents/records.")
    else: raise ValueError("Input JSON must be a list or object.")
    out=[]
    for i,item in enumerate(raw):
        if not isinstance(item,dict): logging.warning("Skipping non-object input at index %s",i); continue
        text=str(item.get("page_content",item.get("text",""))).strip()
        if not text: continue
        meta=item.get("metadata") or {}
        if not isinstance(meta,dict): meta={"raw_metadata":str(meta)}
        out.append({"source_index":i,"page_content":text,"metadata":meta})
    return out


def _is_table_line(line):
    return ("\t" in line) or (line.count("|") >= 2)


def _split_long_block(block, limit):
    lines=block.splitlines()
    # Keep table rows intact and repeat the header row in each table subpart.
    table_positions=[i for i,line in enumerate(lines) if _is_table_line(line)]
    if len(lines)>1 and len(table_positions)/len(lines) >= 0.6:
        header_index=table_positions[0]
        preamble="\n".join(lines[:header_index]).strip()
        table_lines=lines[header_index:]
        header=table_lines[0]
        pieces=[preamble] if preamble else []; current=[]; size=len(header)
        for line in table_lines[1:]:
            if current and size+len(line)+1>limit:
                pieces.append("\n".join([header]+current)); current=[]; size=len(header)
            if len(line)+len(header)+1>limit:
                # An exceptionally long single row: preserve it intact rather than slicing cells.
                if current: pieces.append("\n".join([header]+current)); current=[]; size=len(header)
                pieces.append("\n".join([header,line]))
            else: current.append(line); size+=len(line)+1
        if current: pieces.append("\n".join([header]+current))
        return pieces or [block]
    # Prefer line/sentence boundaries; only split on whitespace as last resort.
    units=[x.strip() for x in lines if x.strip()]
    if len(units)<=1:
        units=re.split(r"(?<=[.!?;])\s+",block.strip())
    pieces=[]; current=""
    for unit in units:
        if len(unit)>limit:
            if current: pieces.append(current); current=""
            words=unit.split()
            part=""
            for word in words:
                if part and len(part)+1+len(word)>limit:
                    pieces.append(part); part=word
                else: part=(part+" "+word).strip()
            if part: pieces.append(part)
        elif current and len(current)+2+len(unit)>limit:
            pieces.append(current); current=unit
        else: current=(current+"\n"+unit).strip()
    if current: pieces.append(current)
    return pieces


def split_text(text, limit):
    paragraphs=[p.strip() for p in re.split(r"\n\s*\n",text) if p.strip()]
    blocks=[]
    for p in paragraphs:
        if len(p)>limit: blocks.extend(_split_long_block(p,limit))
        else: blocks.append(p)
    out=[]; cur=""
    for block in blocks:
        if cur and len(cur)+2+len(block)>limit:
            out.append(cur); cur=block
        else: cur=(cur+"\n\n"+block).strip()
    if cur: out.append(cur)
    return out or [text]


def prepare_work_items(chunks):
    work=[]
    for chunk in chunks:
        parts=split_text(chunk["page_content"],config.TARGET_CHUNK_CHARS)
        for n,piece in enumerate(parts,1):
            meta=dict(chunk["metadata"])
            meta["original_source_index"]=chunk["source_index"]
            meta["extraction_subpart"]=n
            idx=chunk["source_index"]*10000+n
            identity=f"{idx}|{json.dumps(meta,sort_keys=True,ensure_ascii=False,default=str)}|{piece}"
            work.append({"source_index":idx,"page_content":piece,"metadata":meta,
                         "chunk_key":hashlib.sha256(identity.encode()).hexdigest()})
    return work


def _extract_content(message):
    c=message.get("content","")
    if isinstance(c,str): return c
    if isinstance(c,list): return "".join(b.get("text","") for b in c if isinstance(b,dict))
    return str(c or "")


def call_openrouter(model,text,metadata,store):
    key=os.getenv(config.OPENROUTER_API_KEY_ENV)
    if not key: raise PermanentAPIError(f"Missing {config.OPENROUTER_API_KEY_ENV}. Set it in PowerShell.")
    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json",
             "HTTP-Referer":config.OPENROUTER_HTTP_REFERER,"X-Title":config.OPENROUTER_APP_TITLE}
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":build_user_prompt(text,metadata)}],
        "temperature":config.TEMPERATURE,"top_p":config.TOP_P,"max_tokens":config.MAX_OUTPUT_TOKENS,
        "response_format":{"type":"json_schema","json_schema":{"name":"agricultural_kg_triples",
        "strict":True,"schema":TRIPLE_SCHEMA}},"usage":{"include":True}}
    last=None
    for attempt in range(1,config.GENERATION_RETRIES+1):
        reserved=store.reserve_api_attempt(config.DAILY_REQUEST_BUDGET)
        logging.info("OpenRouter attempt %d/%d | model=%s | chars=%d | output_budget=%d | daily_request=%d/%d",
            attempt,config.GENERATION_RETRIES,model,len(text),config.MAX_OUTPUT_TOKENS,reserved,config.DAILY_REQUEST_BUDGET)
        try: response=requests.post(config.OPENROUTER_API_URL,headers=headers,json=payload,timeout=config.REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as e:
            last=e
            if attempt<config.GENERATION_RETRIES: time.sleep(config.RETRY_DELAY_SECONDS*attempt+random.random()); continue
            raise GenerationError(f"Network failure after {attempt} attempts: {e}") from e
        if response.status_code==429: raise RateLimitStop(f"OpenRouter HTTP 429. Stop now; response: {response.text[:1000]}")
        if response.status_code==402: raise InsufficientCreditsStop(f"OpenRouter insufficient credits (402): {response.text[:1000]}")
        if response.status_code in (400,401,403,404,422): raise PermanentAPIError(f"OpenRouter HTTP {response.status_code}: {response.text[:1400]}")
        if response.status_code in (408,500,502,503,504):
            last=RuntimeError(f"Temporary HTTP {response.status_code}: {response.text[:500]}")
            if attempt<config.GENERATION_RETRIES: time.sleep(config.RETRY_DELAY_SECONDS*attempt); continue
            raise GenerationError(str(last))
        try: response.raise_for_status(); body=response.json()
        except (requests.RequestException,ValueError) as e:
            last=e
            if attempt<config.GENERATION_RETRIES: time.sleep(config.RETRY_DELAY_SECONDS*attempt); continue
            raise GenerationError(f"Invalid API response: {e}") from e
        choices=body.get("choices") or []
        if not choices: raise GenerationError(f"No model choices in response: {str(body)[:800]}")
        choice=choices[0]; finish=str(choice.get("finish_reason") or "").lower()
        content=_extract_content(choice.get("message") or "").strip()
        if finish in ("length","max_tokens"):
            raise GenerationTruncatedError(f"Output truncated at {config.MAX_OUTPUT_TOKENS} tokens")
        try:
            parsed=json.loads(content)
            if not isinstance(parsed,dict) or not isinstance(parsed.get("triples"),list): raise ValueError("Expected {triples: [...]} JSON")
        except (ValueError,json.JSONDecodeError) as e: raise GenerationError(f"Invalid JSON from model: {e}; output={content[:600]}") from e
        usage=body.get("usage") or {}
        body["_normalized_usage"]={"prompt_tokens":usage.get("prompt_tokens",0),"completion_tokens":usage.get("completion_tokens",0),"cost":usage.get("cost")}
        return parsed["triples"],body
    raise GenerationError(str(last or "Generation failed"))


def _adaptive_extract(model,text,metadata,store,depth=0):
    try:
        return call_openrouter(model,text,metadata,store)
    except GenerationTruncatedError:
        if depth>=config.MAX_RECURSIVE_SPLIT_DEPTH or len(text)<=config.MIN_SPLIT_CHARS:
            raise GenerationError(f"Output still truncates after {depth} adaptive splits; chars={len(text)}")
        pieces=split_text(text,max(config.MIN_SPLIT_CHARS,len(text)//2))
        if len(pieces)<2:
            raise GenerationError(f"Cannot safely split truncated passage ({len(text)} chars)")
        logging.warning("Truncated output; splitting %d-char passage into %d smaller pieces (depth %d)",len(text),len(pieces),depth+1)
        triples=[]; usages=[]
        for i,piece in enumerate(pieces,1):
            child_meta=dict(metadata); child_meta["adaptive_split_depth"]=depth+1; child_meta["adaptive_split_part"]=i
            child_triples,body=_adaptive_extract(model,piece,child_meta,store,depth+1)
            triples.extend(child_triples); usages.append(body.get("_normalized_usage",{}))
        total={k:sum((u.get(k) or 0) for u in usages) for k in ("prompt_tokens","completion_tokens")}
        costs=[u.get("cost") for u in usages if isinstance(u.get("cost"),(int,float))]
        total["cost"]=sum(costs) if costs else None
        return triples,{"_normalized_usage":total}


def main():
    setup_logging()
    if not config.INPUT_JSON.exists(): raise FileNotFoundError(f"Input file not found: {config.INPUT_JSON}. Set AGRI_INPUT_JSON if needed.")
    chunks=load_input_chunks(config.INPUT_JSON)
    work=prepare_work_items(chunks)
    logging.info("Loaded %d source chunks; prepared %d extraction work items (target %d chars).",len(chunks),len(work),config.TARGET_CHUNK_CHARS)
    store=KGStore(config.DB_PATH); current=None; stop=False
    try:
        store.register_chunks(work)
        active_keys={item["chunk_key"] for item in work}
        pending=[item for item in store.get_pending_chunks(config.RETRY_FAILED_CHUNKS) if item["chunk_key"] in active_keys]
        logging.info("Model=%s | pending=%d | existing=%s | request_usage=%s",config.ACTIVE_MODEL,len(pending),json.dumps(store.stats()),store.request_usage())
        for n,chunk in enumerate(pending,1):
            current=chunk["chunk_key"]
            logging.info("[%d/%d] chunk_id=%s chars=%d",n,len(pending),chunk.get("chunk_id"),len(chunk["page_content"]))
            store.mark_processing(current,config.ACTIVE_MODEL)
            try:
                meta=json.loads(chunk["metadata_json"])
                raw,body=_adaptive_extract(config.ACTIVE_MODEL,chunk["page_content"],meta,store)
                accepted,rejected=validate_and_clean_triples(raw,chunk["page_content"])
                store.save_success(chunk,accepted,rejected,config.ACTIVE_MODEL)
                u=body.get("_normalized_usage",{})
                logging.info("Committed | raw=%d accepted=%d rejected=%d | input_tokens=%s output_tokens=%s cost=%s",
                    len(raw),len(accepted),len(rejected),u.get("prompt_tokens"),u.get("completion_tokens"),u.get("cost"))
                current=None
            except (DailyBudgetExceeded,RateLimitStop,InsufficientCreditsStop,PermanentAPIError) as e:
                store.mark_pending(current,str(e)); current=None; stop=True; logging.error("Paused safely: %s",e); break
            except KeyboardInterrupt:
                store.mark_pending(current,"Interrupted by user; retry on resume"); current=None; raise
            except Exception as e:
                store.mark_failed(current,e); logging.exception("Chunk failed; it remains retryable: %s",e); current=None
            if n%config.EXPORT_AFTER_EVERY_N_CHUNKS==0:
                logging.info("Progress: %s | requests=%s",json.dumps(store.stats()),store.request_usage())
    except KeyboardInterrupt: logging.warning("Interrupted. Completed chunks remain saved; current chunk will resume.")
    finally:
        if current: store.mark_pending(current,"Stopped before commit; retry on resume")
        logging.info("Final stats: %s | requests=%s",json.dumps(store.stats()),store.request_usage())
        store.close()
    from export_data import export_all
    export_all()
    if stop: logging.warning("Paused by provider/budget. Re-run extractor.py to resume.")
    else: logging.info("Session finished. Re-run to retry any failed chunks.")

if __name__=="__main__": main()
