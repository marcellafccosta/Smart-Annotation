#config.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+pg8000://postgres:root@localhost/imscience"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            print("Conexão bem-sucedida!")
    except Exception as e:
        print(f"Erro ao conectar: {e}")
