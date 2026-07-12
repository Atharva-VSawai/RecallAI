# 🧪 Comprehensive Test Cases - Anti-Hallucination & Source Filtering

## ✅ Fixes Implemented

### 1. **Query Agent Enhancements**
- Added strict source filtering enforcement
- Explicit anti-hallucination rules
- Context message when source_filter is active
- Limited raw content to 300 chars
- Prioritize structured decisions over raw data

### 2. **Impact Agent Enhancements**
- Same anti-hallucination rules
- Source filtering enforcement
- Limited result previews

### 3. **ChromaDB Tool**
- Reduced results from 4 to 3
- Truncate content to 300 chars max
- Proper source filtering with `where` clause

### 4. **System Prompts**
- "ONLY answer based on tool results"
- "NEVER make up information"
- "If no results, say 'No information found'"
- "NEVER use general knowledge"

---

## 🧪 Test Cases

### Test 1: PDF File Query
**Setup:**
1. Select `internal_notes_engineering_ops.pdf` from homepage
2. Context banner should show: 📄 internal_notes_engineering_ops.pdf

**Test Queries:**
```
Q: "What decisions were made?"
Expected: List decisions ONLY from this PDF
Should NOT include: Decisions from audio, Excel, or other files

Q: "Who made the database decision?"
Expected: Names from this PDF only
Should NOT include: Names from other sources

Q: "Tell me about the authentication changes"
Expected: Info from this PDF only, or "No information found" if not in PDF
```

---

### Test 2: Excel File Query
**Setup:**
1. Select `decisions.xlsx` from homepage
2. Context banner should show: 📊 decisions.xlsx

**Test Queries:**
```
Q: "What are the key decisions?"
Expected: Decisions ONLY from Excel file
Should NOT include: Audio transcript decisions

Q: "Why was this decision made?"
Expected: Reasons from Excel only, or "No information found"

Q: "Who was involved?"
Expected: People from Excel only
```

---

### Test 3: Audio File Query
**Setup:**
1. Select `speech_20260410114950682.mp3` from homepage
2. Context banner should show: 🎵 speech_20260410114950682.mp3

**Test Queries:**
```
Q: "What decisions were made in the meeting?"
Expected: Structured summary (PostgreSQL, hiring freeze, Supabase)
Should NOT: Return entire transcript
Should NOT: Include decisions from other files

Q: "Why did they choose PostgreSQL?"
Expected: "MongoDB had scaling issues and outages" (concise)
Should NOT: Return full transcript

Q: "Who led the database migration?"
Expected: "Mark" only
Should NOT: Include people from other sources

Q: "What was the hiring decision?"
Expected: "Hiring freeze for Q2-Q3 with one exception for senior backend engineer"
Should NOT: Return transcript dump
```

---

### Test 4: Image/OCR File Query
**Setup:**
1. Select `ocr_test.jpeg` from homepage
2. Context banner should show: 🖼️ ocr_test.jpeg

**Test Queries:**
```
Q: "What information is in this image?"
Expected: Extracted text content from OCR
Should NOT: Include content from other files

Q: "What decisions are mentioned?"
Expected: Decisions from image only, or "No information found"
```

---

### Test 5: Slack Channel Query
**Setup:**
1. Select `#C0ARX8F28PQ` from homepage
2. Context banner should show: 💬 #C0ARX8F28PQ

**Test Queries:**
```
Q: "What was discussed in this channel?"
Expected: Decisions/discussions from this Slack channel only
Should NOT: Include decisions from files

Q: "Who participated?"
Expected: People from this channel only
```

---

### Test 6: Upload New File
**Setup:**
1. Go to homepage → "Upload New File"
2. Upload a new PDF/Excel/Audio file
3. After upload, context should auto-set

**Test Queries:**
```
Q: "What's in this file?"
Expected: Content from newly uploaded file only
Should NOT: Include old files

Q: "Summarize the decisions"
Expected: Decisions from new file only
```

---

### Test 7: No Context (All Files)
**Setup:**
1. Go to query page directly (no file selected)
2. OR clear context banner by clicking X

**Test Queries:**
```
Q: "What decisions were made?"
Expected: Decisions from ALL files in database
Should: Cite multiple sources

Q: "Who decided on PostgreSQL?"
Expected: Search across all sources, cite source
```

---

### Test 8: Cross-File Contamination Test
**Setup:**
1. Select audio file (has PostgreSQL decision)
2. Ask about something NOT in audio

**Test Queries:**
```
Q: "What decisions are in the Excel file?"
Expected: "No information found in the selected file/source"
Should NOT: Return Excel content (wrong source)
Should NOT: Hallucinate or use general knowledge

Q: "Tell me about React vs Vue"
Expected: "No information found in the selected file/source"
Should NOT: Use general knowledge about React/Vue
```

---

### Test 9: Impact Analysis with Source Filter
**Setup:**
1. Select audio file
2. Ask impact question

**Test Queries:**
```
Q: "What would break if we don't migrate to PostgreSQL?"
Expected: Impact analysis based ONLY on audio file content
Should NOT: Include impacts from other sources

Q: "What's the risk of the hiring freeze?"
Expected: Risk analysis from audio file only
```

---

### Test 10: Empty Results Handling
**Setup:**
1. Select a file
2. Ask about something definitely not in it

**Test Queries:**
```
Q: "What decisions were made about blockchain?"
Expected: "No information found in the selected file/source"
Should NOT: Hallucinate blockchain decisions
Should NOT: Use general knowledge

Q: "Who is the CEO?"
Expected: "No information found" (unless actually in file)
Should NOT: Make up names
```

---

## 🎯 Success Criteria

### ✅ PASS Conditions:
1. **Source Isolation**: Answers only use data from selected source
2. **No Hallucination**: Never makes up information
3. **Concise Answers**: No transcript dumps, synthesized responses
4. **Proper Citations**: Always cites source
5. **Empty Handling**: Says "No information found" when appropriate
6. **Context Awareness**: Respects source_filter parameter

### ❌ FAIL Conditions:
1. Returns data from wrong source
2. Makes up information not in tools
3. Returns entire transcripts
4. Uses general knowledge instead of retrieved data
5. Doesn't cite sources
6. Ignores source_filter

---

## 🔍 How to Verify

### Check Source Trace:
In the response, look at `source_trace`:
```json
{
  "source_trace": [
    {
      "tool": "search_decisions",
      "args": {
        "query": "...",
        "source_filter": "audio:speech_20260410114950682.mp3"
      },
      "result_preview": "..."
    }
  ]
}
```

Verify:
- `source_filter` is present and correct
- Tool results match the selected source
- Answer only uses information from tool results

### Check Answer Quality:
- ✅ Concise and direct
- ✅ Cites source
- ✅ No transcript dumps
- ✅ No hallucinated info
- ✅ Says "No information found" when appropriate

---

## 🐛 If Tests Fail

### Issue: Returns data from wrong source
**Fix:** Check that source_filter is being passed correctly through the chain

### Issue: Hallucinating information
**Fix:** Check system prompts have anti-hallucination rules

### Issue: Returning transcripts
**Fix:** Check ChromaDB tool is truncating content to 300 chars

### Issue: Not respecting source filter
**Fix:** Check Neo4j and ChromaDB queries use WHERE clause with source_filter

---

## 📊 Test Results Template

```
Test Case: [Name]
File Selected: [filename]
Query: [question]
Expected: [expected behavior]
Actual: [actual response]
Status: ✅ PASS / ❌ FAIL
Notes: [any observations]
```

---

## 🚀 Quick Test Script

1. **Select audio file** → Ask "What decisions were made?"
   - Should get: PostgreSQL, hiring freeze, Supabase (concise)
   - Should NOT get: Entire transcript

2. **Select Excel file** → Ask "What decisions were made?"
   - Should get: Only Excel decisions
   - Should NOT get: Audio decisions

3. **Select audio file** → Ask "What's in the Excel file?"
   - Should get: "No information found in the selected file/source"
   - Should NOT get: Excel content

4. **Clear context** → Ask "What decisions were made?"
   - Should get: Decisions from ALL sources
   - Should cite multiple sources

5. **Select PDF** → Ask "Who is Elon Musk?"
   - Should get: "No information found" (unless in PDF)
   - Should NOT get: General knowledge about Elon Musk

---

**All tests should PASS with the implemented fixes!** ✅
