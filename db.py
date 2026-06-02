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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                task_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
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

    def add_todo(self, task_text, conversation_id=None):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO todos (task_text, conversation_id) VALUES (?, ?)",
            (task_text, conversation_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_todos(self, status=None):
        cursor = self.conn.cursor()
        if status:
            cursor.execute("SELECT id, task_text, status, created_at FROM todos WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT id, task_text, status, created_at FROM todos ORDER BY created_at DESC")
        return cursor.fetchall()

    def mark_todo_done(self, todo_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE todos SET status = 'done', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (todo_id,)
        )
        self.conn.commit()

    def remove_todo(self, todo_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self.conn.commit()

    def get_conversations_in_range(self, start_date, end_date):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, summary FROM conversations WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
            (start_date, end_date)
        )
        return cursor.fetchall()

    def search(self, query, n_results=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
