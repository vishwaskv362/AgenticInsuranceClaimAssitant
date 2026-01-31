"""PDF parsing tool for extracting text from insurance documents."""

import io
import os
import json
from typing import Optional
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# AI-powered extraction
try:
    from langchain_mistralai import ChatMistralAI
    from langchain_core.messages import HumanMessage, SystemMessage
    AI_EXTRACTION_AVAILABLE = True
except ImportError:
    AI_EXTRACTION_AVAILABLE = False


def extract_text_from_pdf(file_path: str | Path | io.BytesIO) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to PDF file or BytesIO object
        
    Returns:
        Extracted text from all pages
    """
    text_parts = []
    
    # Try pdfplumber first (better for structured documents)
    if pdfplumber is not None:
        try:
            if isinstance(file_path, io.BytesIO):
                pdf = pdfplumber.open(file_path)
            else:
                pdf = pdfplumber.open(str(file_path))
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            pdf.close()
            
            if text_parts:
                return "\n\n".join(text_parts)
        except Exception as e:
            print(f"pdfplumber failed, trying pypdf: {e}")
    
    # Fallback to pypdf
    if PdfReader is not None:
        try:
            if isinstance(file_path, io.BytesIO):
                file_path.seek(0)
                reader = PdfReader(file_path)
            else:
                reader = PdfReader(str(file_path))
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            if text_parts:
                return "\n\n".join(text_parts)
        except Exception as e:
            print(f"pypdf also failed: {e}")
    
    return ""


def extract_claim_info(text: str) -> dict:
    """
    Extract structured claim information from document text using AI.
    
    Args:
        text: Raw text extracted from PDF
        
    Returns:
        Dictionary with extracted claim details
    """
    # Default empty info
    info = {
        "claim_number": None,
        "member_id": None,
        "policy_number": None,
        "service_date": None,
        "admission_date": None,
        "discharge_date": None,
        "denial_date": None,
        "provider": None,
        "hospital_name": None,
        "insurer_name": None,
        "tpa_name": None,
        "patient_name": None,
        "billed_amount": None,
        "allowed_amount": None,
        "denied_amount": None,
        "claim_amount": None,
        "denial_codes": [],
        "denial_reason": None,
    }
    
    # Try AI-powered extraction first
    if AI_EXTRACTION_AVAILABLE:
        try:
            ai_info = extract_claim_info_with_ai(text)
            if ai_info:
                # Merge AI results with defaults
                for key, value in ai_info.items():
                    if value and key in info:
                        info[key] = value
                return info
        except Exception as e:
            print(f"AI extraction failed, falling back to regex: {e}")
    
    # Fallback to regex-based extraction
    return extract_claim_info_regex(text)


def extract_claim_info_with_ai(text: str) -> dict:
    """
    Use Mistral AI to extract structured information from claim document.
    
    Args:
        text: Raw text from claim document
        
    Returns:
        Dictionary with extracted claim details
    """
    if not AI_EXTRACTION_AVAILABLE:
        return {}
    
    # Get API key from environment
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return {}
    
    # Initialize Mistral
    llm = ChatMistralAI(
        model="mistral-small-latest",
        api_key=api_key,
        temperature=0.1,  # Low temperature for extraction accuracy
        max_tokens=1500,
    )
    
    # Create extraction prompt
    system_prompt = """You are an expert at extracting structured information from Indian insurance claim rejection letters.
Extract the following fields from the document. Return ONLY a valid JSON object with these exact keys.
If a field is not found, use null. Be precise and extract exact values as they appear.

Required JSON format:
{
    "claim_number": "exact claim/reference number",
    "policy_number": "policy/certificate number",
    "patient_name": "patient/insured name without titles like Mr/Mrs",
    "insurer_name": "insurance company name only (e.g., ICICI Lombard, Star Health, HDFC ERGO)",
    "hospital_name": "hospital name only without address",
    "tpa_name": "TPA company name if mentioned (e.g., Medi Assist, Paramount)",
    "admission_date": "date of admission in DD/MM/YYYY or as found",
    "discharge_date": "date of discharge in DD/MM/YYYY or as found",
    "claim_amount": "claimed amount as number without currency symbol",
    "denial_reason": "brief reason for rejection/denial",
    "denial_codes": ["array of denial codes like PED-001, PA-001"]
}

IMPORTANT:
- Extract ONLY the actual values, not labels or surrounding text
- For hospital_name, extract just the hospital name (e.g., "Max Super Speciality Hospital, Saket")
- For insurer_name, extract just the company name (e.g., "ICICI Lombard")
- For patient_name, remove titles like Mr., Mrs., Shri, Smt.
- Return valid JSON only, no additional text"""

    user_prompt = f"""Extract information from this insurance claim document:

---
{text[:4000]}
---

Return ONLY the JSON object with extracted values."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Clean up response - extract JSON from markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        extracted = json.loads(response_text)
        
        # Ensure denial_codes is a list
        if extracted.get("denial_codes") and not isinstance(extracted["denial_codes"], list):
            extracted["denial_codes"] = [extracted["denial_codes"]]
        
        return extracted
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response as JSON: {e}")
        return {}
    except Exception as e:
        print(f"AI extraction error: {e}")
        return {}


def extract_claim_info_regex(text: str) -> dict:
    """
    Fallback regex-based extraction for when AI is not available.
    
    Args:
        text: Raw text extracted from PDF
        
    Returns:
        Dictionary with extracted claim details
    """
    import re
    
    info = {
        "claim_number": None,
        "member_id": None,
        "policy_number": None,
        "service_date": None,
        "admission_date": None,
        "discharge_date": None,
        "denial_date": None,
        "provider": None,
        "hospital_name": None,
        "insurer_name": None,
        "tpa_name": None,
        "patient_name": None,
        "billed_amount": None,
        "allowed_amount": None,
        "denied_amount": None,
        "claim_amount": None,
        "denial_codes": [],
        "denial_reason": None,
    }
    
    # Simple patterns for key fields
    patterns = {
        "claim_number": r"claim\s*(?:number|#|no\.?|id|ref)\s*[:.]?\s*([A-Z0-9\-\/]+)",
        "policy_number": r"policy\s*(?:number|#|no\.?)\s*[:.]?\s*([A-Z0-9\-\/]+)",
        "admission_date": r"(?:admission|admitted)\s*(?:date|on)?\s*[:.]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        "discharge_date": r"discharge\s*(?:date|on)?\s*[:.]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        "claim_amount": r"(?:claim|total)\s*amount\s*[:.]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+)",
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info[field] = match.group(1).strip()
    
    # Extract insurer name
    insurers = ["Star Health", "ICICI Lombard", "HDFC ERGO", "Bajaj Allianz", "Max Bupa", 
                "Care Health", "Niva Bupa", "Aditya Birla", "Tata AIG", "SBI General",
                "New India", "United India", "Oriental", "National Insurance"]
    for insurer in insurers:
        if insurer.lower() in text.lower():
            info["insurer_name"] = insurer
            break
    
    # Extract hospital name
    hospitals = ["Apollo", "Fortis", "Max", "Medanta", "Narayana", "Manipal", "AIIMS",
                 "Kokilaben", "Lilavati", "Hinduja", "Sir Ganga Ram", "BLK", "Artemis"]
    for hospital in hospitals:
        if hospital.lower() in text.lower():
            # Try to get more context
            match = re.search(rf"({hospital}[A-Za-z\s,]+(?:Hospital|Medical|Healthcare)?[^,\n]*)", text, re.IGNORECASE)
            if match:
                info["hospital_name"] = match.group(1).strip()[:50]  # Limit length
            else:
                info["hospital_name"] = hospital
            break
    
    # Extract denial codes
    code_pattern = r"\b(PED-\d+|WP-\d+|EXC-\d+|PA-\d+|DOC-\d+|MN-\d+|NW-\d+|SL-\d+)\b"
    codes = re.findall(code_pattern, text, re.IGNORECASE)
    if codes:
        info["denial_codes"] = list(set(codes))
    
    return info
