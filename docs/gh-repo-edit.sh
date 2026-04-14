#!/usr/bin/env bash
# Draft — DO NOT run blindly. Review then execute from the repo root.
#
# These commands set the public repo description and topics so SmartBaseAI
# shows up in searches and on the GitHub profile card with a crisp pitch.

set -euo pipefail

gh repo edit danrixd/smartbaseai \
  --description "Multi-tenant LLM platform that grounds answers in both your structured databases and your unstructured documents. Hybrid RAG + exact DB lookups + pluggable model backends." \
  --homepage "https://danringart.com" \
  --add-topic llm \
  --add-topic rag \
  --add-topic hybrid-search \
  --add-topic multi-tenant \
  --add-topic fastapi \
  --add-topic python \
  --add-topic react \
  --add-topic chromadb \
  --add-topic sentence-transformers \
  --add-topic ollama
