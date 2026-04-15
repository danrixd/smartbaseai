# Frequently Asked Questions

## What does Acme Analytics do?

We build real-time market analytics tools for mid-sized quantitative trading desks. Our three products are Pulse (market data), Atlas (backtesting), and Signal (alpha research).

## How many venues does Pulse support?

Pulse currently ingests from 11 venues: CME, Eurex, LSE, NYSE, NASDAQ, TSE, HKEX, SGX, ICE, BME, and ASX.

## How accurate is the Atlas slippage model?

On out-of-sample 2024 data, predicted fill prices are within 2.3 basis points of actual fills on average. The model was calibrated on 6 years of tick data from 2018 to 2023.

## Who is the CTO?

Dan Ringart, formerly a research physicist at Tel Aviv University.

## What are the latency guarantees for Pulse?

P50 end-to-end latency is 4.2 ms and P99 is 11.8 ms.

## How long is client trading data retained?

Pulse retains 90 days of raw ticks in hot storage and 2 years in cold object storage.
