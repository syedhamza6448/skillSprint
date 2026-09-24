import os
import json
import time
from google import genai
from dotenv import load_dotenv
from pydantic import ValidationError
from core.schemas import OnboardingPlan
from core.db import setup_db, get_matrix_rows_for_role, get_chunks_for_docs_and_sections, log_generation

def test_call():
    """Minimal test to confirm Gemini API connectivity."""
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY missing from environment variables.")
        return None
        
    client = genai.Client(api_key=api_key)
    
    print("Pinging Gemini API with 'say hello'...")
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents="say hello"
    )
    
    print("\n--- Response ---")
    print(response.text)
    print("----------------")
    
    return response.text

def build_prompt(role, matrix_rows, relevant_chunks):
    with open('prompts/onboarding_v1.txt', 'r', encoding='utf-8') as f:
        template = f.read()
        
    matrix_str = json.dumps(matrix_rows, indent=2)
    chunks_str = json.dumps(relevant_chunks, indent=2)
    
    return template.format(role=role, matrix_rows=matrix_str, relevant_chunks=chunks_str)

class _TransientExhausted(Exception):
    """Raised when all retry attempts fail with a transient (503/429) error."""

def call_gemini_with_retry(client, model, contents):
    """Try up to 3 times with exponential backoff for transient errors.

    Raises _TransientExhausted if every attempt hits a retriable error,
    so the caller can try a fallback model. Non-retryable exceptions
    propagate immediately as normal.
    """
    RETRYABLE = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
    BACKOFF_SCHEDULE = [2, 5, 10]   # seconds to wait before attempt 2, 3
    max_attempts = 3
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents
            )
        except Exception as e:
            error_str = str(e)
            is_retryable = any(code in error_str for code in RETRYABLE)
            if is_retryable:
                last_exc = e
                if attempt < max_attempts - 1:
                    wait = BACKOFF_SCHEDULE[attempt]
                    print(f"[{model}] [Retry {attempt + 1}/{max_attempts - 1}] "
                          f"Transient error: {error_str[:120]}... Waiting {wait}s.")
                    time.sleep(wait)
                    continue
                # All attempts exhausted — signal caller to try fallback
                print(f"[{model}] All {max_attempts} attempts exhausted. "
                      f"Triggering fallback model.")
                raise _TransientExhausted(str(last_exc)) from last_exc
            raise

def generate_plan(employee_id, role):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "API Key missing from environment variables"}

    client = genai.Client(api_key=api_key)
    PRIMARY_MODEL   = "gemini-3.5-flash"
    FALLBACK_MODEL  = "gemini-3.5-flash-lite"
    prompt_version  = "v1"

    # Ensure DB tables exist
    setup_db()

    # 1. Fetch source data
    matrix_rows = get_matrix_rows_for_role(role)
    if not matrix_rows:
        return {"error": f"No requirements found for role: {role}"}

    doc_section_pairs = [(r['policy_source_doc'], r['source_section']) for r in matrix_rows]
    relevant_chunks   = get_chunks_for_docs_and_sections(doc_section_pairs)
    prompt            = build_prompt(role, matrix_rows, relevant_chunks)

    def clean_json(text):
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        return text.strip()

    def _call_and_parse(model, contents, note=""):
        """Call Gemini with retry, clean the response, validate against schema.
        Returns (plan_dict, model) on success. Raises on any failure.
        """
        response = call_gemini_with_retry(client=client, model=model, contents=contents)
        raw_json = clean_json(response.text)
        plan = OnboardingPlan.model_validate_json(raw_json)
        plan.employee_id = employee_id
        plan.role = role
        log_generation(employee_id, role, prompt_version, model,
                       "SUCCESS", note or f"Served by {model}")
        return plan.model_dump(), model

    # 2. Primary model attempt (with built-in exponential-backoff retries)
    try:
        plan_dict, model_used = _call_and_parse(PRIMARY_MODEL, prompt)
        return {"plan": plan_dict, "model_used": model_used}

    except _TransientExhausted:
        # Primary exhausted — try the lighter fallback model once
        print(f"[Fallback] Primary model exhausted. Trying {FALLBACK_MODEL}...")
        try:
            plan_dict, model_used = _call_and_parse(
                FALLBACK_MODEL, prompt,
                note=f"Primary {PRIMARY_MODEL} exhausted; served by fallback"
            )
            return {"plan": plan_dict, "model_used": model_used}
        except Exception as fb_exc:
            log_generation(employee_id, role, prompt_version, FALLBACK_MODEL,
                           "FAILED", f"Fallback also failed: {fb_exc}")
            return {"error": f"Both models failed. Last error: {fb_exc}"}

    except ValidationError as ve:
        # Schema mismatch — send correction prompt back to primary
        error_msg   = str(ve)
        fix_prompt  = (f"Your last response didn't match the required JSON schema. "
                       f"Error: {error_msg} — return corrected JSON only.")
        try:
            plan_dict, model_used = _call_and_parse(
                PRIMARY_MODEL, fix_prompt,
                note="Succeeded on schema-correction retry"
            )
            return {"plan": plan_dict, "model_used": model_used}
        except Exception as retry_exc:
            log_generation(employee_id, role, prompt_version, PRIMARY_MODEL,
                           "FAILED", f"Schema retry failed: {retry_exc}")
            return {"error": f"Validation failed after retry: {retry_exc}"}

    except Exception as e:
        log_generation(employee_id, role, prompt_version, PRIMARY_MODEL, "FAILED", str(e))
        return {"error": f"API Call failed: {e}"}
