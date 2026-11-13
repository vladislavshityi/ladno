from datetime import datetime, timedelta

import pytest

from app.modules.issues.deadlines import add_deadline, is_overdue

FRI = datetime(2026, 11, 13, 10, 0)  # пятница


def test_calendar():
    assert add_deadline(FRI, 30, "calendar") == FRI + timedelta(days=30)
    assert add_deadline(FRI, 0, "calendar") == FRI


def test_working_skips_weekend():
    assert add_deadline(FRI, 1, "working") == datetime(2026, 11, 16, 10, 0)  # пн
    assert add_deadline(FRI, 5, "working") == datetime(2026, 11, 20, 10, 0)  # пт
    assert add_deadline(FRI, 10, "working") == datetime(2026, 11, 27, 10, 0)


def test_working_from_weekend():
    sat = datetime(2026, 11, 14, 9, 0)
    assert add_deadline(sat, 1, "working") == datetime(2026, 11, 16, 9, 0)
    assert add_deadline(sat, 0, "working") == sat


def test_bad_type():
    with pytest.raises(ValueError):
        add_deadline(FRI, 1, "other")


def test_is_overdue():
    dl = datetime(2026, 11, 20)
    after, before = dl + timedelta(seconds=1), dl - timedelta(seconds=1)
    assert is_overdue(after, dl, "submitted")
    assert is_overdue(after, dl, "in_progress")
    assert not is_overdue(before, dl, "submitted")
    assert not is_overdue(dl, dl, "submitted")
    for st in ("draft", "resolved", "no_response", "rejected"):
        assert not is_overdue(after, dl, st)
    assert not is_overdue(after, None, "submitted")
