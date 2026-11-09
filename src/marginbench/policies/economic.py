"""P3 economic-myopic and P4 economic-planning (SPEC 9.2)."""

from marginbench.policies.mc import MCPolicy


class P3EconomicMyopic(MCPolicy):
    name = "P3"
    objective = "econ"
    planning = False


class P4EconomicPlanning(MCPolicy):
    name = "P4"
    objective = "econ"
    planning = True
