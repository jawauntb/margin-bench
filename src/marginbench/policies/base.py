"""Policy protocol (SPEC 9). Isolation is an in-process software contract, not a security
sandbox: policies receive frozen observations and never hold a reference to the engine."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from marginbench.config import PublicConfig
from marginbench.schemas import Action, ObservableEvent, Observation


@runtime_checkable
class Policy(Protocol):
    name: str

    def reset(self, public_config: PublicConfig, estimator: Any, initial_observation: Optional[Observation]) -> None: ...

    def act(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action: ...

    def observe_feedback(self, events: tuple[ObservableEvent, ...]) -> None: ...

    def diagnostics(self) -> dict[str, object]: ...


class BasePolicy:
    name = "base"

    def __init__(self) -> None:
        self.pub: Optional[PublicConfig] = None
        self.estimator: Any = None
        self.n_decisions = 0
        self.n_feedback_events = 0

    def reset(self, public_config: PublicConfig, estimator: Any, initial_observation: Optional[Observation]) -> None:
        self.pub = public_config
        self.estimator = estimator
        self.n_decisions = 0
        self.n_feedback_events = 0

    def observe_feedback(self, events: tuple[ObservableEvent, ...]) -> None:
        self.n_feedback_events += len(events)

    def diagnostics(self) -> dict[str, object]:
        return {"decisions": self.n_decisions, "feedback_events": self.n_feedback_events}
