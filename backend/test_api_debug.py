import urllib.request
import urllib.parse
import os

API_KEY = "0d61d99fc6869f68a814c2cf2b2ab6f232f6e2b2e7e2554ba04b7ac61c6c10f4"
law_name = "주택"
encoded_law = urllib.parse.quote(law_name)

base_url = "https://apis.data.go.kr/1170000/law"
search_url = f"{base_url}/lawSearchList.do?serviceKey={API_KEY}&target=law&type=XML&query={encoded_law}"

print(f"Requesting: {search_url}")

try:
    req = urllib.request.Request(search_url)
    with urllib.request.urlopen(req) as response:
        xml_data = response.read().decode('utf-8')
        print(xml_data[:500])
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
