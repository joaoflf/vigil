import os
import tempfile
from dataclasses import dataclass
import cv2
import requests
import numpy as np


@dataclass
class CameraFeed:
    name: str
    video_source: str


class CameraFeedProcessor:
    camera_feed: CameraFeed
    video_first_frame: np.ndarray = np.zeros((1, 1))
    # TODO add observability attributes like average delay/interval between feeds

    def __init__(self, camera_feed: CameraFeed) -> None:
        self.camera_feed = camera_feed

    def process_feed(self):
        response = requests.get(self.camera_feed.video_source, stream=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)

            video = cv2.VideoCapture(video_file.name)
            first_frame_processed = False

            try:
                while True:
                    ret, current_frame = video.read()
                    if not ret:
                        break

                    if not first_frame_processed:
                        first_frame_processed = True
                        if self.is_frame_equal(self.video_first_frame, current_frame):
                            break
            finally:
                video.release()
                os.unlink(video_file.name)

    def is_frame_equal(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        return np.mean(frame1 - frame2) == 0


if __name__ == "__main__":
    feed = CameraFeed(
        name="test_feed",
        video_source="https://cameras.infraestruturasdeportugal.pt/121695_logo.mp4",
    )

    processor = CameraFeedProcessor(feed)
    processor.processFeed()
