import os
import time
import requests

class MockDataService:
    def __init__(self, protocol, server_ip, port, provider_name, device_name, identity_key):
        self.protocol = protocol
        self.server_ip = server_ip
        self.port = port
        self.provider_name = provider_name
        self.device_name = device_name
        self.identity_key = identity_key

    def send_observation_as_http(self, observation):
        address = f"{self.protocol}://{self.server_ip}:{self.port}/data/{self.provider_name}/{self.device_name}/{observation}"
        headers = {
            'IDENTITY_KEY': str(self.identity_key)
        }
        return requests.put(address, headers=headers)
        
def main():
    interval = int(os.environ.get("SEND_INTERVAL", 60))
    
    service = MockDataService(
        protocol="http",
        server_ip="localhost",
        port=5000,  
        provider_name="provider1",
        device_name="device1",
        identity_key=12345
    )
    
    observation = 0 
    while True:
        try:
            response = service.send_observation_as_http(observation)
            print(f"Observation {observation} gönderildi. Status Code: {response.status_code}")
        except Exception as e:
            print(f"Observation {observation} gönderilirken hata: {e}")
        observation += 1
        time.sleep(interval)

if __name__ == "__main__":
    main()