from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.services.audit import AuditService


def test_audit_chain_and_endpoint(client, admin_headers):
    with SessionLocal() as db:
        first = AuditService.record(
            db,
            actor="tester",
            action="create",
            entity_type="shipment",
            entity_id="S1",
            after={"status": "REGISTERED"},
        )
        second = AuditService.record(
            db,
            actor="tester",
            action="update",
            entity_type="shipment",
            entity_id="S1",
            before={"status": "REGISTERED"},
            after={"status": "IN_TRANSIT"},
        )
        db.commit()
        assert first.prev_hash == "GENESIS"
        assert second.prev_hash == first.hash
        assert first.hash != second.hash

    response = client.get("/api/v1/audit", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["hash"] == second.hash
    assert body[1]["hash"] == first.hash
    assert body[0]["action"] == "update"


def test_audit_rows_are_linked(client, admin_headers):
    with SessionLocal() as db:
        for index in range(3):
            AuditService.record(
                db,
                actor="tester",
                action="step",
                entity_type="test",
                entity_id=str(index),
            )
        db.commit()
        rows = (
            db.query(AuditLog)
            .order_by(AuditLog.id.asc())
            .all()
        )
        assert rows[0].prev_hash == "GENESIS"
        for previous, current in zip(rows, rows[1:]):
            assert current.prev_hash == previous.hash
