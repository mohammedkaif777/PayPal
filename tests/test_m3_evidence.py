from app.services.pdf_extractor import PdfExtractorService
from app.services.pdf_fixture import build_encrypted_pdf_stub, build_simple_pdf
from tests.helpers import create_parties, create_shipment, png_bytes


def test_pdf_upload_extract_and_mock_ai(client, operator_headers, tmp_path):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    pdf = build_simple_pdf(
        [
            "ShipmentRef: SHIP-001",
            "Shipper: AgriFresh Farms Ltd",
            "DocumentDate: 2026-11-01T00:00:00Z",
        ]
    )
    upload = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "BILL_OF_LADING"},
        files={"file": ("bol.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    assert "SHIP-001" in (upload.json()["extracted_text"] or "")
    extracted = client.post(
        f"/api/v1/evidence/{upload.json()['id']}/extract",
        headers=operator_headers,
    )
    assert extracted.status_code == 200
    fields = extracted.json()["extracted_fields"]
    assert fields["shipment_ref"] == "SHIP-001"
    assert "claim" not in fields
    assert "payout" not in fields


def test_reject_encrypted_pdf_and_path_traversal(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    encrypted = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "BILL_OF_LADING"},
        files={"file": ("secret.pdf", build_encrypted_pdf_stub(), "application/pdf")},
    )
    assert encrypted.status_code == 400
    traversal = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "PHOTO"},
        files={"file": ("../../etc/passwd.png", png_bytes(), "image/png")},
    )
    assert traversal.status_code == 400


def test_reject_unsupported_type_and_oversize(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    bad_type = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "PHOTO"},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert bad_type.status_code == 415
    huge = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "PHOTO"},
        files={"file": ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (21 * 1024 * 1024), "image/png")},
    )
    assert huge.status_code == 413


def test_image_qc_and_duplicate_hash(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"], ref="SHIP-IMG"
    )
    payload = png_bytes()
    first = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "PHOTO"},
        files={"file": ("a.png", payload, "image/png")},
    )
    second = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "PHOTO"},
        files={"file": ("b.png", payload, "image/png")},
    )
    assert first.status_code == 201
    qc = client.get(
        f"/api/v1/evidence/{second.json()['id']}/qc", headers=operator_headers
    )
    assert qc.status_code == 200
    assert qc.json()["duplicate_of_document_id"] == first.json()["id"]
    assert qc.json()["perceptual_hash"]


def test_pdf_fixture_is_not_encrypted():
    pdf = build_simple_pdf(["ShipmentRef: SHIP-001"])
    assert not PdfExtractorService.is_encrypted_pdf(pdf)
