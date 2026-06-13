class QueryRewriteService:
    def rewrite(self, question: str, vehicle_context: dict, rule_summary: dict | None = None) -> str:
        hints: list[str] = [question]
        session_summary = vehicle_context.get("sessionSummary") or vehicle_context.get("session_summary") or {}
        hottest = vehicle_context.get("sampleHighlights", {}).get("hottestSample") if isinstance(vehicle_context.get("sampleHighlights"), dict) else None

        if session_summary.get("maxCoolantTemp"):
            hints.append(f"maxCoolantTemp={session_summary['maxCoolantTemp']}")
            hints.append("coolant temperature overheating radiator thermostat fan")
        if session_summary.get("avgStft1") or session_summary.get("avgLtft1"):
            hints.append("fuel trim STFT LTFT lean rich mixture vacuum injector")
        if session_summary.get("minBatteryVoltage"):
            hints.append("battery voltage alternator charging electrical")
        if hottest:
            hints.append("hottest sample engine temperature")
        if rule_summary:
            summary = rule_summary.get("summary") or ""
            hints.append(summary)
        return " | ".join(part for part in hints if part)
