# ⚡ PharmaLens Quick Start Guide

Get PharmaLens running in **5 minutes**!

---

## 🎯 Prerequisites

- **Node.js** 18+ (for frontend & API gateway)
- **Python** 3.9+ (for AI engine)
- **npm** or **yarn** (package manager)

---

## 🚀 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/ritik0506/PharmaLens.git
cd PharmaLens
```

### Step 2: Setup Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install Python dependencies
cd ai_engine
pip install -r requirements.txt
```

### Step 3: Setup Node.js Services
```bash
# Install server dependencies
cd ../server
npm install

# Install client dependencies
cd ../client
npm install
```

### Step 4: Configure Environment
```bash
# Create .env file in ai_engine/
cd ../ai_engine
echo "OPENAI_API_KEY=your-key-here" > .env
```

### Step 5: Start Services

**Terminal 1 - AI Engine:**
```bash
cd ai_engine
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - API Server:**
```bash
cd server
npm run dev
```

**Terminal 3 - Frontend:**
```bash
cd client
npm run dev
```

---

## 🎉 Access PharmaLens

Open browser: **http://localhost:5173**

---

## 🧪 Test It

1. Enter a drug name: **"Aspirin"**
2. Select mode: **"Cloud"** (or "Secure" if Llama configured)
3. Click **"Analyze"**
4. Wait 30-60 seconds for multi-agent analysis

---

## 🐛 Troubleshooting

**Port already in use?**
```bash
# Change ports in:
# - ai_engine: uvicorn --port 8001
# - server: PORT=3002 npm run dev
# - client: Edit vite.config.js
```

**AI Engine not connecting?**
- Check `AI_ENGINE_URL` in `server/.env`
- Default: `http://localhost:8000`

**OpenAI errors?**
- Add API key to `ai_engine/.env`
- Get key: https://platform.openai.com

---

## 📚 Next Steps

- [Configure Secure Mode](./SECURE_MODE_SETUP.md)
- [Read Architecture Docs](../architecture/SYSTEM_ARCHITECTURE.md)
- [API Documentation](../api/REST_API.md)
