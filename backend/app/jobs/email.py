import asyncio
from typing import Any

from app.email.renderer import render_template
from app.email.sender import send_email as deliver_email
from app.jobs.celery_app import celery_app


@celery_app.task(name="project_hub.emails.send")
def send_email(
    recipient: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> None:
    """Render an HTML template and deliver it through SMTP."""
    html_body = render_template(template_name, **context)
    asyncio.run(deliver_email(recipient, subject, html_body))
