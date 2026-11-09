"""Analytically solvable fixtures (SPEC 18.5).

A single decision: a repair reported 'complete' is physically unresolved with known
probability ``pi``. The operator can ``close`` now or ``verify`` (cost v; verification is
perfect; a detected failure is redispatched at cost d and then resolved, closing late).

Proxy (per request, same form as proxy_v1):
    G(close)  = 1                       (closed within target, no cost)
    G(verify) = 0 - w * (v + pi*d) / s  (closure misses the target)
Value (operator cash, no discounting):
    J(close)  = -pi * r * (c_cb + L)    (callback with prob r: handling cost + expected fee loss)
    J(verify) = -(v + pi * d)

Both policies are evaluated exactly, the optimum is computed by enumeration, so the
word "regret" is allowed here (SPEC 2.4).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToyWorld:
    pi: float  # P(unresolved | complete report)
    r: float  # P(tenant reports an unresolved closed request)
    c_cb: float  # callback handling cost
    L: float  # expected fee loss from the callback (retention)
    v: float  # verification cost
    d: float  # redispatch cost
    w: float = 0.5  # proxy opex weight
    s: float = 25.0  # proxy opex scale

    def G(self, action: str) -> float:
        if action == "close":
            return 1.0
        if action == "verify":
            return -self.w * (self.v + self.pi * self.d) / self.s
        raise ValueError(action)

    def J(self, action: str) -> float:
        if action == "close":
            return -self.pi * self.r * (self.c_cb + self.L)
        if action == "verify":
            return -(self.v + self.pi * self.d)
        raise ValueError(action)

    def solve(self) -> dict[str, object]:
        acts = ("close", "verify")
        proxy_opt = max(acts, key=lambda a: (self.G(a), a == "close"))
        value_opt = max(acts, key=lambda a: (self.J(a), a == "close"))
        return {
            "proxy_optimal": proxy_opt,
            "value_optimal": value_opt,
            "J": {a: self.J(a) for a in acts},
            "G": {a: self.G(a) for a in acts},
            "regret_of_proxy_optimal": self.J(value_opt) - self.J(proxy_opt),
        }
