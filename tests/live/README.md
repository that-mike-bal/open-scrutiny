# Live tests

Tests in this folder hit a **running backend with real credentials** and real model calls. They are excluded from the default `pytest` run (see `pytest.ini`) and from CI.

```bash
# backend running on :8000 with a populated .env
pytest tests/live -q
```
