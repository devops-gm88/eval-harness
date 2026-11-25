"""The two data shapes: a Case to ask, and a Result to score.

A Case is one thing the system must get right. There are two kinds:

* an answerable case, which names the expected fact and the context ids that
  should be retrieved for it;
* a refusal case (``must_refuse=True``), where the correct behaviour is to
  answer "not in sources" instead of inventing an answer.

A Result is what a runner returned for one Case. The runner is responsible for
the reading of sources and the calling of a model; this library only scores
what came back.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _as_tuple(value) -> tuple[str, ...]:
    """Accept a list or a tuple and store a tuple, so a Case stays hashable."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


@dataclass(frozen=True)
class Case:
    """One question, its expected fact, and whether the right answer is a refusal."""

    id: str
    question: str
    expected: str = ""
    must_refuse: bool = False
    context_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "context_ids", _as_tuple(self.context_ids))
        object.__setattr__(self, "aliases", _as_tuple(self.aliases))
        if not self.id or not str(self.id).strip():
            raise ValueError("a Case needs a non-empty id")
        if not self.question or not str(self.question).strip():
            raise ValueError(f"case {self.id!r} needs a non-empty question")
        if self.must_refuse:
            if self.expected:
                raise ValueError(
                    f"case {self.id!r} is a refusal case and must not carry an expected fact"
                )
        elif not self.expected or not str(self.expected).strip():
            raise ValueError(
                f"case {self.id!r} is answerable, so it needs an expected fact "
                "(set must_refuse=True for a case whose right answer is a refusal)"
            )

    @property
    def fact_forms(self) -> tuple[str, ...]:
        """The expected fact plus its declared surface variants."""
        return (self.expected, *self.aliases)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "expected": self.expected,
            "must_refuse": self.must_refuse,
            "context_ids": list(self.context_ids),
            "aliases": list(self.aliases),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Case":
        return cls(
            id=row["id"],
            question=row["question"],
            expected=row.get("expected") or row.get("key_fact") or "",
            must_refuse=bool(row.get("must_refuse", False)),
            context_ids=row.get("context_ids") or row.get("expected_sources") or (),
            aliases=row.get("aliases") or (),
        )


@dataclass
class Result:
    """What a runner returned for one Case.

    ``cited_texts`` holds the text of every chunk the answer cites. A
    ``cited_fact`` may be supplied instead when a runner records only the fact
    form it matched inside the cited chunk (the published rag-eval-demo reports
    record exactly that). The harness then checks ``cited_fact`` is one of the
    case's declared fact forms, so a fabricated string cannot pass.
    """

    case_id: str
    answer: str = ""
    refused: bool = False
    retrieved_ids: list[str] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    cited_texts: list[str] = field(default_factory=list)
    cited_fact: str | None = None
    invalid_citations: list[int] = field(default_factory=list)

    @classmethod
    def from_runner(cls, case: Case, output) -> "Result":
        if isinstance(output, Result):
            return output
        if output is None:
            output = {}
        if not isinstance(output, dict):
            raise TypeError(
                f"runner returned {type(output).__name__} for case {case.id!r}; "
                "expected a Result or a dict"
            )
        retrieved = output.get("retrieved_ids")
        if retrieved is None:
            retrieved = [
                item.get("id") or item.get("source") if isinstance(item, dict) else item
                for item in output.get("retrieved") or []
            ]
        cited = output.get("cited_ids")
        if cited is None:
            cited = output.get("cited") or []
        return cls(
            case_id=case.id,
            answer=str(output.get("answer") or ""),
            refused=bool(output.get("refused", False)),
            retrieved_ids=[str(item) for item in retrieved],
            cited_ids=[str(item) for item in cited],
            cited_texts=[str(item) for item in output.get("cited_texts") or []],
            cited_fact=output.get("cited_fact"),
            invalid_citations=list(output.get("invalid_citations") or []),
        )

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "answer": self.answer,
            "refused": self.refused,
            "retrieved_ids": list(self.retrieved_ids),
            "cited_ids": list(self.cited_ids),
            "cited_texts": list(self.cited_texts),
            "cited_fact": self.cited_fact,
            "invalid_citations": list(self.invalid_citations),
        }
