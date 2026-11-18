import json
from config import ENTITY_TYPES, PREDICATES

SYSTEM_PROMPT = """You are a precise agricultural knowledge-graph extraction system.
Extract every distinct, explicitly stated factual relationship in the supplied passage.
Do not use outside knowledge, infer plausible agronomy, or invent values or recommendations.
There is NO fixed maximum number of triples: extract all useful supported facts.
Each triple must be atomic and preserve exact crop/variety names, values, units, rates,
conditions, stages, seasons, locations and exceptions. Put context in qualifiers.
Use LITERAL for numeric values, rates, ranges, dates, durations and other non-entity values.
Use only allowed entity types and predicates. Use OTHER only for a clearly stated relation
that genuinely does not fit an available predicate. Do not emit generic filler relations.

EVIDENCE IS CRITICAL:
- evidence must be ONE continuous, exact quotation copied from the passage.
- Copy it character-for-character as far as possible; do not paraphrase, summarize,
  combine distant phrases, insert ellipses, or normalize numbers/units.
- Keep evidence concise but sufficient to support the whole relationship.
- If one continuous excerpt cannot support the triple, do not emit that triple.

For tables, use headers and row labels together. Preserve the exact row-to-column mapping.
If table structure is unclear, omit only the ambiguous relationship, not clear facts nearby.
Do not extract from metadata alone or from headings without supporting content.
Return one JSON object with a triples array and no markdown or commentary.
"""

TRIPLE_SCHEMA = {
  "type": "object", "properties": {"triples": {"type": "array", "items": {
    "type": "object", "properties": {
      "subject": {"type": "string"}, "subject_type": {"type": "string", "enum": ENTITY_TYPES},
      "predicate": {"type": "string", "enum": PREDICATES}, "object": {"type": "string"},
      "object_type": {"type": "string", "enum": ENTITY_TYPES + ["LITERAL"]},
      "evidence": {"type": "string"}, "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "qualifiers": {"type": "object", "additionalProperties": {"type": "string"}
      }
    }, "required": ["subject", "subject_type", "predicate", "object", "object_type", "evidence", "confidence", "qualifiers"],
    "additionalProperties": False
  }}}, "required": ["triples"], "additionalProperties": False
}

def build_user_prompt(chunk_text, metadata):
    return f"""Extract all supported agricultural knowledge graph triples from this passage.
Allowed entity types: {', '.join(ENTITY_TYPES)}
Allowed predicates: {', '.join(PREDICATES)}
Metadata is provenance/context only, never proof: {json.dumps(metadata, ensure_ascii=False, default=str)}

Important: there is no arbitrary triple-count limit. Completeness matters, but never guess.
For a table, interpret each row with its column headings; repeat crop/season/location context
in qualifiers where appropriate. A numeric recommendation must retain its exact value and unit.
Evidence must be a single contiguous verbatim excerpt from the passage, without ellipses.

PASSAGE START
{chunk_text}
PASSAGE END
"""
