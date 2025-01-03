import pickle
import jsonpickle
import zmq
import cv2
from dotenv import load_dotenv
from inference.models.utils import get_roboflow_model
import os
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS


class FeedClassifier:
    def __init__(self, confidence: float) -> None:
        self.confidence = confidence
        load_dotenv()
        self.model = get_roboflow_model(
            model_id="crash-car-detection/3", api_key=os.environ.get("RF_API_KEY")
        )

        client = influxdb_client.InfluxDBClient(
            url=os.environ.get("INFLUX_HOST") or "",
            token=os.environ.get("INFLUX_TOKEN"),
            org=os.environ.get("INFLUX_ORG"),
        )
        self.write_api = client.write_api(write_options=SYNCHRONOUS)

        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.bind("tcp://*:5556")
        print("Listening on 5556")

        try:
            while True:
                self._process_message(socket.recv())
        except KeyboardInterrupt:
            print("W: interrupt received, stopping...")
        finally:
            socket.close()
            context.term()

    def _process_message(self, message: bytes) -> None:
        id, last_update, frame = pickle.loads(message)
        result = self.model.infer(frame)[0]

        is_accident = any(
            [
                prediction.class_name == "accident"
                and prediction.confidence >= self.confidence
                for prediction in result.predictions
            ]
        )

        points = (
            influxdb_client.Point("feed")
            .tag("id", id)
            .field("last_update", int(last_update))
            .field("online", True)
            .field("accident", is_accident)
        )

        self.write_api.write(bucket="vigil", record=points)

        if is_accident:
            print(f"{id}: Accident found!")
            cv2.imwrite(f"positives/{id}-{last_update}.jpg", frame)
            with open(f"positives/{id}-{last_update}.txt", "w") as file:
                file.write(str(jsonpickle.encode(result.predictions)))
        else:
            print("No accidents found")


if __name__ == "__main__":
    classifier = FeedClassifier(0.7)
