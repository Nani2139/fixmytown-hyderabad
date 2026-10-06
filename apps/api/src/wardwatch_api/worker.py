from __future__ import annotations

import time

from sqlalchemy.orm import Session

from wardwatch_api.db import SessionLocal
from wardwatch_api.models import VisionJob
from wardwatch_api.vision import process_vision_job


def run_forever() -> None:
    print("WardWatch worker listening for vision jobs")
    while True:
        db: Session = SessionLocal()
        try:
            job = (
                db.query(VisionJob)
                .filter(VisionJob.status == "queued")
                .order_by(VisionJob.created_at.asc())
                .first()
            )
            if job:
                process_vision_job(db, job.id)
        finally:
            db.close()
        time.sleep(1)


if __name__ == "__main__":
    run_forever()
