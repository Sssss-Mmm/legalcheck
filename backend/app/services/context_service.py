from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class ContextCompressor:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # gpt-4o-mini is cost effective and good enough for summarization
        self.parser = StrOutputParser()

    async def compress_documents(self, query: str, docs: list) -> str:
        """
        RAG 파이프라인에서 검색된 방대한 텍스트 문서들 중에서 
        사용자의 질문과 관련된 핵심 내용만 발췌하여 압축된 형태의 컨텍스트를 생성합니다.
        """
        if not docs:
            return ""
            
        raw_context = "\n\n".join([f"--- 문서 (출처: {d.metadata.get('source', '알 수 없음')}) ---\n{d.page_content}" for d in docs])
        
        system_prompt = """당신은 법률/규정 팩트체크 시스템을 위한 'Context 압축기'입니다.
아래 제공된 [검색된 문서(법 조문, 판례 등)] 원문에서, 
사용자의 [질문]에 답변하는 데 꼭 필요한 핵심 규칙/조건/제외사항만 선별하여 간결하게 발췌 및 요약하세요.

**압축 규칙:**
1. 사용자의 질문과 무관한 법 조항이나 판례 내용은 과감히 버리세요.
2. 각 문서의 출처(조문 번호, 판례 번호 등)를 명시하면서, 핵심 내용을 3~5줄 이내의 개조식(Bullet points)으로 정리하세요.
3. 질문에서 답변을 내릴 수 없는 내용이라도, 질문과 연관된 조문이 있다면 그 조항의 원칙만 간략히 요약하세요.
4. 당신의 개인적인 해석이나 창작을 더하지 마세요. 문서에 있는 사실 그대로 발췌하되 길이만 줄이세요.
5. "이 조항에 따르면..." 같은 불필요한 서술어를 빼고 명사형이나 간결한 문장형태로 쓰세요.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "[질문]: {query}\n\n[검색된 문서]:\n{raw_context}\n\n위 문서를 기반으로 필수 정보만 압축해 주세요.")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            compressed_context = await chain.ainvoke({
                "query": query,
                "raw_context": raw_context
            })
            return compressed_context
        except Exception as e:
            print(f"Context compression failed: {e}")
            # Fallback to the raw context format if LLM fails
            return raw_context
