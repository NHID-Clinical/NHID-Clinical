# Specification RAG

`src/nhid_spec_rag.py` answers questions from the Markdown in `docs/`. It is a reading aid for the NHID-Clinical specification. It is not the policy engine, not a conformance result, and not a certification.

Mount the router on the existing FastAPI app:

```python
from src.nhid_spec_rag import router as spec_rag_router
app.include_router(spec_rag_router)
```

Build the index from the repository root:

```bash
python -m src.nhid_spec_rag
```

`GET /spec/health` returns the chunk count. `POST /spec/ask` accepts `{"question": "What does PDX-01 require?"}` and returns an answer plus source paths. Without `OPENAI_API_KEY` the index uses a local hash so the route still runs. Set the key and rebuild before publishing a hit rate.

Files larger than 200 KB are skipped so the archive dump is not treated as the specification.
