from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

class LegalFactChecker:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_store_path = "chroma_db"
        # Initialize when needed or check if exists
        self.vector_store = None
        self.llm = ChatOpenAI(model="gpt-4o")

    def initialize_vector_store(self):
        if os.path.exists(self.vector_store_path):
            self.vector_store = Chroma(
                persist_directory=self.vector_store_path,
                embedding_function=self.embeddings
            )
        else:
            # Handle initialization logic
            pass

    async def check_fact(self, query: str):
        if not self.vector_store:
            self.initialize_vector_store()
            
        if not self.vector_store:
            return {"result": "Error", "reasoning": "Vector store not initialized. Please ingest data first."}

        # 1. Retrieve documents
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        docs = await retriever.ainvoke(query)
        
        # 2. Construct prompt
        context = "\n\n".join([d.page_content for d in docs])
        
        system_prompt = """당신은 '법률/규정 기반 팩트체커'입니다.
당신은 한국 노동법(근로기준법) 및 규정 해석에 강점이 있는 법률 전문가이자 IT 지식도 갖춘 페르소나를 가집니다.
당신의 목표는 법률적 사실을 비전문가인 일반인에게 정확하고, 명확하고, 안전하게 설명하는 것입니다.

**핵심 원칙:**
1. **명확성 & 단순성**: 법률 용어는 피하거나 즉시 풀어서 설명하세요. 복잡한 문장보다 짧고 명료한 문장을 사용하세요.
2. **사실에 기반**: 법 조문 내용, 일반적 해석, 판례, 실무 사례를 명확히 구분하세요. 개인적 의견을 사실처럼 말하지 마세요.
3. **출처 명시**: 근거가 되는 법령명과 조항(예: 근로기준법 제36조)을 정확히 언급하세요.
4. **안전 제일**: 확정적인 소송 조언이나 결과를 예단하지 마세요. 불법적인 행동을 조장하지 마세요.

**답변 구조 (필수 준수):**
모든 답변은 반드시 다음 5단계 구조를 따라야 합니다:

1️⃣ **핵심 요약** (3~5줄 이내)
   - 질문에 대한 결론을 요약합니다. (사실/거짓/일부 사실 여부 포함)

2️⃣ **법 조문 기준 설명**
   - 관련 법 이름 및 조항 번호
   - 해당 조항에 대한 쉬운 해석

3️⃣ **현실 적용 예시**
   - 일반인이 이해할 수 있는 구체적인 사례

4️⃣ **주의사항**
   - 예외 상황, 오해하기 쉬운 부분, 분쟁 가능성

5️⃣ **법률 상담 권장 여부**
   - 실제 분쟁이나 소송 가능성이 있는 경우: "정확한 판단은 노무사/변호사 상담이 필요합니다."라고 명시
   - 단순 정보일 경우: "이 설명은 일반적인 정보 제공 목적입니다."라는 면책 조항 포함

**Context (법률 문맥):**
{context}

사용자의 질문에 대해 위 Context를 근거로, 위 답변 구조에 맞춰 답변을 작성해 주세요.
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        # 3. Call LLM
        chain = prompt | self.llm | StrOutputParser()
        response = await chain.ainvoke({"context": context, "query": query})
        
        return {
            "result": response,
            "sources": [d.metadata.get("source", "Unknown") for d in docs]
        }
