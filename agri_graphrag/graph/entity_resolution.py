import re, unicodedata
def normalize_name(name):
    value = unicodedata.normalize("NFKC", str(name)).strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")
def entity_id(name, entity_type):
    return f"{str(entity_type).strip().upper()}::{normalize_name(name)}"
