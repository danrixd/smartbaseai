# Pricing playbook for AI-native SaaS

A short field guide for setting prices on a product where model costs are a first-class line item.

## Step 1 — Measure actual usage, not guessed usage

Before pricing anything, instrument tokens-in, tokens-out, and compute seconds for every call, tagged by tenant and by feature. Don't trust dashboards from the model vendor — build your own.

## Step 2 — Pick the billing atom

The billing atom is the unit your customer understands and accepts being charged for. Candidates:
- per seat (classic)
- per workflow run
- per document processed
- per API call
- per successful outcome (e.g., per reply received)

**The best atom is the smallest unit the customer already counts.** If an operations team counts "tickets resolved," charge per ticket. If a marketing team counts "campaigns shipped," charge per campaign.

## Step 3 — Build a three-tier menu

The classic three-tier SaaS menu still works. For AI:

- **Starter** — generous free tier with a low usage cap. Customer acquisition cost.
- **Pro** — the "good price" tier. Designed to be profitable at p50 usage; loss-leader at the p99. Most customers land here.
- **Enterprise** — bespoke terms, often BYOK or dedicated capacity, SLA, and custom data-retention terms.

## Step 4 — Protect the gross margin explicitly

- Hard cap on the Pro plan at a number your finance team approves.
- Soft cap with automatic overage billing, communicated clearly at signup.
- Automatic model routing: route low-complexity queries to cheaper models, reserve the expensive model for when it's needed. A good router can cut model cost by 40–60% without any drop in user-perceived quality.

## Step 5 — Communicate in dollars the customer understands

"$29 / month / user" is legible. "$0.0015 per thousand tokens" is not. Even if the backend is usage-based, the customer-facing number should be something a CFO can forecast. Usage-based pricing that fails the CFO-forecasting test burns adoption in the enterprise segment.

## Anti-patterns

- **Per-seat pricing on an AI product where the work is automated.** The customer's seat count goes to zero; your revenue goes with it.
- **Unlimited usage tiers on a hosted-model product.** A small number of heavy users will destroy your gross margin. Always have a cap.
- **Hiding the model costs in a "platform fee".** Enterprise buyers will demand the breakdown, and if you can't produce it, you'll lose the deal.
