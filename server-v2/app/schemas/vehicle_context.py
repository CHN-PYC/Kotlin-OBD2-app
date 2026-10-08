from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class SessionSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, strict=True)
    duration_sec: int = Field(ge=0)
    sample_count: int = Field(ge=0)
    avg_speed: float = Field(allow_inf_nan=False, ge=0)
    max_speed: int = Field(ge=0)
    avg_rpm: float = Field(allow_inf_nan=False, ge=0)
    max_rpm: int = Field(ge=0)
    avg_coolant_temp: float = Field(allow_inf_nan=False)
    max_coolant_temp: int
    avg_battery_voltage: float = Field(allow_inf_nan=False, ge=0)
    min_battery_voltage: float = Field(ge=0, allow_inf_nan=False)
    max_battery_voltage: float = Field(ge=0, allow_inf_nan=False)
    avg_engine_load: float = Field(allow_inf_nan=False, ge=0)
    max_engine_load: float = Field(allow_inf_nan=False, ge=0)
    avg_stft1: float = Field(allow_inf_nan=False)
    avg_ltft1: float = Field(allow_inf_nan=False)
    avg_lambda: float = Field(allow_inf_nan=False, ge=0)


class SamplePoint(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, strict=True)
    timestamp: int = Field(ge=0)
    speed: int = Field(ge=0)
    rpm: int = Field(ge=0)
    coolant_temp: int
    battery_voltage: float = Field(allow_inf_nan=False, ge=0)
    engine_load: float = Field(allow_inf_nan=False, ge=0, le=100)
    short_term_fuel_trim_bank1: float = Field(allow_inf_nan=False)
    long_term_fuel_trim_bank1: float = Field(allow_inf_nan=False)
    equivalence_ratio: float = Field(allow_inf_nan=False, ge=0)
    intake_manifold_pressure: float = Field(allow_inf_nan=False, ge=0)
    maf_rate: float = Field(allow_inf_nan=False, ge=0)
    throttle_pos: int = Field(ge=0, le=100, allow_inf_nan=False)


class SampleHighlights(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, strict=True)
    hottest_sample: SamplePoint | None = None
    lowest_voltage_sample: SamplePoint | None = None
    highest_load_sample: SamplePoint | None = None
    highest_stft_sample: SamplePoint | None = None
    representative_cruise_sample: SamplePoint | None = None


class VehicleSourceType(str, Enum):
    REAL = "REAL"
    DEMO = "DEMO"
    REPLAY = "REPLAY"


class PromptHints(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, strict=True, str_strip_whitespace=True
    )
    is_demo_data: bool
    should_avoid_hard_fault_claims: bool
    instruction: str = Field(min_length=1)


class VehicleContext(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, strict=True)
    session_summary: SessionSummary
    sample_highlights: SampleHighlights
    prompt_hints: PromptHints
    source_type: VehicleSourceType = Field(strict=False)
    created_at: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_demo_flag(self) -> Self:
        expected_is_demo = self.source_type == VehicleSourceType.DEMO
        if self.prompt_hints.is_demo_data != expected_is_demo:
            raise ValueError(
                f"Inconsistent demo flag: source_type={self.source_type}, "
                f"prompt_hints.is_demo_data={self.prompt_hints.is_demo_data}"
            )
        return self
