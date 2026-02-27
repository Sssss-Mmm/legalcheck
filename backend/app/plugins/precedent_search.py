import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# Load API Key from environment or use the one provided by user
API_KEY = os.environ.get("LAW_GO_KR_API_KEY", "0d61d99fc6869f68a814c2cf2b2ab6f232f6e2b2e7e2554ba04b7ac61c6c10f4")

def search_precedents(keywords: list) -> list:
    """
    국가법령정보센터(LAW.GO.KR) Open API를 활용하여 실제 판례/법령해석례를 검색합니다.
    (law.go.kr 대신 스크린샷에 명시된 data.go.kr 엔드포인트 적용)
    """
    if not keywords:
        return []
    
    query = " ".join(keywords)
    encoded_query = urllib.parse.quote(query)
    
    # 스크린샷의 End Point 적용
    base_url = "https://apis.data.go.kr/1170000/law"
    
    # 스크린샷 메뉴에 명시된 법령해석례(expcSearchList.do) 또는 판례(precSearchList.do) 호출
    search_url = f"{base_url}/precSearchList.do?serviceKey={API_KEY}&target=prec&type=XML&query={encoded_query}&display=3"
    
    results = []
    try:
        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req) as response:
            xml_data = response.read().decode('utf-8')
            
        root = ET.fromstring(xml_data)
        
        for prec in root.findall('.//prec'):
            prec_no = prec.findtext('판례일련번호')
            case_name = prec.findtext('사건명')
            case_no = prec.findtext('사건번호')
            court = prec.findtext('선고국가') 
            if not court:
                court = prec.findtext('선고법원')
            date = prec.findtext('선고일자')
            
            # 상세조회 API (목록에 없을 경우 본문 활용)
            detail_url = f"{base_url}/precService.do?serviceKey={API_KEY}&target=prec&ID={prec_no}&type=XML"
            
            try:
                with urllib.request.urlopen(detail_url) as detail_response:
                    detail_xml = detail_response.read().decode('utf-8')
                detail_root = ET.fromstring(detail_xml)
            except urllib.error.HTTPError:
                detail_root = root # Fallback
            
            prec_info = detail_root.findtext('.//판결요지', '')
            if not prec_info or prec_info.strip() == "":
                prec_info = detail_root.findtext('.//판례내용', '')
                
            if prec_info and len(prec_info) > 1000:
                prec_info = prec_info[:1000] + "...(중략)"
                
            results.append({
                "사건명": case_name,
                "사건번호": f"{court} {date} 선고 {case_no}",
                "판결요지": prec_info.strip() if prec_info else "내용 없음"
            })
            
    except Exception as e:
        print(f"Error fetching precedent from DATA.GO.KR: {e}")
        # API 인증 대기(1~2시간) 혹은 네트워크 오류 시 Fallback
        results.append({
            "사건명": f"판례 검색 대기 (키워드: {query})",
            "사건번호": "데이터포털 연동 중",
            "판결요지": f"공공데이터포털 API 연동 대기 중이거나 해당 스펙을 지원하지 않습니다. 에러내용: {e}"
        })
            
    return results
