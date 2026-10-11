import time

import pytest
from fastapi.testclient import TestClient

from kinora.app import create_app
from kinora.config import Settings


@pytest.fixture
def client(tmp_path):
    settings = Settings(output_dir=tmp_path, providers=("mock", "replicate"), replicate_token=None)
    with TestClient(create_app(settings)) as c:
        yield c


def wait_for(client, job_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def test_providers_reports_availability(client):
    data = client.get("/api/providers").json()
    by_name = {p["name"]: p for p in data["providers"]}
    assert by_name["mock"]["available"] is True
    assert by_name["replicate"]["available"] is False
    assert "REPLICATE_API_TOKEN" in by_name["replicate"]["reason"]


def test_mock_generation_produces_mp4(client):
    r = client.post(
        "/api/jobs", json={"prompt": "a red fox in the snow", "seconds": 1, "width": 320, "height": 192}
    )
    assert r.status_code == 201
    job = wait_for(client, r.json()["id"])
    assert job["status"] == "succeeded", job["error"]
    video = client.get(job["video_url"])
    assert video.status_code == 200
    assert video.content[4:8] == b"ftyp"  # MP4 container signature


def test_unavailable_provider_is_rejected(client):
    r = client.post("/api/jobs", json={"prompt": "hello", "provider": "replicate"})
    assert r.status_code == 400


def test_unknown_provider_is_rejected(client):
    r = client.post("/api/jobs", json={"prompt": "hello", "provider": "nope"})
    assert r.status_code == 404


def test_empty_prompt_is_rejected(client):
    assert client.post("/api/jobs", json={"prompt": ""}).status_code == 422


def test_frontend_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "kinora" in r.text
