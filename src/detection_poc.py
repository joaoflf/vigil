from dotenv import load_dotenv
from inference.models.utils import get_roboflow_model
import cv2
import os

load_dotenv()
model = get_roboflow_model(
    model_id="crash-car-detection/3", api_key=os.environ.get("RF_API_KEY")
)
image = cv2.imread("../test/test_assets/traffic-frame.jpg")
result = model.infer(image)[0]
is_accident = any(
    [prediction.class_name == "accident" for prediction in result.predictions]
)

print(f"Found accident: {is_accident}")
