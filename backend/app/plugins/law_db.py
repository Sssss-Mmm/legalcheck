import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

API_KEY = os.environ.get("LAW_GO_KR_API_KEY", "0d61d99fc6869f68a814c2cf2b2ab6f232f6e2b2e7e2554ba04b7ac61c6c10f4")

def search_law_articles(law_name: str, keyword: str = "", limit: int = 3) -> list:
    """
    국가법령정보센터 Open API를 사용하여 특정 법령(예: 근로기준법)의 내용을 검색하거나
    키워드에 맞는 조문을 동적으로 추출합니다.
    (law.go.kr 대신 스크린샷에 명시된 data.go.kr 엔드포인트 적용)
    """
    encoded_law = urllib.parse.quote(law_name)
    
    # 1. 법령 기본 정보 및 ID 조회 (스크린샷 NO 1: 법령정보 목록 조회 /lawSearchList.do)
    base_url = "https://apis.data.go.kr/1170000/law"
    # 활용가이드 스크린샷에 명시된 필수 파라미터(numOfRows, pageNo) 추가
    search_url = f"{base_url}/lawSearchList.do?serviceKey={API_KEY}&target=law&type=XML&query={encoded_law}&numOfRows=5&pageNo=1"
    
    results = []
    try:
        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req) as response:
            xml_data = response.read().decode('utf-8')
            
        root = ET.fromstring(xml_data)
        
        # 검색된 법령 중 상위 최대 3개까지의 본문을 순회합니다 (자주 나오는 법률, 시행령, 시행규칙 등 포괄)
        laws = root.findall('.//law')[:3]
        if not laws:
            return []
            
        for law in laws:
            # 법령 상세링크 추출 (data.go.kr 게이트웨이는 목록만 제공하므로 상세는 링크를 타고 들어감)
            detail_link = law.findtext('법령상세링크')
            if not detail_link:
                continue
                
            # 2. 법령 상세 조회 (제공된 링크에서 type을 XML로 변경)
            detail_link = detail_link.replace('type=HTML', 'type=XML')
            detail_url = f"https://www.law.go.kr{detail_link}"
            
            # 만약 상세조회 API 경로가 다를 수 있으므로 예외 처리
            try:
                with urllib.request.urlopen(detail_url) as detail_response:
                    detail_xml = detail_response.read().decode('utf-8')
                detail_root = ET.fromstring(detail_xml)
            except urllib.error.HTTPError:
                detail_root = root

            # 조문 태그(<조문단위>)를 순회하며 키워드가 포함된 조문 발췌
            jo_list = detail_root.findall('.//조문단위')
            law_results = []
            
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
                    
                law_results.append({
                    "법령명": law.findtext('법령명한글', law_name), # 실제 반환된 법령명 사용
                    "조문번호": jo_num,
                    "조문제목": jo_title,
                    "조문내용": full_content.strip()
                })
                
                # 각 법령별로 limit(기본 30개 등)만큼만 발췌하여 부하 방지
                if len(law_results) >= limit:
                    break
            
            results.extend(law_results)
                
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
