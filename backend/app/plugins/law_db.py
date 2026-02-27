import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

API_KEY = os.environ.get("LAW_GO_KR_API_KEY", "0d61d99fc6869f68a814c2cf2b2ab6f232f6e2b2e7e2554ba04b7ac61c6c10f4")

def search_law_articles(law_name: str, keyword: str = "") -> list:
    """
    국가법령정보센터 Open API를 사용하여 특정 법령(예: 근로기준법)의 내용을 검색하거나
    키워드에 맞는 조문을 동적으로 추출합니다.
    (law.go.kr 대신 스크린샷에 명시된 data.go.kr 엔드포인트 적용)
    """
    encoded_law = urllib.parse.quote(law_name)
    
    # 1. 법령 기본 정보 및 ID 조회 (스크린샷 NO 1: 법령정보 목록 조회 /lawSearchList.do)
    base_url = "https://apis.data.go.kr/1170000/law"
    search_url = f"{base_url}/lawSearchList.do?serviceKey={API_KEY}&target=law&type=XML&query={encoded_law}"
    
    results = []
    try:
        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req) as response:
            xml_data = response.read().decode('utf-8')
            
        root = ET.fromstring(xml_data)
        
        # 첫 번째 검색된 법령의 법령일련번호를 가져옵니다
        law = root.find('.//law')
        if law is None:
            return []
            
        law_id = law.findtext('법령일련번호')
        
        # 2. 법령 상세 조회 (API 구조상 상세조회는 보통 별도로 구성됨. 서비스 목록에 없으나 통상 사용되는 lawService 연동)
        detail_url = f"{base_url}/lawService.do?serviceKey={API_KEY}&target=law&MST={law_id}&type=XML"
        
        # 만약 상세조회 API 경로가 다를 수 있으므로 예외 처리
        try:
            with urllib.request.urlopen(detail_url) as detail_response:
                detail_xml = detail_response.read().decode('utf-8')
            detail_root = ET.fromstring(detail_xml)
        except urllib.error.HTTPError:
            # 404/403 등 에러 발생 시 목록조회에서 받아온 데이터로 Fallback
            detail_root = root

        # 조문 태그(<조문단위>)를 순회하며 키워드가 포함된 조문 발췌
        jo_list = detail_root.findall('.//조문단위')
        
        for jo in jo_list:
            jo_title = jo.findtext('조문제목', '')
            jo_num = jo.findtext('조문번호', '')
            jo_content = jo.findtext('조문내용', '')
            
            # 하위 항/권/호 텍스트들 합치기
            hang_list = jo.findall('.//항내용')
            ho_list = jo.findall('.//호내용')
            
            full_content = jo_content + "\n" + "\n".join([h.text for h in hang_list if h.text]) + "\n" + "\n".join([h.text for h in ho_list if h.text])
            
            if keyword and keyword not in full_content and keyword not in jo_title:
                continue
                
            results.append({
                "법령명": law_name,
                "조문번호": jo_num,
                "조문제목": jo_title,
                "조문내용": full_content.strip()
            })
            
            # API 호출 지연 방지를 위해 최대 3~5개 조문만 발췌
            if len(results) >= 3:
                break
                
    except Exception as e:
        print(f"Error fetching law info from DATA.GO.KR: {e}")
        # API 인증 대기(1~2시간) 혹은 네트워크 오류 시 Fallback
        results.append({
            "법령명": law_name,
            "조문번호": "-",
            "조문제목": "조문 확인 불가 (데이터포털 연동 중)",
            "조문내용": f"공공데이터포털 API 연동 중 오류 발생: {e}"
        })
        
    return results
