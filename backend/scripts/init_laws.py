import os
import asyncio
import logging
from app.core.database import SessionLocal, engine
from app.models import Base, Law
from app.core.container import get_services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_ingestion():
    # Make sure tables exist
    Base.metadata.create_all(bind=engine)
    
    services = get_services()
    pdf_parser = services.pdf_parser
    checker = services.checker

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    if not os.path.exists(data_dir):
        logger.error(f"Data dir not found: {data_dir}")
        return

    pdf_files = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]
    if not pdf_files:
        logger.info("No PDF files found.")
        return

    db = SessionLocal()
    try:
        for file_name in pdf_files:
            law_name = file_name.split("(")[0].strip()
            
            # Check if law already exists
            existing_law = db.query(Law).filter(Law.name == law_name).first()
            if existing_law:
                logger.info(f"Law {law_name} already exists. Skipping ingestion for {file_name}.")
                continue
                
            logger.info(f"Creating Law entry for: {law_name}")
            new_law = Law(name=law_name, jurisdiction="KR")
            db.add(new_law)
            db.commit()
            db.refresh(new_law)
            
            file_path = os.path.join(data_dir, file_name)
            logger.info(f"Reading file: {file_path}")
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            logger.info(f"Parsing PDF and updating DB for: {law_name} ... (This may take a while using LLM)")
            created_articles, embedded_revisions = await pdf_parser.process_pdf(db, new_law.id, file_content)
            
            logger.info(f"Added {len(created_articles)} articles.")
            
            if embedded_revisions:
                logger.info(f"Adding embeddings to Vector Store...")
                checker.add_revisions(embedded_revisions)
                logger.info("Embeddings added successfully.")
                
    except Exception as e:
        db.rollback()
        logger.error(f"Failed during ingestion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_ingestion())
