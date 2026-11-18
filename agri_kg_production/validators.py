import re, json, hashlib, unicodedata
from config import ENTITY_TYPES, PREDICATES

def normalize_text(value):
    s = unicodedata.normalize("NFKC", str(value or "")).casefold()
    s = s.replace("\u00a0", " ").replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def stable_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def validate_and_clean_triples(raw_triples, source_text):
    accepted, rejected = [], []
    normalized_source = normalize_text(source_text)
    for index, item in enumerate(raw_triples or []):
        try:
            if not isinstance(item, dict): raise ValueError("Triple is not an object")
            subject = str(item.get("subject", "")).strip()
            subject_type = str(item.get("subject_type", "")).strip().upper()
            predicate = str(item.get("predicate", "")).strip().upper()
            obj = str(item.get("object", "")).strip()
            object_type = str(item.get("object_type", "")).strip().upper()
            evidence = str(item.get("evidence", "")).strip()
            confidence = float(item.get("confidence", 0))
            qualifiers = item.get("qualifiers", {})
            if not subject or not obj or not evidence: raise ValueError("Empty subject, object, or evidence")
            if subject_type not in ENTITY_TYPES: raise ValueError(f"Invalid subject_type: {subject_type}")
            if predicate not in PREDICATES: raise ValueError(f"Invalid predicate: {predicate}")
            if object_type not in ENTITY_TYPES + ["LITERAL"]: raise ValueError(f"Invalid object_type: {object_type}")
            if not 0 <= confidence <= 1: raise ValueError("Confidence outside [0,1]")
            if not isinstance(qualifiers, dict): raise ValueError("qualifiers must be an object")
            ne = normalize_text(evidence)
            if len(ne) < 8: raise ValueError("Evidence excerpt is too short")
            # Conservative exact-match after Unicode and whitespace normalization only.
            if ne not in normalized_source:
                raise ValueError("Evidence is not a continuous verbatim excerpt from source")
            if normalize_text(subject) == normalize_text(obj): raise ValueError("Self-loop rejected")
            accepted.append({"subject":subject,"subject_type":subject_type,"predicate":predicate,
                "object":obj,"object_type":object_type,"evidence":evidence,"confidence":round(confidence,4),
                "qualifiers":{str(k):str(v) for k,v in qualifiers.items() if str(k).strip() and str(v).strip()}})
        except Exception as exc:
            rejected.append({"index":index,"reason":str(exc),"raw":item})
    unique, seen = [], set()
    for t in accepted:
        key=(normalize_text(t["subject"]),t["predicate"],normalize_text(t["object"]),json.dumps(t["qualifiers"],sort_keys=True,ensure_ascii=False))
        if key not in seen: seen.add(key); unique.append(t)
    return unique, rejected
