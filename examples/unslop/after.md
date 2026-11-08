# Webhook retries

Paid orders sometimes got no ticket when the Razorpay webhook failed once. Ticket issuing now runs in a Celery task that retries 5 times over about 30 minutes.

- `issue_ticket` is idempotent on `payment_id`, so a retry can't create a second ticket.
- After the last failed retry, the order id goes to `#payments-alerts`.
- Behind `RETRY_WEBHOOKS`. Off runs the old inline path.

To check: replay a webhook with the worker stopped, start it, and confirm one ticket and no alert.
