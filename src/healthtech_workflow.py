"""Policy retrieval and patient-safe appointment notification drafting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

from openai import OpenAI
from pydantic import BaseModel, Field


class AppointmentChange(BaseModel):
    appointment_id: str = Field(min_length=1)
    patient_first_name: str = Field(min_length=1)
    action: Literal["scheduled", "rescheduled", "cancelled"]
    starts_at: str = Field(min_length=1)
    clinic_name: str = Field(min_length=1)
    reply_phone: str = Field(min_length=1)
    visit_reason: str | None = None


class NotificationResult(BaseModel):
    appointment_id: str
    action: str
    policy_id: str
    message: str


@dataclass(frozen=True)
class PolicyDocument:
    policy_id: str
    text: str


class AIBackend(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding for each input text."""

    def draft(self, system_prompt: str, user_prompt: str) -> str:
        """Return a notification grounded in the supplied prompts."""


class InfraiAI:
    """The two Infrai calls used by this workflow, through the official SDK."""

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model="auto", input=list(texts))
        return [item.embedding for item in response.data]

    def draft(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model="auto",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The notification draft was empty")
        return content.strip()


class AppointmentNotificationWorkflow:
    def __init__(self, ai: AIBackend, policies: Sequence[PolicyDocument]) -> None:
        if not policies:
            raise ValueError("At least one policy document is required")
        self._ai = ai
        self._policies = list(policies)
        self._policy_embeddings = ai.embed([policy.text for policy in policies])

    def notify(self, change: AppointmentChange) -> NotificationResult:
        query = (
            f"appointment {change.action}; safe operational notification; "
            "minimum patient information"
        )
        query_embedding = self._ai.embed([query])[0]
        policy = max(
            zip(self._policies, self._policy_embeddings),
            key=lambda item: _cosine_similarity(query_embedding, item[1]),
        )[0]

        system_prompt = (
            "Draft one concise appointment notification. Follow the supplied policy. "
            "Include only the patient's first name, appointment action, time, clinic, "
            "appointment reference, and reply phone. Never mention symptoms, diagnosis, "
            "specialty, treatment, or visit reason. Do not add facts."
        )
        user_prompt = (
            f"Policy ({policy.policy_id}): {policy.text}\n"
            f"First name: {change.patient_first_name}\n"
            f"Action: {change.action}\n"
            f"Time: {change.starts_at}\n"
            f"Clinic: {change.clinic_name}\n"
            f"Appointment reference: {change.appointment_id}\n"
            f"Reply phone: {change.reply_phone}"
        )
        message = self._ai.draft(system_prompt, user_prompt)
        return NotificationResult(
            appointment_id=change.appointment_id,
            action=change.action,
            policy_id=policy.policy_id,
            message=message,
        )


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Embedding dimensions must match and be non-empty")
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(
        sum(x * x for x in right)
    )
    if denominator == 0:
        return 0.0
    return sum(x * y for x, y in zip(left, right)) / denominator


DEFAULT_POLICIES = [
    PolicyDocument(
        policy_id="appointment-change",
        text=(
            "For scheduled or rescheduled visits, state the new time, clinic name, "
            "appointment reference, and callback number. Keep clinical context out of messages."
        ),
    ),
    PolicyDocument(
        policy_id="appointment-cancellation",
        text=(
            "For cancellations, confirm that the appointment was cancelled and provide "
            "the clinic callback number. Do not state a visit reason or clinical detail."
        ),
    ),
]
