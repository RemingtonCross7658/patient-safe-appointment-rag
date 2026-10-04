"""FastAPI boundary for the appointment notification workflow."""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from openai import APIConnectionError, APIError, APIStatusError, RateLimitError

from healthtech_workflow import (
    DEFAULT_POLICIES,
    AppointmentChange,
    AppointmentNotificationWorkflow,
    InfraiAI,
    NotificationResult,
)

app = FastAPI(title="Patient-safe appointment notifications")


@lru_cache
def get_workflow() -> AppointmentNotificationWorkflow:
    return AppointmentNotificationWorkflow(
        InfraiAI(api_key=os.environ["INFRAI_API_KEY"]),
        DEFAULT_POLICIES,
    )


@app.post("/appointment-notifications", response_model=NotificationResult)
def create_notification(
    change: AppointmentChange,
    workflow: AppointmentNotificationWorkflow = Depends(get_workflow),
) -> NotificationResult:
    try:
        return workflow.notify(change)
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail="Please retry shortly") from exc
    except APIStatusError as exc:
        if 400 <= exc.status_code < 500:
            raise HTTPException(
                status_code=exc.status_code,
                detail=f"Request rejected: {exc.message}",
            ) from exc
        raise HTTPException(status_code=502, detail="Notification drafting was interrupted") from exc
    except (APIConnectionError, APIError) as exc:
        raise HTTPException(status_code=502, detail="Notification drafting was interrupted") from exc
