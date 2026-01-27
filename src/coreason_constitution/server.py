from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

import coreason_constitution
from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import ConstitutionalTrace
from coreason_constitution.sentinel import Sentinel
from coreason_constitution.simulation import SimulatedLLMClient
from coreason_constitution.utils.logger import logger


class ComplianceRequest(BaseModel):
    input_prompt: str
    draft_response: str
    context_tags: Optional[List[str]] = None
    max_retries: int = 3


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize components
    logger.info("Initializing Constitutional System...")
    archive = LegislativeArchive()
    archive.load_defaults()

    sentinel = Sentinel(archive.get_sentinel_rules())

    llm_client = SimulatedLLMClient()
    judge = ConstitutionalJudge(llm_client)
    revision_engine = RevisionEngine(llm_client)

    system = ConstitutionalSystem(archive, sentinel, judge, revision_engine)

    app.state.system = system
    yield
    logger.info("Shutting down Constitutional System...")


app = FastAPI(lifespan=lifespan, title="CoReason Constitution Governance API")


@app.get("/health")
async def health():
    return {"status": "ready", "version": coreason_constitution.__version__}


@app.get("/laws")
async def get_laws(request: Request):
    system: ConstitutionalSystem = request.app.state.system
    return system.archive.get_laws()


@app.post("/govern/sentinel")
async def sentinel_check(request: Request, payload: dict):
    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Content required")

    system: ConstitutionalSystem = request.app.state.system
    try:
        system.sentinel.check(content)
        return {"status": "allowed"}
    except SecurityException as e:
        # Sentinel raises SecurityException for blocked content
        # We return 403 Forbidden with details
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/govern/compliance-cycle", response_model=ConstitutionalTrace)
async def run_compliance_cycle(request: Request, body: ComplianceRequest):
    system: ConstitutionalSystem = request.app.state.system
    trace = system.run_compliance_cycle(
        input_prompt=body.input_prompt,
        draft_response=body.draft_response,
        context_tags=body.context_tags,
        max_retries=body.max_retries,
    )
    return trace
