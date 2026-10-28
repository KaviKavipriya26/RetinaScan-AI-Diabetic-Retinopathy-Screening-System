# RetinaScan AI - Setup & Execution Guide

Follow these simple steps to set up and run both the Backend (FastAPI) and Frontend (React Vite) on any machine after extracting this ZIP file.

---

## 📌 Prerequisites (System Requirements)
Before starting, ensure the following software is installed on your computer:
1. **Python 3.10, 3.11, or 3.12**
   - Download from: https://www.python.org/downloads/
   - ⚠️ **Important:** During Python installation, check the box **"Add Python to PATH"**.
2. **Node.js (v18 or v20+ LTS)**
   - Download from: https://nodejs.org/

---

## ⚙️ Step 1: Run Backend (FastAPI Server)

1. Open a new **PowerShell** or **Command Prompt** (Terminal 1).
2. Navigate to the `backend` directory:
   ```powershell
   cd backend
   ```
3. Create a fresh Python virtual environment:
   ```powershell
   python -m venv venv
   ```
4. Activate the virtual environment:
   - **Windows PowerShell:**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
     *(If script execution is disabled in PowerShell, first run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*
   - **Windows Command Prompt (cmd):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```
5. Install all required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
6. Start the Backend API server:
   ```powershell
   python -m uvicorn main:app --reload --port 8000
   ```
   ✅ *Backend is now active at: `http://localhost:8000`*

---

## 🌐 Step 2: Run Frontend (React Vite Application)

1. Open a second **PowerShell** or **Command Prompt** (Terminal 2).
2. Navigate to the `dr-frontend` directory:
   ```powershell
   cd dr-frontend
   ```
3. Install frontend dependencies:
   ```powershell
   npm install
   ```
4. Start the Vite development server:
   ```powershell
   npm run dev
   ```
   ✅ *Frontend is now active at: `http://localhost:5173`*

---

## 🚀 Step 3: Open in Browser & Login

1. Open your web browser (Chrome / Edge / Firefox) and visit:
   👉 **`http://localhost:5173`**
2. **To Login:**
   - Click the **"Use Demo Credentials"** button for instant one-click login.
   - Or enter credentials manually:
     - **Email:** `doctor@retinascan.ai`
     - **Password:** `Password123`
   - Or click **"Create Account"** to register a new account.
3. **Features to Try:**
   - **Dark Mode / Light Mode:** Click the toggle button at the top right.
   - **Image Upload:** Upload any retinal fundus image (.jpg / .png).
   - **Diagnostic Analysis:** Click "Run Diagnostic Analysis" to view AI Classification, Grad-CAM Heatmap overlay, and 5-class probability chart.
   - **User Manual:** Download the PDF guide directly from the header button.
