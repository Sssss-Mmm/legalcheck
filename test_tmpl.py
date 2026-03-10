import asyncio
import sys
import os

# Ensure the backend directory is in the python path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.template_service import DocumentTemplateGenerator

async def test_generator():
    generator = DocumentTemplateGenerator()
    try:
        res = await generator.generate_template("월급을 2달째 못받았어 제발 도와줘", "근로기준법 36조 위반으로 14일 이내 못받으면 처벌 대상입니다.")
        print(f"Title: {res.get('document_title')}")
        print(f"Content:\n{res.get('document_content')}")
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_generator())
