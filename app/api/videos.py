from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import require_bearer_token
from app.deps import get_job_service
from app.schemas.job import CreateJobRequest, JobResponse
from app.services.job_service import (
    JobNotCancellableError,
    JobNotFoundError,
    JobService,
)

router = APIRouter(
    prefix="/api/videos",
    tags=["videos"],
    dependencies=[Depends(require_bearer_token)],
)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def create_video(
    req: CreateJobRequest,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    job = await service.create_job(req)
    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_video(
    job_id: int,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.get_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", response_model=JobResponse)
async def cancel_video(
    job_id: int,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.cancel_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except JobNotCancellableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return JobResponse.model_validate(job)
