import requests
import pytest
from unittest.mock import Mock
from src.feed_extractor import CameraFeed, FeedExtractor


@pytest.fixture
def camera_feed():
    return CameraFeed(name="test_feed", video_source="test_source")


class FeedMockResponse:
    def __init__(self, headers):
        self.headers = headers

    @staticmethod
    def iter_content(chunk_size):
        with open("tests/test_assets/traffic-frame.jpg", "rb") as f:
            yield f.read(chunk_size)


def text_extract_frames(camera_feed, monkeypatch, capsys):
    mock_response = FeedMockResponse({"last-modified": 1})

    def mock_get(*args, **kwargs):
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get)

    extractor = FeedExtractor(camera_feed)

    mock_send = Mock()
    monkeypatch.setattr("extractor.socket.send", mock_send)

    extractor._extract_frames()
    mock_send.assert_called_with(True)


def test_same_video_not_processed_twice(camera_feed, monkeypatch, capsys):
    mock_response = FeedMockResponse({"last-modified": 1})

    def mock_get(*args, **kwargs):
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get)

    extractor = FeedExtractor(camera_feed)
    extractor._extract_frames()
    capsys.readouterr()
    extractor._extract_frames()
    captured = capsys.readouterr()
    assert captured.out == "Same video. Skipping\n"
