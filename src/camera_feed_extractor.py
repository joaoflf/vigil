import time
from datetime import datetime
import os
import tempfile
from dataclasses import dataclass
import cv2
import requests


@dataclass
class CameraFeed:
    name: str
    video_source: str
    last_update: int = 0


class FeedExtractor:
    camera_feed: CameraFeed
    # TODO add observability attributes like average delay/interval between feeds

    def __init__(self, camera_feed: CameraFeed) -> None:
        self.camera_feed = camera_feed

    def start_extracting(self, interval: int) -> None:
        while True:
            self._extract_frames()
            time.sleep(interval)

    def _extract_frames(self):
        response = requests.get(self.camera_feed.video_source, stream=True)

        last_modified = response.headers.get("last-modified", 0)
        if isinstance(last_modified, str):
            last_modified = int(
                datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").timestamp()
            )

        if last_modified <= self.camera_feed.last_update:
            print("Same video. Skipping")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)

            video = cv2.VideoCapture(video_file.name)

            while True:
                ret, current_frame = video.read()
                if not ret:
                    break

                print("sent frame")

            video.release()
            os.unlink(video_file.name)
            self.camera_feed.last_update = last_modified


# if __name__ == "__main__":
#     feed = CameraFeed(
#         name="test_feed",
#         video_source="https://cameras.infraestruturasdeportugal.pt/121695_logo.mp4",
#     )
#
#     processor = FeedExtractor(feed)
#     processor.start_extracting(15)
