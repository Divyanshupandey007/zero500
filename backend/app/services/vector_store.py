import psycopg
from pgvector.psycopg import register_vector
from google import genai
from google.genai import types
from typing import List, Dict,Any
from app.config import settings

class VectorStore:
    def __init__(self):
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set in .env")
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMEINI_API_KEY is not set in .env")
        self.gemini_client=genai.Client(api_key=settings.GEMINI_API_KEY)

    def get_connection(self):
        """Open connection and register the pgvector type handler"""
        conn=psycopg.connect(settings.DATABASE_URL)
        register_vector(conn)
        return conn

    def get_embedding(self,text:str)->List[float]:
        """Generate 768-dimensional embedding vector using embedding model"""
        response=self.gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=768
            ),
        )
        return response.embeddings[0].values

    def init_db(self):
        """Initializes tables and pgvector extension"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
CREATE TABLE IF NOT EXISTS runbooks(
id SERIAL PRIMARY KEY,
title VARCHAR(255) NOT NULL,
service VARCHAR(100) NOT NULL,
doc_type VARCHAR(50) NOT NULL,
content TEXT NOT NULL,
embedding vector(768)
);
""")
                conn.commit()

    def search_similar_docs(self,query_text:str,limit:int=2)->List[Dict[str,Any]]:
        """Perform cosine similarity search using pgvector(<=> operator)"""
        query_vector=self.get_embedding(query_text)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
SELECT id,title,service,doc_type,content,
1 - (embedding <=> %s::vector) AS similarity_score
FROM runbooks
ORDER BY embedding <=> %s::vector ASC
LIMIT %s;
""",(query_vector,query_vector,limit)
                            )
                rows=cur.fetchall()
                results=[]
                for row in rows:
                    results.append({
                        "id":row[0],
                        "title":row[1],
                        "service":row[2],
                        "doc_type":row[3],
                        "content":row[4],
                        "similarity_score":round(float(row[5]),3)
                    })
                return results

vector_store=VectorStore()