import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple


PRONOUNS = {
    "it",
    "this",
    "that",
    "these",
    "those",
    "they",
    "them",
    "he",
    "she",
    "him",
    "her",
    "his",
    "hers",
    "their",
    "theirs",
}
PREPOSITIONS = {"to", "for", "with", "from", "in", "on", "at", "by", "into", "onto"}

PASSIVE_AUX = r"(?:is|are|was|were|be|been|being)"
STOPWORDS = {
    "the",
    "a",
    "an",
    "to",
    "for",
    "of",
    "and",
    "or",
    "in",
    "on",
    "with",
    "by",
    "at",
    "from",
    "then",
    "now",
}

IRREGULAR_PARTICIPLES = {
    "written": "write",
    "given": "give",
    "taken": "take",
    "done": "do",
    "made": "make",
    "seen": "see",
    "known": "know",
    "sent": "send",
    "read": "read",
    "built": "build",
    "left": "leave",
    "completed": "complete",
    "approved": "approve",
    "changed": "change",
    "closed": "close",
    "used": "use",
}

IRREGULAR_PAST = {
    "written": "wrote",
    "given": "gave",
    "taken": "took",
    "done": "did",
    "made": "made",
    "seen": "saw",
    "known": "knew",
    "sent": "sent",
    "read": "read",
    "built": "built",
    "left": "left",
}


@dataclass
class InstructionUnit:
    original: str
    rewritten: str
    actor: Optional[str]
    action: Optional[str]
    object: Optional[str]
    constraints: List[str]
    conditions: List[str]
    unresolved_references: List[str]
    passive_detected: bool
    passive_remaining: bool
    confidence: float
    notes: List[str]


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _base_form(word: str) -> str:
    w = word.lower()
    if w in IRREGULAR_PARTICIPLES:
        return IRREGULAR_PARTICIPLES[w]
    if w.endswith("ied") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("ed") and len(w) > 3:
        root = w[:-2]
        if len(root) > 2 and root[-1] == root[-2]:
            root = root[:-1]
        return root
    return w


def _replace_ambiguous_pronouns(
    sentence: str, last_entity: Optional[str], last_actor: Optional[str]
) -> Tuple[str, List[str]]:
    unresolved = []
    tokens = re.findall(r"\w+|[^\w\s]", sentence)
    rewritten_tokens = []
    for token in tokens:
        lower = token.lower()
        if lower in PRONOUNS:
            resolved = False
            if lower in {"it", "this", "that", "these", "those"} and last_entity:
                replacement = last_entity
                if token[:1].isupper():
                    replacement = replacement[:1].upper() + replacement[1:]
                rewritten_tokens.append(replacement)
                resolved = True
            elif lower in {"he", "she", "him", "her", "his", "hers"} and last_actor:
                replacement = last_actor
                if token[:1].isupper():
                    replacement = replacement[:1].upper() + replacement[1:]
                rewritten_tokens.append(replacement)
                resolved = True
            elif lower in {"they", "them", "their", "theirs"} and last_actor:
                replacement = last_actor
                if token[:1].isupper():
                    replacement = replacement[:1].upper() + replacement[1:]
                rewritten_tokens.append(replacement)
                resolved = True

            if not resolved:
                unresolved.append(lower)
                rewritten_tokens.append(token)
            continue
        rewritten_tokens.append(token)
    rebuilt = " ".join(rewritten_tokens)
    rebuilt = re.sub(r"\s+([,.;:!?])", r"\1", rebuilt)
    return rebuilt, sorted(set(unresolved))


def _capitalize_sentence_start(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _normalize_moved_object(obj: str) -> str:
    """Lowercase a leading article when moving an object into mid-sentence position."""
    return re.sub(r"^(The|A|An)\b", lambda m: m.group(1).lower(), obj, count=1)


def _participle_to_active_verb(participle: str, aux: str) -> str:
    p = participle.lower()
    a = aux.lower()
    if a in {"was", "were", "been", "being", "be"}:
        if p in IRREGULAR_PAST:
            return IRREGULAR_PAST[p]
        return p if p.endswith("ed") else _base_form(p)
    if a in {"is", "are"}:
        base = _base_form(p)
        if base.endswith(("s", "x", "z", "ch", "sh")):
            return base + "es"
        if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
            return base[:-1] + "ies"
        return base + "s"
    return _base_form(p)


def _normalize_entity_phrase(obj: str) -> str:
    cleaned = obj.strip().rstrip(",.;:!?")
    words = cleaned.split()
    if not words:
        return cleaned
    phrase = [words[0]]
    for w in words[1:]:
        if w.lower() in PREPOSITIONS:
            break
        phrase.append(w)
    return " ".join(phrase)


def _convert_passive(sentence: str) -> Tuple[str, bool]:
    modal_pattern = re.compile(
        rf"^(?P<object>.+?)\s+(?P<modal>must|should|may|can|will)\s+be\s+(?P<verb>\w+)\s+by\s+(?P<actor>.+?)(?P<end>[.!?]?)$",
        re.IGNORECASE,
    )
    m = modal_pattern.match(sentence)
    if m:
        obj = _normalize_moved_object(m.group("object").strip())
        modal = m.group("modal").lower()
        verb = _base_form(m.group("verb"))
        actor = _capitalize_sentence_start(m.group("actor").strip())
        end = m.group("end") or "."
        return f"{actor} {modal} {verb} {obj}{end}", True

    past_pattern = re.compile(
        rf"^(?P<object>.+?)\s+(?P<aux>{PASSIVE_AUX})\s+(?P<verb>\w+)\s+by\s+(?P<actor>.+?)(?P<end>[.!?]?)$",
        re.IGNORECASE,
    )
    m = past_pattern.match(sentence)
    if m:
        obj = _normalize_moved_object(m.group("object").strip())
        verb = _participle_to_active_verb(m.group("verb").strip(), m.group("aux").strip())
        actor = _capitalize_sentence_start(m.group("actor").strip())
        end = m.group("end") or "."
        return f"{actor} {verb} {obj}{end}", True

    return sentence, False


def _extract_conditions(sentence: str) -> List[str]:
    matches = re.findall(r"\b(if|when|unless)\b(.+?)(?:[.;!?]|$)", sentence, flags=re.IGNORECASE)
    return [f"{kw.lower()} {rest.strip()}" for kw, rest in matches]


def _extract_constraints(sentence: str) -> List[str]:
    constraints = []
    if re.search(r"\bmust\b", sentence, flags=re.IGNORECASE):
        constraints.append("must")
    if re.search(r"\bshould\b", sentence, flags=re.IGNORECASE):
        constraints.append("should")
    if re.search(r"\bonly\b", sentence, flags=re.IGNORECASE):
        constraints.append("only")
    return constraints


def _parse_actor_action_object(sentence: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    cleaned = sentence.strip().rstrip(".!?")
    words = cleaned.split()
    if len(words) < 2:
        return cleaned if cleaned else None, None, None
    if len(words) >= 3 and words[1].lower() in {"the", "a", "an"}:
        action = words[0]
        obj = " ".join(words[1:])
        return None, action, obj
    actor = words[0]
    action = words[1]
    obj = " ".join(words[2:]) if len(words) > 2 else None
    return actor, action, obj


def _contains_passive(sentence: str) -> bool:
    return bool(re.search(rf"\b{PASSIVE_AUX}\b\s+\w+(?:\s+by\b)?", sentence, flags=re.IGNORECASE))


def _content_terms(sentence: str) -> set:
    terms = {
        w.lower()
        for w in re.findall(r"[A-Za-z']+", sentence)
        if w.lower() not in STOPWORDS and w.lower() not in PRONOUNS
    }
    return terms


def _confidence(original: str, rewritten: str, unresolved_count: int, passive_remaining: bool) -> Tuple[float, List[str]]:
    notes = []
    original_terms = _content_terms(original)
    rewritten_terms = _content_terms(rewritten)
    overlap = len(original_terms & rewritten_terms) / max(len(original_terms | rewritten_terms), 1)
    score = overlap
    if unresolved_count:
        score -= 0.3
        notes.append("Unresolved reference(s) remain.")
    if passive_remaining:
        score -= 0.2
        notes.append("Passive voice still detected.")
    if overlap < 0.5:
        notes.append("Low semantic overlap after rewrite.")
    return max(0.0, min(1.0, round(score, 2))), notes


def rewrite_instructions(text: str) -> Dict[str, Any]:
    sentences = _split_sentences(text)
    units: List[InstructionUnit] = []
    rewritten_sentences: List[str] = []
    last_entity: Optional[str] = None
    last_actor: Optional[str] = None

    for sentence in sentences:
        active_sentence, passive_detected = _convert_passive(sentence)
        resolved_sentence, unresolved = _replace_ambiguous_pronouns(active_sentence, last_entity, last_actor)
        passive_remaining = _contains_passive(resolved_sentence)
        actor, action, obj = _parse_actor_action_object(resolved_sentence)
        constraints = _extract_constraints(resolved_sentence)
        conditions = _extract_conditions(resolved_sentence)
        conf, notes = _confidence(sentence, resolved_sentence, len(unresolved), passive_remaining)

        unit = InstructionUnit(
            original=sentence,
            rewritten=resolved_sentence,
            actor=actor,
            action=action,
            object=obj,
            constraints=constraints,
            conditions=conditions,
            unresolved_references=unresolved,
            passive_detected=passive_detected,
            passive_remaining=passive_remaining,
            confidence=conf,
            notes=notes,
        )
        units.append(unit)
        rewritten_sentences.append(resolved_sentence)

        if obj:
            last_entity = _normalize_entity_phrase(obj)
        if actor:
            last_actor = actor

    unresolved_all = sorted({r for unit in units for r in unit.unresolved_references})
    passive_remaining_all = any(unit.passive_remaining for unit in units)
    overall_confidence = round(sum(unit.confidence for unit in units) / max(len(units), 1), 2)
    notes_all = []
    if unresolved_all:
        notes_all.append("Some pronouns could not be resolved to explicit entities.")
    if passive_remaining_all:
        notes_all.append("Some instructions still appear to use passive voice.")

    return {
        "human_readable": " ".join(rewritten_sentences),
        "machine_readable": [asdict(unit) for unit in units],
        "quality_checks": {
            "unresolved_references": unresolved_all,
            "passive_sentences_remaining": passive_remaining_all,
            "overall_confidence": overall_confidence,
            "notes": notes_all,
        },
    }
