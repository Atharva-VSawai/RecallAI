# Deployment Guide: Vercel & Render

This guide outlines how to deploy the **Recall.AI** platform using the optimal setup: **Vercel** for the Next.js frontend (blazing fast Edge delivery) and **Render** for the FastAPI backend (longer timeouts for AI processing).

---

## 1. Deploy the Backend (Render)

Render is perfect for the Python backend because it supports long-running processes (like large document ingestions) without the strict 10-second serverless timeouts that Vercel enforces.

We have included a `render.yaml` Blueprint file, making this a 1-click setup.

1. Create an account at [Render.com](https://render.com) and link your GitHub account.
2. In the Render Dashboard, click **New +** and select **Blueprint**.
3. Select this repository from the list.
4. Render will automatically detect the `render.yaml` file and configure the Web Service with the correct build command (`pip install -r requirements.txt`) and start command (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
5. Click **Apply**.
6. **Set Environment Variables**: In the Render dashboard, go to your new Web Service -> **Environment** and add the following missing keys (copied from your local `.env`):
   - `SUPABASE_URL`
   - `SUPABASE_PUBLISHABLE_KEY`
   - `SUPABASE_JWT_ISSUER`
   - `GROQ_API_KEY`
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
   - `CHROMA_API_KEY`, `CHROMA_TENANT`
   - `COHERE_API_KEY`
   - `SLACK_BOT_TOKEN`

> ⏳ **Note:** The first build might take a few minutes as it installs Python dependencies. Once deployed, note down the Render URL (e.g., `https://recall-ai-backend.onrender.com`).

---

## 2. Deploy the Frontend (Vercel)

Vercel provides the absolute best experience for Next.js applications.

1. Create an account at [Vercel.com](https://vercel.com) and link your GitHub account.
2. Click **Add New...** -> **Project**.
3. Import this repository.
4. **IMPORTANT: Set the Root Directory**:
   - In the project configuration screen, click **Edit** next to "Root Directory".
   - Select the `frontend` folder and click Continue.
5. **Set Environment Variables**: Expand the Environment Variables section and add:
   - `NEXT_PUBLIC_SUPABASE_URL`: (Your Supabase URL)
   - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`: (Your Supabase Anon/Publishable Key)
   - `NEXT_PUBLIC_API_URL`: **Set this to your Render Backend URL** (e.g., `https://recall-ai-backend.onrender.com`). *Make sure there is no trailing slash!*
6. Click **Deploy**.

---

## 3. Final Step: Configure CORS on Render

Once your Vercel frontend is deployed, Vercel will give you a public URL (e.g., `https://recall-ai-frontend.vercel.app`).

For security, the Render backend needs to know that this Vercel domain is allowed to make API requests to it.

1. Copy your Vercel frontend URL.
2. Go back to the **Render Dashboard** -> Web Service -> **Environment**.
3. Edit the `CORS_ORIGINS` variable (which was set as a placeholder) and replace it with your Vercel URL.
   *Example: `https://recall-ai-frontend.vercel.app`*
4. Save the changes. Render will briefly restart your backend service.

---

### 🎉 You're Done!
Your application is now fully deployed. The frontend is served globally via Vercel's Edge Network, and your AI backend is securely processing data on Render.
