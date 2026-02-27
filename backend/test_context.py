import asyncio
from app.services.context_service import ContextCompressor
from langchain_core.documents import Document

async def test():
    compressor = ContextCompressor()
    
    # Mocking massive raw documents
    docs = [
        Document(
            page_content="[시행 2021. 11. 19.] [법률 제18176호, 2021. 5. 18., 일부개정] 제26조(해고의 예고) 사용자는 근로자를 해고(경영상 이유에 의한 해고를 포함한다)하려면 적어도 30일 전에 예고를 하여야 하고, 30일 전에 예고를 하지 아니하였을 때에는 30일분 이상의 통상임금을 지급하여야 한다. 다만, 다음 각 호의 어느 하나에 해당하는 경우에는 그러하지 아니하다. 1. 근로자가 계속 근로한 기간이 3개월 미만인 경우 2. 천재ㆍ사변, 그 밖의 부득이한 사유로 사업을 계속하는 것이 불가능한 경우 3. 근로자가 고의로 사업에 막대한 지장을 초래하거나 재산상 손해를 끼친 경우로서 고용노동부령으로 정하는 사유에 해당하는 경우",
            metadata={"source": "근로기준법 제26조"}
        ),
        Document(
            page_content="[시행 2024. 1. 1.] 제27조(해고사유 등의 서면통지) ① 사용자는 근로자를 해고하려면 해고사유와 해고시기를 서면으로 통지하여야 한다. ② 근로자에 대한 해고는 제1항에 따라 서면으로 통지하여야 효력이 있다. ③ 사용자가 제26조에 따른 해고의 예고를 해고사유와 해고시기를 명시하여 서면으로 한 경우에는 제1항에 따른 통지를 한 것으로 본다.",
            metadata={"source": "근로기준법 제27조"}
        )
    ]
    
    query = "회사에서 방금 문자 한통으로 당장 내일부터 나오지 말라고 해고당했어. 나 두 달째 일하고 있었는데 억울해."
    
    print(f"--- [User Query] ---\n{query}\n")
    
    compressed = await compressor.compress_documents(query, docs)
    
    print("--- [Compressed Context by LLM] ---")
    print(compressed)

if __name__ == "__main__":
    asyncio.run(test())
