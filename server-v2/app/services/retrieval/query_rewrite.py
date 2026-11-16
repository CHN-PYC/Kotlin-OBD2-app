import re
from typing import ClassVar

from app.schemas.memory import ConversationTurn, SessionMemory
from app.schemas.qa import VehicleQARequest
from app.schemas.query_rewrite import QueryRewriteResult

_REFERENTIAL = re.compile(r"这个|那个|它|刚才|之前|上述|还是这样|这种情况")
_DTC = re.compile(r"\b[PBCU][0-9A-Fa-f]{4}\b")
_MAX_QUERY_CHARACTERS = 500
_SEPARATOR = "；"


def _is_follow_up(question: str) -> bool:
    return bool(_REFERENTIAL.search(question)) or len(question) <= 6


class DeterministicQueryRewriter:
    """Add explicit diagnostic terms without asking another model or inventing facts."""

    _aliases: ClassVar[dict[str, str]] = {
        "水温": "冷却液温度 ECT",
        "空气流量计": "空气质量流量传感器 MAF",
        "进气压力": "进气歧管绝对压力 MAP",
        "短期燃油修正": "STFT",
        "长期燃油修正": "LTFT",
        "氧传感器": "Lambda O2",
        "电瓶": "蓄电池电压",
        "节气门": "THROTTLE",
    }

    def rewrite(
        self,
        request: VehicleQARequest,
        memory: SessionMemory,
    ) -> QueryRewriteResult:
        original = request.question.strip()
        rules: list[str] = []

        # LEARNING: 只引用历史的原始问题，绝不引用上一轮 rewritten_query；
        # 派生结果回流会让每轮嵌套一层，长度无限增长。
        anchor = self._topic_anchor(memory.turns) if _is_follow_up(original) else None
        if anchor is not None:
            rules.append("resolve_previous_turn_reference")
        source_text = original if anchor is None else f"{original} {anchor}"

        enrichments: list[str] = []
        terms = [
            canonical
            for alias, canonical in self._aliases.items()
            if alias in source_text and canonical.lower() not in source_text.lower()
        ]
        if terms:
            enrichments.append(f"标准术语：{'、'.join(dict.fromkeys(terms))}")
            rules.append("normalize_vehicle_terms")

        codes = {code.upper() for code in _DTC.findall(source_text)}
        if request.rule_summary is not None and (
            "故障码" in original or "报码" in original or _REFERENTIAL.search(original)
        ):
            codes.update(
                finding.code.upper()
                for finding in request.rule_summary.findings
                if _DTC.fullmatch(finding.code)
            )
        if codes and not all(code in original for code in codes):
            enrichments.append(f"相关 DTC：{'、'.join(sorted(codes))}")
            rules.append("preserve_dtc_codes")

        return QueryRewriteResult(
            original_query=original,
            rewritten_query=self._compose(original, enrichments, anchor),
            applied_rules=rules,
        )

    @staticmethod
    def _topic_anchor(turns: list[ConversationTurn]) -> str | None:
        """Latest self-contained question, so chained follow-ups keep the real topic."""
        # 记忆已由 session_max_turns 限长，这里扫描全部保留轮次；
        # 中间全是追问时，最近一条完整问题就是当前话题。
        for turn in reversed(turns):
            if not _is_follow_up(turn.question):
                return turn.question
        return turns[-1].question if turns else None

    @staticmethod
    def _compose(original: str, enrichments: list[str], anchor: str | None) -> str:
        # 优先级：当前问题 > 术语/DTC > 历史话题；超出预算时只截低优先级部分。
        query = original[:_MAX_QUERY_CHARACTERS]
        tail = [*enrichments, f"上文话题：{anchor}"] if anchor is not None else enrichments
        for part in tail:
            remaining = _MAX_QUERY_CHARACTERS - len(query) - len(_SEPARATOR)
            if remaining <= 0:
                break
            query = f"{query}{_SEPARATOR}{part[:remaining]}"
        return query
