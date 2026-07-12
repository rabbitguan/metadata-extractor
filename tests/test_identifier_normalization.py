import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import backend  # noqa: E402
import doi_resolver  # noqa: E402
from extractors import geodata  # noqa: E402
from requests.exceptions import SSLError  # noqa: E402
from requests.exceptions import ReadTimeout  # noqa: E402


def test_cstr_normalization_accepts_url_and_mixed_text():
    assert (
        backend._normalize_cstr_identifier("https://cstr.cn/CSTR:11738.11.NCDC.BNORSG.DB7212.2026")
        == "11738.11.NCDC.BNORSG.DB7212.2026"
    )
    assert (
        backend._normalize_cstr_identifier("引用：https://cstr.cn/11738.11.NCDC.BNORSG.DB7212.2026。")
        == "11738.11.NCDC.BNORSG.DB7212.2026"
    )


def test_geodata_uses_cstr_field_and_converts_timezone_dates():
    payload = geodata._payload_from_data(
        {
            "guid": "274461948639522",
            "cstr": "CSTR:17099.11.G274461948639522.20260703.v1",
            "doi": "10.12009/YRDR.2026.1008.ver1.db",
            "title": "全球10km高分辨率无缝逐日XCH4数据集(2003-2020年)",
            "dataStartTime": "2002-12-31T16:00:00.000+0000",
            "dataEndTime": "2020-12-30T16:00:00.000+0000",
        },
        "https://www.geodata.cn/main/face_science_detail?typeName=face_science&guid=274461948639522",
        "",
    )
    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]

    assert core["identifier"] == "CSTR:17099.11.G274461948639522.20260703.v1"
    assert {"type": "DOI", "identifier": "10.12009/YRDR.2026.1008.ver1.db"} in core["alternative_identifiers"]
    assert geodata._format_date("2002-12-31T16:00:00.000+0000") == "2003-01-01"
    assert "2003-01-01 - 2020-12-31" in str(unified)


def test_geodata_recognizes_legacy_dataguid_landing_url():
    url = "https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522"

    assert geodata.matches(url, "", "国家地球系统科学数据共享平台")
    assert geodata._geodata_guid_from_url(url) == "274461948639522"
    assert geodata._is_geodata_detail_url(url)


def test_doi_landing_page_retries_without_ssl_verification(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        url = "https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522"
        headers = {"content-type": "text/html; charset=utf-8"}
        content = b"<html><body>ok</body></html>"
        text = "<html><body>ok</body></html>"
        encoding = None
        history = []

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise SSLError("certificate verify failed")
        return Response()

    monkeypatch.setattr(doi_resolver.requests, "get", fake_get)

    resolved = doi_resolver.resolve_doi_landing_page("10.12009/YRDR.2026.1008.ver1.db")

    assert resolved["url"] == Response.url
    assert resolved["content"] == Response.text
    assert calls[0].get("verify") is None
    assert calls[1].get("verify") is False


def test_doi_landing_page_follows_redirect_location(monkeypatch):
    calls = []

    class RedirectResponse:
        status_code = 302
        url = "https://doi.org/10.12009/YRDR.2026.1008.ver1.db"
        headers = {"Location": "https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522"}
        content = b""
        text = ""
        encoding = None
        history = []

        def raise_for_status(self):
            return None

    class LandingResponse:
        status_code = 200
        url = "https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522"
        headers = {"content-type": "text/html; charset=utf-8"}
        content = b"<html><body>landing</body></html>"
        text = "<html><body>landing</body></html>"
        encoding = None
        history = []

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return RedirectResponse() if len(calls) == 1 else LandingResponse()

    monkeypatch.setattr(doi_resolver.requests, "get", fake_get)

    resolved = doi_resolver.resolve_doi_landing_page("10.12009/YRDR.2026.1008.ver1.db")

    assert calls[0][1]["allow_redirects"] is False
    assert calls[1][0] == LandingResponse.url
    assert resolved["url"] == LandingResponse.url
    assert resolved["content"] == LandingResponse.text


def test_doi_landing_page_uses_handle_api_when_doi_redirect_times_out(monkeypatch):
    calls = []

    class HandleResponse:
        status_code = 200
        url = "https://doi.org/api/handles/10.12009/YRDR.2026.1008.ver1.db"
        headers = {"content-type": "application/json"}
        content = b"{}"
        text = "{}"
        encoding = None
        history = []

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "values": [
                    {
                        "type": "URL",
                        "data": {
                            "value": "https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522"
                        },
                    }
                ]
            }

    class LandingResponse:
        status_code = 200
        url = "https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522"
        headers = {"content-type": "text/html; charset=utf-8"}
        content = b"<html><body>landing</body></html>"
        text = "<html><body>landing</body></html>"
        encoding = None
        history = []

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) == 1:
            raise ReadTimeout("doi.org timed out")
        return HandleResponse() if "/api/handles/" in url else LandingResponse()

    monkeypatch.setattr(doi_resolver.requests, "get", fake_get)

    resolved = doi_resolver.resolve_doi_landing_page("10.12009/YRDR.2026.1008.ver1.db")

    assert calls[0][0].startswith("https://doi.org/10.12009/")
    assert calls[1][0].startswith("https://doi.org/api/handles/")
    assert calls[2][0] == LandingResponse.url
    assert resolved["url"] == LandingResponse.url
