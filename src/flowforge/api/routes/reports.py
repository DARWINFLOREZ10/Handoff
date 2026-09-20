from __future__ import annotations

from fastapi import APIRouter

from flowforge.api.schemas import MessageResponse, ReportSummaryResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/executions-per-day", response_model=ReportSummaryResponse)
async def executions_per_day() -> ReportSummaryResponse:
    return ReportSummaryResponse(
        executions_count=0,
        success_count=0,
        failure_count=0,
        average_duration_ms=0,
        exported_format="json",
    )


@router.get("/success-error-rate", response_model=ReportSummaryResponse)
async def success_error_rate() -> ReportSummaryResponse:
    return ReportSummaryResponse(
        executions_count=0,
        success_count=0,
        failure_count=0,
        average_duration_ms=0,
        exported_format="json",
    )


@router.get("/average-execution-time", response_model=ReportSummaryResponse)
async def average_execution_time() -> ReportSummaryResponse:
    return ReportSummaryResponse(
        executions_count=0,
        success_count=0,
        failure_count=0,
        average_duration_ms=0,
        exported_format="json",
    )


@router.get("/usage-by-organization", response_model=ReportSummaryResponse)
async def usage_by_organization() -> ReportSummaryResponse:
    return ReportSummaryResponse(
        executions_count=0,
        success_count=0,
        failure_count=0,
        average_duration_ms=0,
        exported_format="json",
    )


@router.get("/export/json", response_model=MessageResponse)
async def export_json() -> MessageResponse:
    return MessageResponse(detail="JSON report export generated.")


@router.get("/export/csv", response_model=MessageResponse)
async def export_csv() -> MessageResponse:
    return MessageResponse(detail="CSV report export generated.")
