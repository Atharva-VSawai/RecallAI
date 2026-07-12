# 🚀 Quick Start: File Selection Feature

## Setup (No Additional Configuration Needed!)

The file selection feature is **automatically enabled** with your existing setup. No new environment variables or dependencies required.

---

## 📋 How to Use

### Option 1: Select from Existing Files

1. **Go to Homepage** (`http://localhost:3000`)

2. **Click "Select Existing File"** button
   - A dialog will open showing all previously uploaded files

3. **Browse or Search**
   - Use the search bar to find files by name or type
   - Files are sorted by upload date (newest first)

4. **Select a File**
   - Click on any file card to select it
   - Selected file will be highlighted with a checkmark

5. **Query the File**
   - Click "Query Selected File" button
   - You'll be redirected to the query page with the file context loaded
   - Ask questions specific to that file

### Option 2: Upload New File

1. **Go to Homepage** (`http://localhost:3000`)

2. **Click "Upload New File"** button
   - You'll be redirected to the query page

3. **Choose Upload Tab**
   - PDF, Excel, Audio/Video, or Image

4. **Upload Your File**
   - Drag & drop or click to browse
   - System automatically checks for duplicates

5. **If Duplicate Detected**
   - You'll see a message: "File already uploaded on [date]"
   - No re-processing needed
   - Context is automatically set

6. **If New File**
   - File is processed and stored
   - Context is automatically set
   - You can immediately query it

---

## 🎯 Key Features

### ✅ Automatic Duplicate Detection
- Files are identified by content (SHA256 hash), not filename
- Prevents wasting time and resources on re-processing
- Shows when file was originally uploaded

### 🔍 Smart Search
- Search by filename
- Filter by file type
- Real-time results

### 📁 File Type Support
- **Documents**: PDF, Excel (.xlsx, .xls)
- **Images**: PNG, JPG, JPEG, GIF, WebP
- **Audio**: MP3, WAV, M4A, FLAC, OGG
- **Video**: MP4, MOV, AVI, MKV, WebM

### 🎨 Visual Indicators
- File type icons (📄 📊 🖼️ 🎵 🎬)
- Upload dates
- Selection highlighting
- Context banner in query page

---

## 💡 Usage Tips

### Tip 1: Context-Aware Querying
When you select a file, all queries are automatically filtered to that file only:
```
✅ Context Active: 📄 meeting_notes.pdf
Your Question: "What decisions were made?"
→ Results only from meeting_notes.pdf
```

### Tip 2: Clear Context to Query All Files
Click the ❌ button in the context banner to query across all files:
```
❌ Context Cleared
Your Question: "What decisions were made?"
→ Results from ALL uploaded files
```

### Tip 3: Direct File Links
Share specific file contexts with your team:
```
http://localhost:3000/query?source=document:report.pdf&filename=report.pdf
```

### Tip 4: Rename Files Before Upload
Since duplicates are detected by content, renaming a file won't bypass detection:
```
report.pdf → report_v2.pdf
❌ Still detected as duplicate (same content)
```

---

## 🔄 Common Workflows

### Workflow 1: Daily Standup Notes
1. Upload standup notes PDF every day
2. Each file is tracked separately
3. Query specific day: Select file from homepage
4. Query all standups: Clear context and ask

### Workflow 2: Meeting Recordings
1. Upload meeting audio/video files
2. System transcribes and extracts decisions
3. Select specific meeting from homepage
4. Ask questions about that meeting

### Workflow 3: Project Documentation
1. Upload multiple project PDFs
2. Browse files by date or name
3. Select relevant document
4. Get context-specific answers

---

## 🐛 Troubleshooting

### Problem: File not showing in list
**Solution:**
- Refresh the page
- Check if upload completed successfully
- Verify backend is running (`http://localhost:8000/health`)

### Problem: Duplicate not detected
**Solution:**
- Ensure file content is identical (not just filename)
- Check if file was modified
- Verify backend logs for errors

### Problem: Context not loading
**Solution:**
- Check URL parameters are correct
- Clear browser cache
- Try selecting file again from homepage

### Problem: Search not working
**Solution:**
- Type at least 2 characters
- Check spelling
- Try searching by file type instead

---

## 📊 Example Scenarios

### Scenario 1: Quarterly Review
```
1. Upload Q1, Q2, Q3, Q4 reports
2. Homepage → Select "Q3_report.pdf"
3. Query: "What were the key challenges in Q3?"
4. Get Q3-specific insights
```

### Scenario 2: Team Decisions
```
1. Upload multiple meeting notes
2. Homepage → Select "2024-01-15_meeting.pdf"
3. Query: "Who decided on the new architecture?"
4. Get decision makers from that specific meeting
```

### Scenario 3: Cross-Document Analysis
```
1. Upload multiple documents
2. Homepage → Don't select any file
3. Go to query page
4. Query: "What's the common theme across all documents?"
5. Get insights from entire knowledge base
```

---

## 🎓 Best Practices

1. **Use Descriptive Filenames**
   - ✅ `2024-01-15_standup_notes.pdf`
   - ❌ `notes.pdf`

2. **Upload Regularly**
   - Build your knowledge base over time
   - More data = better insights

3. **Use Context Wisely**
   - Select file for specific questions
   - Clear context for broad questions

4. **Organize by Date**
   - Files are sorted by upload date
   - Recent files appear first

5. **Search Efficiently**
   - Use file type filters
   - Search by date in filename
   - Use partial matches

---

## 🚀 Next Steps

1. **Upload Your First File**
   - Try with a PDF or Excel file
   - See how decisions are extracted

2. **Explore File Selection**
   - Upload a few more files
   - Practice selecting and querying

3. **Test Duplicate Detection**
   - Try uploading the same file twice
   - See the duplicate message

4. **Share with Team**
   - Share file context URLs
   - Collaborate on insights

---

## 📚 Additional Resources

- **Full Documentation**: See `FILE_SELECTION_FEATURE.md`
- **API Reference**: See main `README.md`
- **Architecture**: See architecture diagrams in docs

---

**Happy Querying! 🎉**

If you have questions or issues, check the troubleshooting section or review the full documentation.
