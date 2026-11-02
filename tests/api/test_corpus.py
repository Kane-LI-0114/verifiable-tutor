"""Corpus page images for the citation panel."""

from __future__ import annotations


def _write_page(api, doc_id: str = "course_project", page_no: int = 1) -> bytes:
    directory = api.settings.corpus_images_dir
    directory.mkdir(parents=True, exist_ok=True)
    payload = b"RIFF-webp-page"
    (directory / f"{doc_id}.p{page_no:03d}.webp").write_bytes(payload)
    return payload


def test_page_image_requires_sign_in(api):
    assert api.client.get("/api/corpus/course_project/pages/1.webp").status_code == 401


def test_page_image_is_served_from_the_local_mirror(api):
    api.create_active_account("alice@ust.hk")
    payload = _write_page(api)

    response = api.client.get("/api/corpus/course_project/pages/1.webp")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.content == payload


def test_missing_page_image_is_not_found(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/corpus/course_project/pages/9.webp")

    assert response.status_code == 404
    assert response.json() == {"detail": "page image not found"}


def test_invalid_document_id_and_page_number_are_rejected(api):
    api.create_active_account("alice@ust.hk")

    assert api.client.get("/api/corpus/bad%20doc/pages/1.webp").status_code == 422
    assert api.client.get("/api/corpus/course_project/pages/0.webp").status_code == 422
    assert api.client.get("/api/corpus/course_project/pages/notanumber.webp").status_code == 422
