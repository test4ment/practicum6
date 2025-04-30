from ssl import SSLError
import requests
import os
path = os.getcwd() + "/certs/"

addr = "https://127.0.0.1:8000/"
with requests.Session() as s:
    s.cert = (path + "client.crt", path + "client.key")
    s.verify = path + "ca.crt"  
    
    resp = s.get(addr, timeout=2.5)
    print(resp, resp.json())

    resp = s.get(addr + "generate_token?service_name=test%20service").json()
    print(resp)

    resp = s.get(addr + f"auth_service?token={resp['access_token']}").json()
    print(resp)

    resp = s.get(addr + f"auth_service?token=abracadabra")
    print(resp)

try:
    resp = requests.get(addr, timeout=2.5)
except Exception as ex:
    print(ex)
