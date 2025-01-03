from concurrent.futures import ThreadPoolExecutor
import numpy as np
import ffmpeg
import time
import pickle
import zmq
from datetime import datetime
from dataclasses import dataclass
import requests
import os
from dotenv import load_dotenv
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS


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
                name=item["attributes"]["descricao"],
                road=item["attributes"]["estrada"],
                video_source=item["attributes"]["url1"],
            )
            for item in items
        ]


class FeedExtractor:
    FPS_TO_EXTRACT: float = 1.0
    # TODO add observability attributes like average delay/interval between feeds

    def __init__(self, feeds: list[CameraFeed]) -> None:
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


if __name__ == "__main__":
    CHUNK_SIZE = 10
    feeds = IPCameraFetcher.fetch_camera_list()

    load_dotenv()
    client = influxdb_client.InfluxDBClient(
        url=os.environ.get("INFLUX_HOST") or "",
        token=os.environ.get("INFLUX_TOKEN"),
        org=os.environ.get("INFLUX_ORG"),
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    points = [
        influxdb_client.Point("feed")
        .tag("id", feed.id)
        .tag("name", feed.name)
        .tag("road", feed.road)
        .field("last_update", feed.last_update)
        .field("video_source", feed.video_source)
        .field("online", False)
        .field("accident", False)
        for feed in feeds
    ]

    write_api.write(bucket="vigil", record=points)

    executor = ThreadPoolExecutor()
    for chunk in [feeds[i : i + CHUNK_SIZE] for i in range(0, len(feeds), CHUNK_SIZE)]:
        processor = FeedExtractor(chunk)
        executor.submit(processor.start_extracting, 15)
