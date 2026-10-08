import re
from typing import ClassVar

from app.schemas.memory import SessionMemory
from app.schemas.qa import VehicleQARequest
from app.schemas.query_rewrite import QueryRewriteResult

_REFERENTIAL = re.compile(r"这个|那个|它|刚才|之前|上述|还是这样|这种情况")
_DTC = re.compile(r"\b[PBCU][0-9A-Fa-f]{4}\b")


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
        rewritten = original
        rules: list[str] = []

        if (_REFERENTIAL.search(original) or len(original) <= 6) and memory.turns:
            rewritten = f"关于上一轮 {memory.turns[-1].rewritten_query}；当前问题：{original}"
            rules.append("resolve_previous_turn_reference")

        normalized_terms: list[str] = []
        for alias, canonical in self._aliases.items():
            if alias in rewritten and canonical.lower() not in rewritten.lower():
                normalized_terms.append(canonical)
        if normalized_terms:
            rewritten = f"{rewritten}；标准术语：{'、'.join(dict.fromkeys(normalized_terms))}"
            rules.append("normalize_vehicle_terms")

        codes = {code.upper() for code in _DTC.findall(rewritten)}
        if request.rule_summary is not None and (
            "故障码" in original or "报码" in original or _REFERENTIAL.search(original)
        ):
            codes.update(
                finding.code.upper()
                for finding in request.rule_summary.findings
                if _DTC.fullmatch(finding.code)
            )
        if codes and not all(code in rewritten for code in codes):
            rewritten = f"{rewritten}；相关 DTC：{'、'.join(sorted(codes))}"
            rules.append("preserve_dtc_codes")

        return QueryRewriteResult(
            original_query=original,
            rewritten_query=rewritten[:500],
            applied_rules=rules,
        )
