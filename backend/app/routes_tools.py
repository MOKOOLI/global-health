from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import asr

router = APIRouter(prefix="/api/tools")


class Group(BaseModel):
    cases: float = Field(ge=0)
    pop: float = Field(gt=0)
    weight: float | None = Field(default=None, ge=0)


class AsrIn(BaseModel):
    groups: list[Group] = Field(min_length=2, max_length=30)
    standard: str = "segi"           # segi | who2000 | custom
    per: float = Field(default=100_000, gt=0)
    confidence: float = Field(default=0.95, gt=0.5, lt=1)


@router.get("/standards")
def standards():
    return {k: dict(labels=v[0], weights=v[1], note=(
        "Entered from memory; verify before publishing." if k == "who2000" else "Segi world standard; sums to 100,000."))
        for k, v in asr.STANDARDS.items()}


@router.post("/age-standardise")
def age_standardise(body: AsrIn):
    n = len(body.groups)
    if body.standard == "custom":
        if any(g.weight is None for g in body.groups):
            raise HTTPException(422, "custom standard needs a weight for every age group")
        weights = [g.weight for g in body.groups]  # type: ignore[misc]
    elif body.standard in asr.STANDARDS:
        std = asr.STANDARDS[body.standard][1]
        if n != len(std):
            raise HTTPException(422, f"standard '{body.standard}' has {len(std)} age groups; you sent {n}")
        weights = list(std)
    else:
        raise HTTPException(422, "standard must be segi, who2000 or custom")
    try:
        return asr.standardise([g.cases for g in body.groups], [g.pop for g in body.groups], weights,
                               body.per, body.confidence)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
