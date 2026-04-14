# Pulse — Product Specification

Pulse is Acme Analytics' real-time market data aggregator. It normalizes raw order-book snapshots from multiple exchanges into a unified schema and publishes them over a low-latency gRPC stream.

## Supported venues

Pulse currently ingests from 11 venues: CME, Eurex, LSE, NYSE, NASDAQ, TSE, HKEX, SGX, ICE, BME, and ASX. Adding a new venue typically takes 3 weeks of engineering work including conformance tests.

## Latency guarantees

- P50 end-to-end latency: **4.2 ms**
- P99 end-to-end latency: **11.8 ms**
- Delivery guarantee: at-least-once, with client-side de-duplication by sequence number.

## Schema

Every tick is published as a `MarketTick` message with the following fields:

- `symbol` — venue-qualified ticker, e.g. `NASDAQ:AAPL`
- `timestamp` — nanosecond epoch
- `bid_price`, `bid_size`, `ask_price`, `ask_size`
- `trade_price`, `trade_size`, `trade_side`
- `sequence` — monotonic per-symbol sequence number

## Retention

Pulse retains 90 days of raw ticks in hot storage and 2 years in cold S3-compatible object storage. Clients can replay any 90-day window at up to 10× wall-clock speed.
