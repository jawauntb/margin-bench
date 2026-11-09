from marginbench.environment.events import PRIORITY, EventQueue, Scheduled


def test_queue_orders_by_tick_priority_event_id():
    q = EventQueue()
    q.push(Scheduled(10, PRIORITY["ARRIVAL"], 1, "ARRIVAL"))
    q.push(Scheduled(10, PRIORITY["DAY_START"], 5, "DAY_START"))
    q.push(Scheduled(5, PRIORITY["CALLBACK"], 9, "CALLBACK"))
    q.push(Scheduled(10, PRIORITY["DAY_START"], 2, "DAY_START"))
    got = [(q.pop().event_id) for _ in range(4)]
    assert got == [9, 2, 5, 1]


def test_work_start_precedes_sla_check_at_same_tick():
    assert PRIORITY["WORK_START"] < PRIORITY["SLA_CHECK"]
    assert PRIORITY["DAY_START"] == min(PRIORITY.values())


def test_engine_event_log_ticks_monotone():
    from helpers import run_p0, small_cfg

    _, out, _ = run_p0(small_cfg())
    ticks = [e.tick for e in out.events]
    assert ticks == sorted(ticks)
    ids = [e.event_id for e in out.events]
    assert len(ids) == len(set(ids))
