import json
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, AdmissionForm, FormStatus
from backend.api.routes.forms import apply_form_filters
from backend.api.routes.export import EXPORT_FIELDS, form_to_csv_row, form_to_json_dict


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def create_form(session, **overrides):
    defaults = {
        "filename": overrides.pop("filename", "sample.pdf"),
        "file_path": overrides.pop("file_path", "uploads/sample.pdf"),
        "upload_date": overrides.pop("upload_date", datetime(2025, 1, 1, 10, 0, 0)),
        "ocr_provider": overrides.pop("ocr_provider", "tesseract"),
        "status": overrides.pop("status", FormStatus.VERIFIED),
        "student_name": overrides.pop("student_name", "Test Student"),
        "course_applied": overrides.pop("course_applied", "B.Com"),
        "enrollment_number": overrides.pop("enrollment_number", "ENR001"),
    }
    form = AdmissionForm(**defaults, **overrides)
    session.add(form)
    session.commit()
    return form


def test_apply_form_filters_by_name(session):
    create_form(session, student_name="Alice Johnson")
    create_form(session, student_name="Bob Smith")

    query = session.query(AdmissionForm)
    filtered = apply_form_filters(query, student_name="alice")

    assert filtered.count() == 1
    assert filtered.first().student_name == "Alice Johnson"


def test_apply_form_filters_by_date_range(session):
    create_form(session, student_name="April Form", upload_date=datetime(2025, 4, 10, 9, 30))
    create_form(session, student_name="May Form", upload_date=datetime(2025, 5, 5, 14, 0))

    query = session.query(AdmissionForm)
    filtered = apply_form_filters(
        query,
        date_from=datetime(2025, 4, 1),
        date_to=datetime(2025, 4, 30),
    )

    results = filtered.all()
    assert len(results) == 1
    assert results[0].student_name == "April Form"


def test_apply_form_filters_by_status_and_course(session):
    create_form(session, student_name="Pending Form", status=FormStatus.EXTRACTED, course_applied="BBA")
    create_form(session, student_name="Verified Form", status=FormStatus.VERIFIED, course_applied="BSC")

    query = session.query(AdmissionForm)
    filtered = apply_form_filters(
        query,
        status=FormStatus.EXTRACTED,
        course_applied="bb",
    )

    results = filtered.all()
    assert len(results) == 1
    assert results[0].student_name == "Pending Form"


def test_form_to_json_dict_structure(session):
    form = create_form(
        session,
        student_name="Json Export",
        additional_info={"notes": "Requires scholarship verification"},
        verified_by="auditor@example.com",
    )

    payload = form_to_json_dict(form)

    assert payload["student_name"] == "Json Export"
    assert payload["status"] == FormStatus.VERIFIED.value
    assert payload["additional_info"] == {"notes": "Requires scholarship verification"}
    assert payload["verified_by"] == "auditor@example.com"
    assert payload["upload_date"].endswith("00:00:00")
    assert set(payload.keys()) == {attr for attr, _ in EXPORT_FIELDS}


def test_form_to_csv_row_alignment(session):
    info = {"remarks": "International applicant"}
    form = create_form(
        session,
        student_name="CSV Export",
        enrollment_number="ENR-2025-009",
        additional_info=info,
    )

    row = form_to_csv_row(form)
    assert len(row) == len(EXPORT_FIELDS)
    headers = [header for _, header in EXPORT_FIELDS]

    header_to_value = dict(zip(headers, row))
    assert header_to_value["Student Name"] == "CSV Export"
    assert header_to_value["Enrollment Number"] == "ENR-2025-009"
    assert json.loads(header_to_value["Additional Info"]) == info

