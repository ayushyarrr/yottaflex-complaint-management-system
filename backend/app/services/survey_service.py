
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Complaint, Resolution, Survey
from backend.app.schemas.survey import SurveyCreate


def get_current_time():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def submit_survey(
    db: Session,
    complaint_id: str,
    payload: SurveyCreate,
):
    try:
        # 1. Verify that the complaint exists.
        complaint = (
            db.query(Complaint)
            .filter(Complaint.complaint_id == complaint_id)
            .first()
        )

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found.",
            )

        # 2. Surveys are accepted only after closure.
        if complaint.status != "CLOSED":
            raise HTTPException(
                status_code=409,
                detail="A survey can only be submitted after the complaint is closed.",
            )

        # 3. Verify that the resolution exists and belongs
        # to this complaint.
        resolution = (
            db.query(Resolution)
            .filter(
                Resolution.resolution_id == payload.resolution_id,
                Resolution.complaint_id == complaint_id,
            )
            .first()
        )

        if not resolution:
            raise HTTPException(
                status_code=404,
                detail="Resolution not found for this complaint.",
            )

        # 4. Only the final resolution can receive a survey.
        if not resolution.is_final:
            raise HTTPException(
                status_code=409,
                detail="A survey can only be submitted for the final resolution.",
            )

        # 5. Prevent duplicate surveys.
        existing_survey = (
            db.query(Survey)
            .filter(Survey.resolution_id == resolution.resolution_id)
            .first()
        )

        if existing_survey:
            raise HTTPException(
                status_code=409,
                detail="A survey has already been submitted for this resolution.",
            )

        # 6. Create the survey.
        survey = Survey(
            resolution_id=resolution.resolution_id,
            complaint_id=complaint_id,
            rating=payload.rating,
            feedback=payload.feedback,
            submitted_at=get_current_time(),
        )

        db.add(survey)
        db.flush()

        # 7. Record the submission in the complaint event history.
        from backend.app.models import ComplaintEvent

        event = ComplaintEvent(
            complaint_id=complaint_id,
            event_type="SURVEY_SUBMITTED",
            old_value=None,
            new_value=str(survey.survey_id),
            description=(
                f"Customer satisfaction survey submitted "
                f"with rating {survey.rating}/5."
            ),
            performed_by="CUSTOMER",
        )

        db.add(event)
        db.commit()
        db.refresh(survey)

        return survey

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A survey already exists for this resolution.",
        )

    except Exception:
        db.rollback()
        raise
