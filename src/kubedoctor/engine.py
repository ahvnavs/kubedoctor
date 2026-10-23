"""Composable orchestration for deterministic and optional diagnosis stages."""

from dataclasses import dataclass, field
from typing import Any, Callable

from .diagnose import diagnose_all
from .enrich import EnrichmentError, add_llm_explanations, add_prometheus_context
from .models import Diagnosis


@dataclass(frozen=True, slots=True)
class StageStatus:
    name: str
    state: str
    detail: str


@dataclass(slots=True)
class EngineReport:
    diagnoses: list[Diagnosis]
    stages: list[StageStatus] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        return [stage.detail for stage in self.stages if stage.state == "degraded"]


class DiagnosisEngine:
    """Runs isolated stages while keeping rules authoritative."""

    def __init__(
        self,
        prometheus_url: str | None = None,
        explain: bool = False,
        metrics_stage: Callable[[list[Diagnosis], str], list[Diagnosis]] = add_prometheus_context,
        explanation_stage: Callable[[list[Diagnosis]], list[Diagnosis]] = add_llm_explanations,
    ) -> None:
        self.prometheus_url = prometheus_url
        self.explain = explain
        self.metrics_stage = metrics_stage
        self.explanation_stage = explanation_stage

    def run(self, snapshots: list[dict[str, Any]]) -> EngineReport:
        diagnoses = diagnose_all(snapshots)
        stages = [StageStatus("rules", "ready", f"{len(diagnoses)} diagnoses")]
        if self.prometheus_url:
            try:
                diagnoses = self.metrics_stage(diagnoses, self.prometheus_url)
                stages.append(StageStatus("prometheus", "ready", "resource context added"))
            except EnrichmentError as exc:
                stages.append(StageStatus("prometheus", "degraded", f"Prometheus skipped: {exc}"))
        else:
            stages.append(StageStatus("prometheus", "disabled", "enable with --prometheus-url"))
        if self.explain:
            try:
                diagnoses = self.explanation_stage(diagnoses)
                stages.append(StageStatus("explanation", "ready", "plain-language context added"))
            except EnrichmentError as exc:
                stages.append(StageStatus("explanation", "degraded", f"LLM skipped: {exc}"))
        else:
            stages.append(StageStatus("explanation", "disabled", "enable with --explain"))
        unsafe = [item.code for item in diagnoses if not item.fix_command.startswith("kubectl ")]
        if unsafe:
            raise RuntimeError(f"unsafe command emitted by: {', '.join(unsafe)}")
        stages.append(StageStatus("command-guard", "ready", "all commands are explicit kubectl operations"))
        return EngineReport(diagnoses, stages)
