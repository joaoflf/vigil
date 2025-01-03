import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from ip_camera_fetcher import IPCameraFetcher
from concurrent.futures import ThreadPoolExecutor
from threading import Event as ThreadEvent
from multiprocessing import Process, Event as ProcessEvent
from feed_extractor import FeedExtractor
from feed_classifier import FeedClassifier
import fire


def main(
    fetcher: str = "IP",
    feeds_per_thread: int = 10,
    pause_time: int = 15,
    model_confidence: float = 0.7,
) -> None:
    if not (
        os.environ.get("INFLUX_HOST")
        and os.environ.get("INFLUX_TOKEN")
        and os.environ.get("INFLUX_ORG")
    ):
        print(
            "Influx vars not set: please set $INFLUX_HOST, $INFLUX_TOKEN and $INFLUX_ORG"
        )
        exit(0)

    if fetcher != "IP":
        print("Invalid camera feed fetcher")

    feed_fetcher = IPCameraFetcher
    print("Fetching camera list...")
    feeds = feed_fetcher.fetch_camera_list()
    print("Success")
    print("─" * 25)

    load_dotenv()
    influxdb_client = InfluxDBClient(
        url=os.environ.get("INFLUX_HOST"),
        token=os.environ.get("INFLUX_TOKEN"),
        org=os.environ.get("INFLUX_ORG"),
    )
    influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    print("Writing camera metadata to influxdb...")
    points = [
        Point("feed")
        .tag("id", feed.id)
        .tag("name", feed.name)
        .tag("road", feed.road)
        .field("last_update", feed.last_update)
        .field("video_source", feed.video_source)
        .field("online", False)
        .field("accident", False)
        for feed in feeds
    ]
    print("Success")
    print("─" * 25)

    influxdb_write_api.write(bucket="vigil", record=points)

    thread_stop_event = ThreadEvent()
    process_stop_event = ProcessEvent()
    executor = ThreadPoolExecutor()

    try:
        classifier_process = Process(
            target=FeedClassifier,
            args=(model_confidence, process_stop_event),
        )
        classifier_process.start()

        for chunk in [
            feeds[i : i + feeds_per_thread]
            for i in range(0, len(feeds), feeds_per_thread)
        ]:
            processor = FeedExtractor(chunk)
            executor.submit(processor.start_extracting, pause_time)

    except KeyboardInterrupt:
        print("W: interrupt received, stopping...")
    finally:
        executor.shutdown()
        influxdb_client.close()


if __name__ == "__main__":
    fire.Fire(main)
