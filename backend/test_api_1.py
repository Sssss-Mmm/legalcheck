import os
import requests

API_KEY = "0d61d99fc6869f68a814c2cf2b2ab6f232f6e2b2e7e2554ba04b7ac61c6c10f4"

url = "https://apis.data.go.kr/1170000/law/lawSearchList.do"

url = 'http://apis.data.go.kr/1170000/law/lawSearchList.do'
params ={'serviceKey' : API_KEY, 'target' : 'law', 'query' : '10', 'numOfRows' : '10', 'pageNo' : '1' }

response = requests.get(url, params=params)
print(response.content)

