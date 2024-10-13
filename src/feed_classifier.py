import pickle
import json
import zmq
import cv2
from dotenv import load_dotenv
from inference.models.utils import get_roboflow_model
import os


class FeedClassifier:
    def __init__(self) -> None:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PULL)
        self.socket.connect("tcp://localhost:5556")
        print("Listening on 5556")

        load_dotenv()
        model = get_roboflow_model(
            model_id="crash-car-detection/3", api_key=os.environ.get("RF_API_KEY")
        )

        try:
            while True:
                raw_message = self.socket.recv()
                name, last_update, frame = pickle.loads(raw_message)
                result = model.infer(frame)[0]
                is_accident = any(
                    [
                        prediction.class_name == "accident"
                        for prediction in result.predictions
                    ]
                )

                if is_accident:
                    print("Accident found!")
                    cv2.imwrite(f"positive-{last_update}.jpg", frame)
                    with open(f"positive-{last_update}.txt", "w") as file:
                        json.dump(result.predictions, file)
                else:
                    print("No accidents found")

        except KeyboardInterrupt:
            print("W: interrupt received, stopping...")
        finally:
            self.socket.close()
            self.context.term()


if __name__ == "__main__":
    classifier = FeedClassifier()
