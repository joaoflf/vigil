import numpy as np
import requests
import ffmpeg
import time
import pickle
import zmq
from datetime import datetime
from camera_feed import CameraFeed


class FeedExtractor:
    FPS_TO_EXTRACT: float = 1.0
    # TODO add observability attributes like average delay/interval between feeds

    def __init__(self, feeds: list[CameraFeed]) -> None:
        print("─" * 25)
        print("Starting extractor...")
        self.feeds = feeds
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.connect("tcp://localhost:5556")
        print("Socket bound on port 5556")

    def start_extracting(self, interval: int) -> None:
        try:
            while True:
                start = time.perf_counter()
                for feed in self.feeds:
                    self._extract_frames(feed)
                end = time.perf_counter()
                print(f"Extraction time: {end - start:.6f} seconds")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("Classifier: Keyboard interrupt")
        finally:
            print("Extractor: closing connections")
            self.socket.close()
            self.context.term()

    def _extract_frames(self, camera_feed: CameraFeed):
        response = requests.head(camera_feed.video_source)

        if response.status_code == 404:
            print(f"{camera_feed.name} is down, skipping")
            return

        last_modified = response.headers.get("last-modified", 0)
        if isinstance(last_modified, str):
            last_modified = int(
                datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").timestamp()
            )

        if last_modified <= camera_feed.last_update:
            print(f"{camera_feed.name}: same video. Skipping")
            return

        probe = ffmpeg.probe(camera_feed.video_source)
        video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
        width = int(video_info["width"])
        height = int(video_info["height"])
        duration = float(video_info["duration"])
        total_frames = int(duration * self.FPS_TO_EXTRACT)

        process = (
            ffmpeg.input(camera_feed.video_source)
            .filter("fps", fps=self.FPS_TO_EXTRACT)
            .output("pipe:", format="rawvideo", pix_fmt="rgb24")
            .global_args("-loglevel", "quiet")
            .run_async(pipe_stdout=True)
        )

        frame_count = 0
        try:
            while frame_count < total_frames:
                in_bytes = process.stdout.read(width * height * 3)
                if not in_bytes:
                    break

                frame = np.frombuffer(in_bytes, np.uint8).reshape([height, width, 3])
                serialized_data = pickle.dumps(
                    [
                        camera_feed.id,
                        camera_feed.last_update,
                        frame,
                    ]
                )
                self.socket.send(serialized_data)
                frame_count += 1

        finally:
            process.stdout.close()
            process.wait()
            print(
                f"{camera_feed.name}: sent {frame_count} frames for timestamp: {response.headers.get('last-modified', 'no timestamp')}"
            )
            camera_feed.last_update = last_modified
