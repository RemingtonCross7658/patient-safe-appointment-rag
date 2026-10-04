from collections.abc import Sequence

from healthtech_workflow import (
    AppointmentChange,
    AppointmentNotificationWorkflow,
    PolicyDocument,
)


class RecordingAI:
    def __init__(self) -> None:
        self.system_prompt = ""
        self.user_prompt = ""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = {
            "Rescheduling guidance": [1.0, 0.0],
            "Cancellation guidance": [0.0, 1.0],
        }
        return [vectors.get(text, [0.0, 1.0]) for text in texts]

    def draft(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return "Maya, appointment APT-2048 was cancelled. Call +1-555-0100."


def test_cancellation_retrieves_policy_without_forwarding_visit_reason() -> None:
    ai = RecordingAI()
    workflow = AppointmentNotificationWorkflow(
        ai,
        [
            PolicyDocument("reschedule", "Rescheduling guidance"),
            PolicyDocument("cancel", "Cancellation guidance"),
        ],
    )

    result = workflow.notify(
        AppointmentChange(
            appointment_id="APT-2048",
            patient_first_name="Maya",
            action="cancelled",
            starts_at="2026-09-08T14:30:00-04:00",
            clinic_name="Harbor Clinic",
            reply_phone="+1-555-0100",
            visit_reason="cardiology follow-up",
        )
    )

    assert result.policy_id == "cancel"
    assert result.action == "cancelled"
    assert "Cancellation guidance" in ai.user_prompt
    assert "cardiology" not in ai.user_prompt
    assert "visit reason" in ai.system_prompt.lower()

