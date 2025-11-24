from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import os
import socket
import datetime
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="Milestone2 API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': os.getenv('DB_PORT')
}

def get_db_connection():
    """Create database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def init_database():
    """Initialize database schema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL DEFAULT 'John Doe',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default user if table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (name) VALUES ('John Doe')")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()

@app.get("/")
async def root():
    return {"message": "Milestone2 API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")

@app.get("/user")
async def get_user():
    """Get user name from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM users WHERE id = 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {"name": result['name']}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/container_id")
async def get_container_id(response: Response):
    """Get container ID (hostname)"""
    response.headers["Connection"] = "close"
    # Prevent browser/proxy caching so each refresh actually hits the backend
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {"container_id": socket.gethostname(), "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}

@app.put("/user/{name}")
async def update_user(name: str):
    """Update user name"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = %s WHERE id = 1", (name,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"message": "User updated successfully", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)