import time
import pickle
import zmq
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
    FRAME_SKIP_INTERVAL: int = 10
    # TODO add observability attributes like average delay/interval between feeds

    def __init__(self, camera_feed: CameraFeed) -> None:
        self.camera_feed = camera_feed
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.bind("tcp://*:5556")
        print("Socket bound on port 5556")

    def start_extracting(self, interval: int) -> None:
        try:
            while True:
                self._extract_frames()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("W: interrupt received, stopping...")
        finally:
            self.socket.close()
            self.context.term()

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

            # prevent video capture to start before finishing download
            time.sleep(1)
            video = cv2.VideoCapture(video_file.name)
            total_frames = 0
            sent_frames = 0

            try:
                while True:
                    ret, current_frame = video.read()
                    total_frames += 1

                    if not ret or total_frames % self.FRAME_SKIP_INTERVAL == 0:
                        break

                    serialized_data = pickle.dumps(
                        [
                            self.camera_feed.name,
                            self.camera_feed.last_update,
                            current_frame,
                        ]
                    )
                    self.socket.send(serialized_data)
                    sent_frames += 1

            finally:
                print(
                    f"Sent {sent_frames} frames for timestamp: {response.headers.get('last-modified', 'no timestamp')}"
                )
                video.release()
                os.unlink(video_file.name)
                self.camera_feed.last_update = last_modified


if __name__ == "__main__":
    feed = CameraFeed(
        name="test_feed",
        video_source="https://cameras.infraestruturasdeportugal.pt/121695_logo.mp4",
    )

    processor = FeedExtractor(feed)
    processor.start_extracting(15)
