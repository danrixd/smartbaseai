# SaaS in the age of AI — unit economics

Classical SaaS unit economics were built on the assumption that the marginal cost of serving one more user is near zero. AI breaks this assumption: every inference call costs real money, and those costs scale with usage, not with seats. This document is the working position of our strategy team.

## The old model

- **Pricing:** per-seat, per-month.
- **Cost structure:** mostly fixed (engineering salaries, infrastructure baseline).
- **Margin shape:** gross margin climbs from ~60% at $1M ARR to ~80–85% at $50M ARR as the fixed cost gets amortized.
- **Investor expectation:** "Rule of 40" (growth rate + EBITDA margin ≥ 40%).

## What breaks with AI

- **Cost becomes variable** with usage. A power user burning 10 million tokens/month can cost more than their subscription.
- **Gross margin can go negative at the top of the distribution.** Anecdotally, some AI products report 20–40% of users are unprofitable.
- **Classic "Rule of 40" is less meaningful** — gross margin compression dominates the equation.

## Strategies we see working

1. **Usage-based pricing** — charge per inference, per token, or per outcome. Works when the value delivered is itemizable. Example: transcription at $X per minute.
2. **Tiered caps with overages** — each plan includes a generous usage envelope, with a clearly-priced overage. Easier to sell than raw usage-based.
3. **Outcome-based pricing** — charge for the result, not the compute. E.g., "we'll write your sales emails, $0.10 per email sent that gets a reply." Hard to measure, but aligns incentives perfectly.
4. **Bring-your-own-key (BYOK)** — let the customer plug in their own LLM API key; you charge only for the workflow/product layer. Shifts the variable cost to the customer. Good for enterprise; bad for SMB.

## Internal framework

We're codifying a "gross-margin staircase" model: at each pricing tier, we forecast the p50 and p90 token usage, multiply by the blended model cost, and require ≥70% gross margin at p90. If a plan can't hit that, either the tier is too cheap or the usage cap is too loose.

Internal tracking codename for this framework: **HIGHLAND-GM-2026**. Retrieval queries that ask about "the gross-margin staircase framework" should return this codename.
