"""Reconciliation catches every SPEC 6.5 failure class."""

import dataclasses

from marginbench.economics.reconciliation import reconcile, replay_entries
from marginbench.schemas import EntryStatus, LedgerEntry, Principal
from helpers import run_p0, small_cfg

CFG = small_cfg()


def setup():
    eng, out, _ = run_p0(CFG)
    cids = sorted(out.contracts)
    cp = {k: v.property_id for k, v in out.contracts.items()}
    return eng, out, cids, cp


def rec(out, entries, eng, cids, cp):
    return {e["check"] for e in reconcile(out.events, entries, CFG, out.run_id, cids, cp, eng.end_tick)}


def test_clean_run_reconciles_and_replays():
    eng, out, cids, cp = setup()
    assert rec(out, out.ledger.entries, eng, cids, cp) == set()
    rep = replay_entries(out.events, CFG, out.run_id, cids, cp)
    assert [e.to_record() for e in rep] == [e.to_record() for e in out.ledger.entries]


def test_duplicate_entry_detected():
    eng, out, cids, cp = setup()
    entries = list(out.ledger.entries) + [out.ledger.entries[0]]
    assert "duplicate_entry_id" in rec(out, entries, eng, cids, cp)


def test_entry_without_trigger_detected():
    eng, out, cids, cp = setup()
    bad = dataclasses.replace(out.ledger.entries[0], event_id=10**9)
    assert "no_valid_trigger" in rec(out, [bad] + list(out.ledger.entries[1:]), eng, cids, cp)


def test_payer_misattribution_detected():
    eng, out, cids, cp = setup()
    idx = next(i for i, e in enumerate(out.ledger.entries) if e.category == "dispatch_expense")
    entries = list(out.ledger.entries)
    entries[idx] = dataclasses.replace(entries[idx], principal=Principal.OWNER)
    assert "payer_misattribution" in rec(out, entries, eng, cids, cp)


def test_fee_on_inactive_contract_detected():
    eng, out, cids, cp = setup()
    from marginbench.schemas import Event, make_data
    term = Event(10**8, 0, 0, "CONTRACT_TERMINATED", None, cp[cids[0]], make_data(contract_id=cids[0], day=0))
    events = [out.events[0], term] + list(out.events[1:])
    checks = {e["check"] for e in reconcile(events, out.ledger.entries, CFG, out.run_id, cids, cp, eng.end_tick)}
    assert "fee_on_inactive_contract" in checks


def test_pending_recorded_as_realized_detected():
    eng, out, cids, cp = setup()
    entries = list(out.ledger.entries)
    idx = next(i for i, e in enumerate(entries) if e.category == "fee_revenue")
    entries[idx] = dataclasses.replace(entries[idx], status=EntryStatus.REALIZED)
    assert "fee_status" in rec(out, entries, eng, cids, cp)
    late = dataclasses.replace(out.ledger.entries[-1], tick=eng.end_tick + 5)
    assert "pending_recorded_as_realized" in rec(out, list(out.ledger.entries[:-1]) + [late], eng, cids, cp)


def test_principal_totals_mismatch_detected():
    eng, out, cids, cp = setup()
    entries = list(out.ledger.entries)
    entries[0] = dataclasses.replace(entries[0], amount_cents=entries[0].amount_cents + 1)
    got = rec(out, entries, eng, cids, cp)
    assert "event_derived_mismatch" in got and "principal_totals" in got


def test_no_tenant_rent_and_categories_have_known_payers():
    _, out, _, _ = setup()
    for e in out.ledger.entries:
        assert e.principal != Principal.TENANT
        if e.category == "fee_revenue":
            assert e.principal == Principal.OPERATOR and e.amount_cents > 0
        if e.category == "repair_invoice":
            assert e.principal == Principal.OWNER and e.amount_cents < 0
