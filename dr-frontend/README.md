# RetinaScan frontend (React + Vite)
1. Backend: put `diabetic_retinopathy_model.keras` inside `backend/`, then
   `pip install -r requirements.txt` and `uvicorn main:app --reload --port 8000`
2. Frontend: `npm install` then `npm run dev` -> http://localhost:5173
(API URL is set in `.env` -> VITE_API_URL)
