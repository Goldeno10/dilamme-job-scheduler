from app.handlers.email import handle_send_email
from app.handlers.webhook import handle_webhook

HANDLERS = {
    "send_email": handle_send_email,
    "webhook": handle_webhook,
    "generate_report": handle_send_email,  # DAG workflow step — simulates report gen
    "upload_file": handle_send_email,
}
