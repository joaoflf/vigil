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
    id: str
    name: str
    road: str
    video_source: str
    last_update: int = 0


IP_CAMERA_REQUEST_URL = "https://utility.arcgis.com/usrsvcs/servers/98bffc4ef35b4e18a03641918c5d07dd/rest/services/webapps/viajar_na_estrada2024/MapServer/3/query?f=json&cacheHint=true&resultOffset=0&resultRecordCount=8000&where=1=1&orderByFields=objectid&outFields=data_ultimo_video,id_camera,estrada,descricao,url1"


class IPCameraFetcher:
    @staticmethod
    def fetch_camera_list() -> list[CameraFeed]:
        response = requests.get(IP_CAMERA_REQUEST_URL)
        items = response.json()["features"]
        return [
            CameraFeed(
                id=item["attributes"]["id_camera"],
                name=item["attributes"]["descricao"]
                .encode("utf-8", errors="ignore")
                .decode("utf-8"),
                road=item["attributes"]["estrada"],
                video_source=item["attributes"]["url1"],
            )
            for item in items
        ]


class FeedExtractor:
    FRAME_SKIP_INTERVAL: int = 10
    # TODO add observability attributes like average delay/interval between feeds

    def __init__(self, feeds: list[CameraFeed]) -> None:
        self.feeds = feeds
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.bind("tcp://*:5556")
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
            print("W: interrupt received, stopping...")

        finally:
            self.socket.close()
            self.context.term()

    def _extract_frames(self, camera_feed: CameraFeed):
        response = requests.get(camera_feed.video_source, stream=True)

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
                            camera_feed.id,
                            camera_feed.name,
                            camera_feed.last_update,
                            current_frame,
                        ]
                    )
                    self.socket.send(serialized_data)
                    sent_frames += 1

            finally:
                print(
                    f"{camera_feed.name}: sent {sent_frames} frames for timestamp: {response.headers.get('last-modified', 'no timestamp')}"
                )
                video.release()
                os.unlink(video_file.name)
                camera_feed.last_update = last_modified


if __name__ == "__main__":
    feeds = IPCameraFetcher.fetch_camera_list()
    processor = FeedExtractor(feeds)
    processor.start_extracting(15)
