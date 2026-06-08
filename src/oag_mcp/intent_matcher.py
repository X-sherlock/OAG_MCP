from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any


PRIORITY_RANK = {"primary": 0, "secondary": 1, "optional": 2}
SPECIFICITY_ORDER = {
    "risk_overview": 0,
    "benchmark_comparison": 1,
    "peer_comparison": 2,
    "performance_overview": 3,
}


@dataclass(frozen=True)
class IntentMatchResult:
    matched_intents: list[dict[str, Any]]
    inferred_attributes: list[dict[str, Any]]
    skill_priority_hints: dict[str, str]


class IntentMatcher:
    """Match broad user wording to schema-level attributes and skill priorities."""

    def __init__(self, profiles: list[dict[str, Any]]) -> None:
        self._profiles = profiles

    def match(
        self,
        question: str,
        resolved_params: dict[str, Any],
        explicit_attributes: list[dict[str, Any]],
    ) -> IntentMatchResult:
        del resolved_params
        normalized_question = _normalize(question)
        ranked = self._rank_profiles(normalized_question)
        matched_intents = [_intent_payload(item, index) for index, item in enumerate(ranked)]
        skill_priority_hints = _skill_priority_hints(ranked)
        explicit_names = {
            item.get("attribute_name") for item in explicit_attributes if item.get("attribute_name")
        }
        inferred_attributes = _inferred_attribute_hints(ranked, explicit_names)
        return IntentMatchResult(
            matched_intents=matched_intents,
            inferred_attributes=inferred_attributes,
            skill_priority_hints=skill_priority_hints,
        )

    def _rank_profiles(self, normalized_question: str) -> list[dict[str, Any]]:
        matches = []
        for profile in self._profiles:
            triggers = [
                alias
                for alias in profile.get("trigger_aliases") or []
                if _normalize(alias) and _normalize(alias) in normalized_question
            ]
            if not triggers:
                continue
            longest = max(triggers, key=lambda value: len(_normalize(value)))
            matches.append(
                {
                    "profile": profile,
                    "triggers": triggers,
                    "longest_trigger": longest,
                    "trigger_count": len(triggers),
                    "trigger_length": len(_normalize(longest)),
                }
            )
        matches.sort(
            key=lambda item: (
                -item["trigger_count"],
                -item["trigger_length"],
                SPECIFICITY_ORDER.get(item["profile"].get("intent_name"), 99),
            )
        )
        return matches


def _intent_payload(match: dict[str, Any], index: int) -> dict[str, Any]:
    profile = match["profile"]
    confidence = max(0.6, min(0.85, 0.85 - index * 0.08))
    trigger = match["longest_trigger"]
    return {
        "intent_name": profile.get("intent_name"),
        "intent_name_zh": profile.get("intent_name_zh", ""),
        "confidence": round(confidence, 3),
        "match_reason": f"trigger_alias_matched:{trigger}",
        "trigger": trigger,
    }


def _skill_priority_hints(matches: list[dict[str, Any]]) -> dict[str, str]:
    hints: dict[str, str] = {}
    for index, match in enumerate(matches):
        profile = match["profile"]
        for field, priority in (
            ("primary_skills", "primary"),
            ("secondary_skills", "secondary"),
            ("optional_skills", "optional"),
        ):
            effective_priority = priority
            if index > 0:
                effective_priority = _demote(priority)
            for skill_id in profile.get(field) or []:
                _set_best_priority(hints, str(skill_id), effective_priority)
    return hints


def _inferred_attribute_hints(
    matches: list[dict[str, Any]], explicit_names: set[Any]
) -> list[dict[str, Any]]:
    rows = []
    seen = set(explicit_names)
    for intent_index, match in enumerate(matches):
        profile = match["profile"]
        confidence_base = max(0.6, min(0.82, 0.82 - intent_index * 0.08))
        for attribute_index, attribute_name in enumerate(profile.get("default_attributes") or []):
            if not attribute_name or attribute_name in seen:
                continue
            seen.add(attribute_name)
            rows.append(
                {
                    "attribute_name": attribute_name,
                    "confidence": round(max(0.6, confidence_base - attribute_index * 0.015), 3),
                    "match_reason": f"inferred_by_intent:{profile.get('intent_name')}",
                    "intent_name": profile.get("intent_name"),
                }
            )
    return rows


def _demote(priority: str) -> str:
    if priority == "primary":
        return "secondary"
    return "optional"


def _set_best_priority(hints: dict[str, str], skill_id: str, priority: str) -> None:
    current = hints.get(skill_id)
    if current is None or PRIORITY_RANK[priority] < PRIORITY_RANK[current]:
        hints[skill_id] = priority


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return "".join(text.split()).lower()
