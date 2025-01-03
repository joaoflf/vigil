from camera_feed import CameraFeed
import requests

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
