from types import SimpleNamespace

from wardwatch_api.db import SessionLocal
from wardwatch_api.rag import REFUSE, ask_city, bm25_rank, rrf, ticket_blob
from wardwatch_api.vectors import dense_rank, upsert_vector


def test_ask_refuses_when_index_empty():
    db = SessionLocal()
    result = ask_city(db, "Who is the mayor of Hyderabad?", lat=17.3616, lng=78.4747)
    assert result["answer"] == REFUSE
    assert result["sources"] == []
    db.close()


def _closed_pothole():
    return SimpleNamespace(
        public_id="WW-24-0001",
        title="Pothole · Gachibowli",
        type="pothole",
        status="resolved",
        ward="Gachibowli",
        neighborhood="gachibowli",
        circle="serilingampally",
        severity="blocks_road",
        body="This is making roads blocked in the evenings",
        resolve_note="this issue has been fixed and thanks for reporting",
    )


def test_bm25_finds_closed_ticket_and_skips_unrelated():
    blob = ticket_blob(_closed_pothole())
    docs = [("WW-24-0001", blob)]
    assert bm25_rank("what happened to WW-24-0001", docs) == ["WW-24-0001"]
    assert bm25_rank("is that pothole fixed", docs) == ["WW-24-0001"]
    assert bm25_rank("closed tickets near me", docs) == ["WW-24-0001"]
    assert bm25_rank("who is the mayor of Hyderabad", docs) == []
    assert bm25_rank("waterlogging near me", docs) == []


def test_rrf_prefers_a_ticket_found_by_both_lists():
    fused = rrf([["WW-24-0002", "WW-24-0001"], ["WW-24-0001", "WW-24-0003"]])
    assert fused[0] == "WW-24-0001"


def test_vector_search_keeps_the_closer_ticket(tmp_path, monkeypatch):
    db_file = (tmp_path / "tickets.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    near = [1.0] + [0.0] * 767
    far = [0.0, 1.0] + [0.0] * 766
    upsert_vector("WW-24-0001", near, "near")
    upsert_vector("WW-24-0002", far, "far")
    ranked = dense_rank(near, {"WW-24-0001", "WW-24-0002"})
    assert ranked == ["WW-24-0001"]
    upsert_vector("WW-24-0001", near, "near-again")
    assert dense_rank(near, {"WW-24-0001"}) == ["WW-24-0001"]
