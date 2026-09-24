# SkillSprint AI

SkillSprint AI generates and validates role-specific onboarding plans by comparing AI-generated output against ground-truth company policies.

## Setup Instructions

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Copy `.env.example` to `.env` and add your Gemini API key:
   ```bash
   cp .env.example .env
   # Edit .env and paste your GEMINI_API_KEY
   ```

4. **Verify Setup:**
   Run the test script to confirm API connectivity:
   ```bash
   python -c "from core.genai_pipeline import test_call; test_call()"
   ```
