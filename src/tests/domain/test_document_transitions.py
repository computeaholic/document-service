import pytest
from datetime import datetime, timezone

from domain.document import Document, Status
from domain.exceptions import IllegalTransitionError, ValidationError


def test_initial_version_is_zero_and_timestamps_match_on_creation() -> None:
    doc = Document(title="Initial", content="Hello")
    assert doc.version == 0
    assert doc.created_at == doc.updated_at


def test_title_validation_on_construction_blank_and_too_long() -> None:
    with pytest.raises(ValidationError):
        Document(title="   ", content="Hello")

    with pytest.raises(ValidationError):
        Document(title="x" * 201, content="Hello")


def test_legal_transitions_and_versioning() -> None:
    doc = Document(title="Initial", content="Hello")
    created_at = doc.created_at
    initial_version = doc.version
    assert initial_version == 0

    # update in draft
    doc.update("Updated", "Hello v2")
    assert doc.title == "Updated"
    assert doc.content == "Hello v2"
    assert doc.status == Status.draft
    assert doc.version == initial_version + 1
    assert doc.updated_at >= created_at

    prev_updated = doc.updated_at

    # submit (requires non-empty content)
    doc.submit()
    assert doc.status == Status.submitted  # type: ignore[comparison-overlap]
    assert doc.version == initial_version + 2
    assert doc.updated_at > prev_updated

    prev_updated = doc.updated_at

    # approve
    doc.approve()
    assert doc.status == Status.approved
    assert doc.version == initial_version + 3
    assert doc.updated_at > prev_updated


def test_reject_from_submitted_and_terminal_protection() -> None:
    doc = Document(title="T", content="Body")
    v0 = doc.version
    doc.submit()
    assert doc.status == Status.submitted
    doc.reject()
    assert doc.status == Status.rejected  # type: ignore[comparison-overlap]
    assert doc.version == v0 + 2

    # terminal: no further mutations allowed
    with pytest.raises(IllegalTransitionError):
        doc.update("x", "y")
    with pytest.raises(IllegalTransitionError):
        doc.submit()
    with pytest.raises(IllegalTransitionError):
        doc.approve()


def test_illegal_transitions_from_wrong_states() -> None:
    d1 = Document(title="a", content="b")
    v0 = d1.version
    t0 = d1.updated_at

    # cannot approve or reject directly from draft
    with pytest.raises(IllegalTransitionError):
        d1.approve()
    assert d1.version == v0
    assert d1.updated_at == t0

    with pytest.raises(IllegalTransitionError):
        d1.reject()
    assert d1.version == v0
    assert d1.updated_at == t0


def test_duplicate_submit_transition_fails_without_bump() -> None:
    doc = Document(title="t", content="ok")
    doc.submit()
    v1 = doc.version
    t1 = doc.updated_at

    with pytest.raises(IllegalTransitionError):
        doc.submit()

    assert doc.version == v1
    assert doc.updated_at == t1


def test_submit_validation_and_no_version_change_on_failure() -> None:
    doc = Document(title="t", content="   ")
    v0 = doc.version
    t0 = doc.updated_at
    with pytest.raises(ValidationError):
        doc.submit()
    # version should not have changed
    assert doc.version == v0
    assert doc.updated_at == t0


def test_title_validation_on_update_and_no_bump_on_failure() -> None:
    doc = Document(title="Valid", content="c")
    v0 = doc.version
    t0 = doc.updated_at

    with pytest.raises(ValidationError):
        doc.update("   ", "new")
    assert doc.version == v0
    assert doc.updated_at == t0

    with pytest.raises(ValidationError):
        doc.update("x" * 201, "new")
    assert doc.version == v0
    assert doc.updated_at == t0


def test_created_at_never_changes_and_updated_at_monotonic() -> None:
    doc = Document(title="s", content="c")
    created = doc.created_at
    first_update_time = doc.updated_at
    doc.update("s2", "c2")
    assert doc.created_at == created
    assert doc.updated_at >= first_update_time


def test_illegal_transition_after_terminal_state_no_bump_and_no_timestamp_change() -> (
    None
):
    doc = Document(title="Term", content="ok")
    doc.submit()
    doc.approve()
    v0 = doc.version
    t0 = doc.updated_at

    with pytest.raises(IllegalTransitionError):
        doc.reject()

    assert doc.version == v0
    assert doc.updated_at == t0


def test_negative_version_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="version must be non-negative"):
        Document(title="Test", content="c", version=-1)


def test_deterministic_clock_initialization_and_mutations() -> None:
    # Fixed clock returning known datetimes
    times = [
        datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),  # creation
        datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc),  # after update
        datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),  # after submit
        datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),  # after approve
    ]
    time_iterator = iter(times)

    def fixed_clock() -> datetime:
        return next(time_iterator)

    doc = Document(title="Test", content="Body", clock=fixed_clock)
    assert doc.created_at == times[0]
    assert doc.updated_at == times[0]
    assert doc.version == 0

    doc.update("Updated", "Body2")
    assert doc.updated_at == times[1]
    assert doc.version == 1

    doc.submit()
    assert doc.updated_at == times[2]
    assert doc.version == 2

    doc.approve()
    assert doc.updated_at == times[3]
    assert doc.version == 3


def test_deterministic_clock_ensures_created_at_equals_updated_at_on_creation() -> None:
    fixed_time = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)

    def fixed_clock() -> datetime:
        return fixed_time

    doc = Document(title="T", content="C", clock=fixed_clock)
    assert doc.created_at == fixed_time
    assert doc.updated_at == fixed_time
    assert doc.created_at == doc.updated_at
