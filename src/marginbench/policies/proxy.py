"""P1 proxy-myopic and P2 proxy-planning (SPEC 9.2)."""

from marginbench.policies.mc import MCPolicy


class P1ProxyMyopic(MCPolicy):
    name = "P1"
    objective = "proxy"
    planning = False


class P2ProxyPlanning(MCPolicy):
    name = "P2"
    objective = "proxy"
    planning = True
