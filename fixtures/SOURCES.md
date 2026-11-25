# Fixture provenance

These three files are byte copies of files published in
`github.com/devops-gm88/rag-eval-demo` at commit `main` on 2026-11-26. They are
committed here so the conformance test never fetches anything at test time.

| Local file | Published path | SHA-256 |
|---|---|---|
| `rag_eval_questions.json` | `evals/questions.json` | `8c9e157d3565221d098159dd508ad7a649e071207749ce2518dd2cd50878f409` |
| `eval_baseline.json` | `reports/eval_baseline.json` | `8e30a8e04324846a236838611777c1f6930d74119cc87e6eb19fb60917db3d36` |
| `eval_improved.json` | `reports/eval_improved.json` | `f53b21bf57776012111b9a1a6e090f53bdae3c0b6c82b38e1f50c4477cfe1d95` |

`tests/test_conformance.py` asserts each digest. Editing a fixture fails the
suite instead of moving the number.

What the fixtures contain: 30 answerable questions and 3 questions that must be
refused, over a 57-document corpus, plus the per-question output of two runs
(fixed chunking + vector retrieval = `baseline`; structural chunking + hybrid
retrieval = `improved`). Each recorded row carries the model answer, the cited
chunk indices, the retrieved sources, and the fact form that was matched inside
the cited chunk.
