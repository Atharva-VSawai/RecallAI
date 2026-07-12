# 📸 Image OCR - Quick Reference

## 🚀 Quick Start

### Frontend (Recommended)
1. Go to `http://localhost:3000/query`
2. Click **Image OCR** tab
3. Upload image (PNG, JPG, GIF, WebP)
4. Click **Extract Text & Ingest**
5. Done! Query your image content

### API
```bash
curl -X POST http://localhost:8000/ingest/image \
  -F "file=@your_image.png"
```

## 📋 Supported Formats
- PNG, JPG, JPEG, GIF, WebP

## 🔧 Tech Stack
- **OCR Model**: Groq Vision API (`meta-llama/llama-4-scout-17b-16e-instruct`)
- **Storage**: Neo4j (decisions) + ChromaDB (raw text)
- **Processing**: Same ingestion agent as PDF/Audio

## 📁 Key Files
```
backend/
  ├── ingestion/image.py          # OCR logic
  └── main.py                     # /ingest/image endpoint

frontend/
  ├── lib/api.ts                  # ingestImage() function
  └── app/query/page.tsx          # Image OCR tab UI
```

## 🎯 Common Use Cases
1. Whiteboard photos → Decisions
2. Screenshots → Searchable text
3. Scanned docs → Knowledge base
4. Handwritten notes → Digital records

## ⚡ Performance
- OCR: ~5-10 seconds
- Ingestion: ~3-5 seconds
- Total: ~10-15 seconds

## 🔍 Query After Upload
After uploading an image, queries are automatically filtered to that source:
```
Source context: "image:filename.png"
```

## 🎨 UI States
- **Idle**: Upload zone ready
- **Loading**: OCR in progress (progress bar)
- **Success**: Shows extracted text + ingestion result
- **Error**: Clear error message with retry

## 💡 Tips for Best Results
1. Use high-resolution images
2. Ensure good lighting/contrast
3. Avoid blurry or skewed images
4. Clear, readable text works best

## 🐛 Troubleshooting

**OCR fails?**
- Check image format (must be PNG/JPG/GIF/WebP)
- Ensure text is visible and clear
- Try a different image

**Nothing extracted?**
- Image may not contain decision keywords
- Check extracted text preview
- Raw text still stored in ChromaDB

**API error?**
- Verify Groq API key in `.env`
- Check backend logs
- Ensure backend is running

## 📚 Full Documentation
See `IMAGE_OCR.md` for complete documentation.

## ✅ Feature Checklist
- [x] Backend OCR module
- [x] API endpoint
- [x] Frontend UI
- [x] Source filtering
- [x] Activity logging
- [x] Error handling
- [x] Progress indicators
- [x] Documentation

**Status: ✅ Production Ready**
