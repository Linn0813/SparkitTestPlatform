from app.services.file_storage import (
    build_content_disposition,
    build_file_download_url,
    resolve_content_type,
    verify_download_signature,
)


def test_build_file_download_url_uses_api_proxy(monkeypatch):
    monkeypatch.setattr(
        "app.services.file_storage.settings.api_public_url",
        "http://127.0.0.1:8000",
    )
    url = build_file_download_url("projects/p1/abc.png")
    assert url.startswith("/api/v1/files/raw?object_key=projects%2Fp1%2Fabc.png")
    assert "&expires=" in url
    assert "&signature=" in url


def test_build_file_download_url_absolute_when_public_api(monkeypatch):
    monkeypatch.setattr(
        "app.services.file_storage.settings.api_public_url",
        "http://192.168.1.10:8000",
    )
    url = build_file_download_url("projects/p1/abc.png")
    assert url.startswith("http://192.168.1.10:8000/api/v1/files/raw?")


def test_download_signature_roundtrip(monkeypatch):
    monkeypatch.setattr("app.services.file_storage.settings.secret_key", "test-secret")
    key = "projects/p1/file.png"
    url = build_file_download_url(key, expires_seconds=3600)
    assert "signature=" in url
    sig = url.split("signature=")[1]
    exp = int(url.split("expires=")[1].split("&")[0])
    assert verify_download_signature(key, exp, sig)


def test_build_content_disposition_ascii():
    assert build_content_disposition("report.pdf", "inline") == "inline"
    header = build_content_disposition("report.pdf", "attachment")
    assert header == 'attachment; filename="report.pdf"'
    header.encode("latin-1")


def test_build_content_disposition_unicode():
    assert build_content_disposition("截图和说明.png", "inline") == "inline"
    header = build_content_disposition("截图和说明.png", "attachment")
    assert header.startswith('attachment; filename="')
    assert "filename*=UTF-8''" in header
    assert "%E6%88%AA" in header
    header.encode("latin-1")


def test_resolve_content_type_from_extension():
    assert resolve_content_type("截图.png", "application/octet-stream") == "image/png"
    assert resolve_content_type("doc.pdf", None) == "application/pdf"
