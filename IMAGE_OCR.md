# 📸 Image OCR Feature

## Overview

The Image OCR feature allows you to upload images containing text (screenshots, whiteboards, documents, notes) and automatically extract decisions and organizational knowledge using Groq's Vision API.

## How It Works

```
┌─────────────────┐
│  Upload Image   │
│  (PNG/JPG/etc)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Groq Vision API (OCR)      │
│  llama-3.2-90b-vision       │
│  Extracts all text          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Ingestion Agent            │
│  Extracts decisions         │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Store in Neo4j + ChromaDB  │
│  Ready for querying         │
└─────────────────────────────┘
```

## Supported Formats

- **PNG** - Portable Network Graphics
- **JPG/JPEG** - Joint Photographic Experts Group
- **GIF** - Graphics Interchange Format
- **WebP** - Modern web image format

## Use Cases

1. **Whiteboard Sessions**: Capture decisions from team whiteboard photos
2. **Screenshots**: Extract decisions from Slack/email screenshots
3. **Scanned Documents**: Process scanned meeting notes or memos
4. **Handwritten Notes**: Extract text from photos of handwritten notes
5. **Presentation Slides**: Capture decisions from slide screenshots

## API Endpoint

### `POST /ingest/image`

**Request:**
```bash
curl -X POST http://localhost:8000/ingest/image \
  -F "file=@whiteboard.png"
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "ingested": 2,
    "items": [
      {
        "decision": "Migrate to microservices architecture",
        "reason": "Better scalability and team autonomy",
        "people": ["Alice", "Bob"],
        "topic": "architecture",
        "decision_id": "uuid-here"
      }
    ]
  },
  "extracted_text": "Full OCR text here..."
}
```

## Frontend Usage

1. Navigate to `/query`
2. Click the **Image OCR** tab
3. Upload your image (drag & drop or click to browse)
4. Click **Extract Text & Ingest**
5. View extracted text and ingestion results
6. Query the decisions immediately

## Technical Details

### Model
- **Groq Vision API**: `meta-llama/llama-4-scout-17b-16e-instruct`
- **Temperature**: 0 (deterministic)
- **Max Tokens**: 4096

### Processing Steps
1. Image converted to base64
2. Sent to Groq Vision API with extraction prompt
3. Text extracted and returned
4. Passed to Ingestion Agent
5. Decisions extracted and stored in Neo4j
6. Raw text stored in ChromaDB

### Source Filtering
After ingestion, you can filter queries to only search within that image:
- Source context: `image:filename.png`
- Automatically set when you click "Query this now"

## Error Handling

The system handles:
- Invalid image formats
- Large file sizes
- OCR failures
- Network errors
- Ingestion errors

All errors are displayed in the UI with clear messages.

## Performance

- **OCR Time**: ~5-10 seconds for typical images
- **Ingestion Time**: ~3-5 seconds
- **Total Time**: ~10-15 seconds end-to-end

## Limitations

1. **Image Quality**: Better quality = better OCR results
2. **Text Density**: Very dense text may be truncated
3. **Handwriting**: Works best with clear handwriting
4. **Language**: Optimized for English text

## Example Workflow

```python
# Backend example
from ingestion.image import extract_text_from_image

# Read image file
with open("meeting_notes.png", "rb") as f:
    image_bytes = f.read()

# Extract text
text = extract_text_from_image(image_bytes, "meeting_notes.png")

# Text is now ready for ingestion
from agents.ingestion_agent import run_ingestion_agent
result = run_ingestion_agent(content=text, source="image:meeting_notes.png")
```

## Tips for Best Results

1. **High Resolution**: Use clear, high-resolution images
2. **Good Lighting**: Ensure text is clearly visible
3. **Straight Angles**: Avoid skewed or rotated images
4. **Contrast**: High contrast between text and background
5. **Focus**: Ensure text is in focus, not blurry

## Integration with Existing Features

The Image OCR feature integrates seamlessly with:
- **Query Agent**: Search decisions from images
- **Impact Agent**: Analyze impact of decisions from images
- **Source Filtering**: Query only image-sourced decisions
- **Activity Timeline**: Track image ingestion events

## Future Enhancements

- [ ] Batch image upload
- [ ] Image preprocessing (rotation, contrast adjustment)
- [ ] Multi-language support
- [ ] Table extraction
- [ ] Diagram understanding
- [ ] Handwriting-specific models
