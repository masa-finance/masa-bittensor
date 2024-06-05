import os
import requests

class ProtocolRequest():
    def __init__(self):
        self.base_url = os.getenv('ORACLE_BASE_URL', "http://localhost:8080/api/v1")
        self.authorization = os.getenv('ORACLE_AUTHORIZATION', "Bearer 1234")
        self.headers = {"Authorization": self.authorization }
        
    def get(self, path) -> requests.Response:
        timeout_duration = 1
        return requests.get(f"{self.base_url}{path}", headers=self.headers, timeout=timeout_duration)
    
    def post(self, path, body) -> requests.Response:
        timeout_duration = 1
        return requests.post(f"{self.base_url}{path}", json=body, headers=self.headers, timeout=timeout_duration)