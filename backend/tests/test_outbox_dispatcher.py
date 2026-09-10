from app.jobs.outbox_dispatcher import dispatch_pending_events
from app.repositories.outbox import OutboxRepository


def test_dispatch_pending_events_publishes_welcome_email_and_marks_event_sent(
    db_session, email_task_delay
):
    outbox_repo = OutboxRepository(db_session)
    event = outbox_repo.add_event(
        "user.registered",
        {"email": "sam@example.com", "username": "sam"},
    )
    db_session.commit()

    dispatched_events = dispatch_pending_events(db_session)

    assert dispatched_events == 1
    assert event.sent is True
    email_task_delay.assert_called_once_with(
        "sam@example.com", "Welcome!", "welcome.html", {"username": "sam"}
    )


def test_dispatch_pending_events_skips_already_sent_events(db_session, email_task_delay):
    outbox_repo = OutboxRepository(db_session)
    event = outbox_repo.add_event(
        "user.registered",
        {"email": "sam@example.com", "username": "sam"},
    )
    event.sent = True
    db_session.commit()

    dispatched_events = dispatch_pending_events(db_session)

    assert dispatched_events == 0
    email_task_delay.assert_not_called()
