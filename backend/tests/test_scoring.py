from app.modules.ratings.scoring import CompanyStats, compute_score


def stats(**overrides: int) -> CompanyStats:
    values = dict(
        issues_total=10,
        resolved=0,
        rejected=0,
        no_response=0,
        overdue_now=0,
        on_time=0,
        escalated=0,
    )
    return CompanyStats(**(values | overrides))


def test_no_issues_has_no_score():
    assert compute_score(stats(issues_total=0)) is None


def test_few_issues_have_no_score():
    assert compute_score(stats(issues_total=2, resolved=2, on_time=2)) is None


def test_no_outcomes_yet_has_no_score():
    assert compute_score(stats()) is None


def test_everything_resolved_on_time_is_perfect():
    assert compute_score(stats(resolved=10, on_time=10)) == 100


def test_everything_overdue_and_escalated_is_zero():
    assert compute_score(stats(overdue_now=10, escalated=10)) == 0


def test_score_follows_formula():
    # решено 5 из 10, в срок 3 из 10, эскалаций 2 из 10: 100 × (0.25 + 0.09 + 0.16)
    assert compute_score(stats(resolved=5, no_response=5, on_time=3, escalated=2)) == 50
