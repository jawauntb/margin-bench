from marginbench.environment.contractors import (
    book_slot,
    earliest_start_day,
    find_slot,
    overtime_start_tick,
    preview_start_tick,
    slot_start_tick,
)

DAY = 1440


def test_earliest_start_day_uses_ceil_of_lead_over_speed():
    assert earliest_start_day(0, 2.0, 0.8) == 3  # ceil(2.5)
    assert earliest_start_day(5 * DAY + 100, 1.5, 1.5) == 6  # ceil(1.0)
    assert earliest_start_day(0, 2.5, 1.0) == 3


def test_capacity_fills_in_order_and_never_bumps():
    sched: dict[int, int] = {}
    starts = [book_slot(sched, 2, 0, 1.0, 1.0) for _ in range(5)]
    # capacity 2: days 1,1,2,2,3; slots 0,1 at 08:00 and 10:00
    assert starts == [1 * DAY + 480, 1 * DAY + 600, 2 * DAY + 480, 2 * DAY + 600, 3 * DAY + 480]
    assert sched == {1: 2, 2: 2, 3: 1}
    assert all(v >= 0 for v in sched.values())


def test_preview_matches_book_and_does_not_mutate():
    sched = {1: 1}
    p = preview_start_tick(sched, 2, 0, 1.0, 1.0)
    assert sched == {1: 1}
    assert p == book_slot(sched, 2, 0, 1.0, 1.0)


def test_unlimited_capacity_never_runs_past_midnight():
    sched: dict[int, int] = {}
    for i in range(20):
        t = book_slot(sched, 0, 0, 1.0, 1.0)
        assert (t % DAY) <= 480 + 120 * 7
    assert slot_start_tick(1, 9) == 2 * DAY + 480 + 120
    assert find_slot({1: 100}, 0, 1) == (1, 100)


def test_overtime_start():
    assert overtime_start_tick(1000, 360, 1.5) == 1000 + 240
    assert overtime_start_tick(1000, 360, 0.8) == 1000 + 450
