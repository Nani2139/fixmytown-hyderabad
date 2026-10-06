import os

os.environ["WARDWATCH_SEED"] = "0"

import pytest

from wardwatch_api.db import Base, engine
from wardwatch_api.models import User  # noqa: F401


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
