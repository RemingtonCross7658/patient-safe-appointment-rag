"""Run one appointment cancellation through retrieval and notification drafting."""

import os

from healthtech_workflow import (
    DEFAULT_POLICIES,
    AppointmentChange,
    AppointmentNotificationWorkflow,
    InfraiAI,
)


def main() -> None:
    workflow = AppointmentNotificationWorkflow(
        InfraiAI(api_key=os.environ["INFRAI_API_KEY"]),
        DEFAULT_POLICIES,
    )
    result = workflow.notify(
        AppointmentChange(
            appointment_id="APT-2048",
            patient_first_name="Maya",
            action="cancelled",
            starts_at="2026-09-08T14:30:00-04:00",
            clinic_name="Harbor Clinic",
            reply_phone="+1-555-0100",
            visit_reason="private intake detail excluded from the notification",
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

