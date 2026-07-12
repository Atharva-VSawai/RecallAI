# Favicon Update Instructions

## ✅ What Was Done

1. Created `public/brain-icon.svg` - Brain icon matching navbar
2. Updated `app/layout.tsx` - Added icon to metadata

## 🎨 Favicon Details

- **Icon**: Brain (same as navbar)
- **Colors**: Orange to Amber gradient (#f97316 → #f59e0b)
- **Format**: SVG (scalable, crisp at any size)

## 🔄 How to Generate ICO (Optional)

If you want a traditional `.ico` file for older browsers:

### Option 1: Online Converter
1. Go to https://convertio.co/svg-ico/
2. Upload `public/brain-icon.svg`
3. Download as `favicon.ico`
4. Replace `app/favicon.ico`

### Option 2: Using ImageMagick (if installed)
```bash
cd frontend/public
convert brain-icon.svg -define icon:auto-resize=16,32,48,64,256 ../app/favicon.ico
```

### Option 3: Using Node.js (if you want automation)
```bash
npm install sharp svg2img --save-dev
```

Then create `scripts/generate-favicon.js`:
```javascript
const sharp = require('sharp');
const fs = require('fs');

async function generateFavicon() {
  const svg = fs.readFileSync('./public/brain-icon.svg');
  
  await sharp(svg)
    .resize(32, 32)
    .toFile('./app/favicon.ico');
  
  console.log('✓ Favicon generated!');
}

generateFavicon();
```

## 🚀 Current Setup

The SVG favicon will work in all modern browsers:
- ✅ Chrome/Edge
- ✅ Firefox
- ✅ Safari
- ✅ Opera

## 🧪 Test It

1. Restart your Next.js dev server:
   ```bash
   npm run dev
   ```

2. Open http://localhost:3000

3. Check the browser tab - you should see the orange brain icon!

4. Hard refresh if needed: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

## 📁 Files Modified

```
frontend/
├── public/
│   └── brain-icon.svg          ← NEW: Brain icon SVG
└── app/
    └── layout.tsx              ← UPDATED: Added icon metadata
```

## 🎯 Result

Your favicon now matches the navbar icon:
- Same Brain icon
- Same orange gradient colors
- Consistent branding across the app

**Status: ✅ Complete!**
