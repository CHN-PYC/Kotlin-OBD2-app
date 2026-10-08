from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.reranking import RerankedSource
from app.schemas.vehicle_context import SessionSummary
from app.services.retrieval.query_retrieval import QueryRetrievalService
from app.tools.registry import AgentTool


class KnowledgeSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchOutput(BaseModel):
    sources: list[RerankedSource]


class SearchVehicleKnowledgeTool(AgentTool):
    name = "search_vehicle_knowledge"
    description = "Search reviewed vehicle diagnostic evidence using the configured retrieval pipeline."
    input_model = KnowledgeSearchInput
    output_model = KnowledgeSearchOutput

    def __init__(self, service: QueryRetrievalService) -> None:
        self._service = service

    async def execute(self, tool_input: BaseModel) -> KnowledgeSearchOutput:
        request = KnowledgeSearchInput.model_validate(tool_input)
        sources = await self._service.retrieve(request.query, final_k=request.top_k)
        return KnowledgeSearchOutput(sources=sources)


class PidLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pids: list[str] = Field(min_length=1, max_length=10)

    @field_validator("pids")
    @classmethod
    def normalize_pids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values if value.strip()]
        if not normalized:
            raise ValueError("at least one non-blank PID is required")
        return list(dict.fromkeys(normalized))


class PidDefinition(BaseModel):
    pid: str
    name: str
    meaning: str
    unit: str | None = None


class PidLookupOutput(BaseModel):
    definitions: list[PidDefinition]
    unknown_pids: list[str]


class LookupPidDefinitionTool(AgentTool):
    name = "lookup_pid_definition"
    description = "Explain supported OBD-II PID names and units without diagnosing a failed part."
    input_model = PidLookupInput
    output_model = PidLookupOutput

    _definitions: ClassVar[dict[str, tuple[str, str, str | None]]] = {
        "RPM": ("Engine speed", "Engine crankshaft revolutions per minute.", "rpm"),
        "ECT": ("Coolant temperature", "Engine coolant temperature reported to the ECU.", "°C"),
        "VOLTAGE": ("Control module voltage", "Electrical system voltage observed by the ECU.", "V"),
        "STFT": ("Short-term fuel trim", "Immediate closed-loop fuel correction.", "%"),
        "LTFT": ("Long-term fuel trim", "Learned persistent fuel correction.", "%"),
        "MAP": ("Manifold absolute pressure", "Absolute pressure used to estimate engine load.", "kPa"),
        "MAF": ("Mass air flow", "Intake air mass rate used for load and fueling.", "g/s"),
        "LAMBDA": ("Equivalence ratio", "Mixture feedback relative to stoichiometric operation.", None),
        "THROTTLE": ("Throttle position", "Reported throttle opening position.", "%"),
    }

    async def execute(self, tool_input: BaseModel) -> PidLookupOutput:
        request = PidLookupInput.model_validate(tool_input)
        definitions = [
            PidDefinition(pid=pid, name=value[0], meaning=value[1], unit=value[2])
            for pid in request.pids
            if (value := self._definitions.get(pid)) is not None
        ]
        known = {item.pid for item in definitions}
        return PidLookupOutput(
            definitions=definitions,
            unknown_pids=[pid for pid in request.pids if pid not in known],
        )


class DtcInterpretInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(pattern=r"^[PBCU][0-9A-Fa-f]{4}$")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class DtcInterpretOutput(BaseModel):
    code: str
    system: str
    family: str
    diagnostic_note: str


class InterpretDtcTool(AgentTool):
    name = "interpret_dtc"
    description = "Classify a validated five-character DTC and return a conservative diagnostic note."
    input_model = DtcInterpretInput
    output_model = DtcInterpretOutput

    _systems: ClassVar[dict[str, str]] = {
        "P": "powertrain",
        "B": "body",
        "C": "chassis",
        "U": "network",
    }

    async def execute(self, tool_input: BaseModel) -> DtcInterpretOutput:
        request = DtcInterpretInput.model_validate(tool_input)
        numeric = int(request.code[1:], 16)
        family = "manufacturer_or_system_specific"
        if request.code.startswith("P01"):
            family = "air_fuel_metering"
        elif request.code.startswith("P03"):
            family = "ignition_or_misfire"
        elif request.code.startswith("P21"):
            family = "throttle_actuator_control"
        return DtcInterpretOutput(
            code=request.code,
            system=self._systems[request.code[0]],
            family=family,
            diagnostic_note=(
                f"DTC numeric payload 0x{numeric:04X} identifies a detected condition, "
                "not proof that a named component must be replaced."
            ),
        )


class SignalSeverity(str, Enum):
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    HIGH = "HIGH"


class SignalObservation(BaseModel):
    code: str
    severity: SignalSeverity
    actual: float
    condition: str


class SessionSignalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: SessionSummary


class SessionSignalOutput(BaseModel):
    observations: list[SignalObservation]
    limitations: list[str]


class AnalyzeSessionSignalsTool(AgentTool):
    name = "analyze_session_signals"
    description = "Apply deterministic screening thresholds to an aggregated OBD-II session."
    input_model = SessionSignalInput
    output_model = SessionSignalOutput

    async def execute(self, tool_input: BaseModel) -> SessionSignalOutput:
        summary = SessionSignalInput.model_validate(tool_input).summary
        observations: list[SignalObservation] = []
        if summary.max_coolant_temp >= 110:
            self._append_if(
                observations,
                True,
                "COOLANT_OVERHEAT",
                SignalSeverity.HIGH,
                summary.max_coolant_temp,
                ">= 110 °C",
            )
        else:
            self._append_if(
                observations,
                summary.max_coolant_temp >= 105,
                "COOLANT_HIGH",
                SignalSeverity.WARNING,
                summary.max_coolant_temp,
                ">= 105 °C",
            )
        self._append_if(
            observations,
            summary.min_battery_voltage < 12.0,
            "VOLTAGE_LOW",
            SignalSeverity.WARNING,
            summary.min_battery_voltage,
            "< 12.0 V",
        )
        self._append_if(
            observations,
            abs(summary.avg_stft1) >= 12,
            "STFT_ABNORMAL",
            SignalSeverity.WARNING,
            summary.avg_stft1,
            "absolute average >= 12%",
        )
        self._append_if(
            observations,
            abs(summary.avg_ltft1) >= 10,
            "LTFT_ABNORMAL",
            SignalSeverity.WARNING,
            summary.avg_ltft1,
            "absolute average >= 10%",
        )
        self._append_if(
            observations,
            not 0.95 <= summary.avg_lambda <= 1.05,
            "LAMBDA_DEVIATION",
            SignalSeverity.NOTICE,
            summary.avg_lambda,
            "outside 0.95-1.05",
        )
        return SessionSignalOutput(
            observations=observations,
            limitations=[
                "Screening thresholds are project heuristics, not vehicle-specific repair limits.",
                "Aggregates can hide transient faults; inspect sample highlights and operating conditions.",
            ],
        )

    @staticmethod
    def _append_if(
        observations: list[SignalObservation],
        matched: bool,
        code: str,
        severity: SignalSeverity,
        actual: float,
        condition: str,
    ) -> None:
        if matched:
            observations.append(
                SignalObservation(
                    code=code,
                    severity=severity,
                    actual=float(actual),
                    condition=condition,
                )
            )
