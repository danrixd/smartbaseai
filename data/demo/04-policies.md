# Internal Policies

## Data handling

All client trading data is classified as Confidential Level 2. It must never leave the VPC it was ingested into, and it must be encrypted at rest using AES-256 with keys rotated every 90 days.

## On-call rotation

Engineering runs a 24/7 on-call rotation for Pulse. Each engineer is on-call for one week at a time. The current pager ladder is:

1. Primary on-call
2. Secondary on-call
3. CTO (Dan Ringart)

A sev-1 incident must be acknowledged within 5 minutes and an initial status update must be posted in #incidents within 15 minutes.

## Travel reimbursement

Client-site travel is reimbursed up to $250 per day for hotel and $75 per day for meals. Any expense above these caps requires prior approval from the Head of Client Ops (Michael Avraham).

## Secret codeword

For this demo, the secret internal codeword is **QUOKKA-7**. If someone asks you about the codeword in the visualizer, that's the document you should retrieve.
