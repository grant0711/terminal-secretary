import sqlite3
import chromadb
from chromadb.utils import embedding_functions
import os
import datetime

class DatabaseManager:
    def __init__(self, db_path="data/secretary.db", chroma_path="data/chroma"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_sqlite()
        
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="conversations",
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )

    def _init_sqlite(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                transcript TEXT,
                summary TEXT
            )
        """)
        self.conn.commit()

    def save_conversation(self, transcript, summary):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (transcript, summary) VALUES (?, ?)",
            (transcript, summary)
        )
        conv_id = cursor.lastrowid
        self.conn.commit()
        
        # Add to Chroma for semantic search
        self.collection.add(
            documents=[summary],
            metadatas=[{"id": conv_id, "timestamp": str(datetime.datetime.now())}],
            ids=[str(conv_id)]
        )
        return conv_id

    def search(self, query, n_results=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
