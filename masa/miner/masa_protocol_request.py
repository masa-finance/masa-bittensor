import os
import requests

# Set to 2 to fix localhost timeout issue (happening when = 1)
REQUEST_TIMEOUT_IN_SECONDS = 2

class MasaProtocolRequest():
    def __init__(self):
        self.base_url = os.getenv('ORACLE_BASE_URL', "http://54.160.27.4:8080/api/v1")
        self.authorization = os.getenv('ORACLE_AUTHORIZATION', "")
        self.headers = {"Authorization": self.authorization }
        
    def get(self, path) -> requests.Response:
        return requests.get(f"{self.base_url}{path}", headers=self.headers, timeout=REQUEST_TIMEOUT_IN_SECONDS)
    
    def post(self, path, body) -> requests.Response:
        return requests.post(f"{self.base_url}{path}", json=body, headers=self.headers, timeout=REQUEST_TIMEOUT_IN_SECONDS)