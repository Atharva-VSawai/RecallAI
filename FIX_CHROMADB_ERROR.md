# Fix: "No module named 'chromadb'" Error

## Problem
The backend dependencies are not installed, causing the error:
```
500 Internal Server Error
"detail": "No module named 'chromadb'"
```

## Solution

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Activate Virtual Environment (if you have one)

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### Step 3: Install All Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- fastapi, uvicorn
- pymupdf (PDF processing)
- openpyxl, pandas (Excel processing)
- langchain, langgraph, langchain-groq
- neo4j (Graph database)
- chromadb, langchain-chroma (Vector database) ← This fixes your error
- slack-sdk (Slack integration)
- groq (Audio transcription)
- And all other dependencies

### Step 4: Restart Backend Server
```bash
uvicorn main:app --reload
```

### Step 5: Test
- Go to http://localhost:3000/query
- Try uploading a PDF or Excel file
- Try querying the knowledge base

## Alternative: Install Specific Package Only
If you only want to fix the chromadb error:
```bash
pip install chromadb langchain-chroma
```

## Verify Installation
Check if chromadb is installed:
```bash
pip list | grep chroma
```

You should see:
```
chromadb              x.x.x
langchain-chroma      x.x.x
```

## Common Issues

### Issue 1: pip not found
**Solution:** Make sure Python is installed and added to PATH

### Issue 2: Permission denied
**Solution:** 
- Windows: Run terminal as Administrator
- macOS/Linux: Use `pip install --user -r requirements.txt`

### Issue 3: Virtual environment not activated
**Solution:** Activate venv first (see Step 2)

### Issue 4: Old pip version
**Solution:** 
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## After Installation
Your backend should work properly with:
- ✅ PDF upload and ingestion
- ✅ Excel upload and ingestion
- ✅ Audio/Video transcription
- ✅ Slack channel ingestion
- ✅ Natural language queries
- ✅ Neo4j graph storage
- ✅ ChromaDB vector storage
