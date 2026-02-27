import asyncio
import httpx
import xml.etree.ElementTree as ET

API_KEY = "0d61d99fc6869f68a814c2cf2b2ab6f232f6e2b2e7e2554ba04b7ac61c6c10f4"

async def test_law_search():
    # End Point from image: https://apis.data.go.kr/1170000/law
    # According to 공공데이터포털, 법령목록조회: /lawSearch.do? or just /law? 
    # Let's try the direct open.law.go.kr style API which is usually what data.go.kr proxies,
    # or just try https://www.law.go.kr/DRF/lawSearch.do with this key? No, the image specifically says https://apis.data.go.kr/1170000/law
    
    url = "https://apis.data.go.kr/1170000/law/lawSearch.do" # typical path, we'll try it
    params = {
        "serviceKey": API_KEY,
        "target": "law",
        "query": "근로기준법",
        "type": "XML"
    }
    
    # test multiple possible endpoints
    endpoints = [
        ("https://apis.data.go.kr/1170000/law/lawSearch.do", params),
        ("https://apis.data.go.kr/1170000/law", {"serviceKey": API_KEY, "target": "law", "query": "근로기준법"}),
        ("https://www.law.go.kr/DRF/lawSearch.do", {"OC": API_KEY, "target": "law", "query": "근로기준법", "type": "XML"}),
    ]
    
    async with httpx.AsyncClient() as client:
        for ep, p in endpoints:
            print(f"Testing {ep}...")
            try:
                res = await client.get(ep, params=p, timeout=5.0)
                print(f"Status: {res.status_code}")
                print(res.text[:500])
                print("-" * 50)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_law_search())
