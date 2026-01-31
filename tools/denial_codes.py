"""Denial/Rejection code lookup tool for understanding claim rejections (India)."""

import json
from pathlib import Path
from typing import Optional


# Load rejection codes database
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
DENIAL_CODES_FILE = KNOWLEDGE_DIR / "denial_codes.json"

_denial_codes_cache = None


def load_denial_codes() -> dict:
    """Load rejection codes from JSON file."""
    global _denial_codes_cache
    
    if _denial_codes_cache is not None:
        return _denial_codes_cache
    
    if DENIAL_CODES_FILE.exists():
        with open(DENIAL_CODES_FILE, "r") as f:
            _denial_codes_cache = json.load(f)
    else:
        _denial_codes_cache = {"rejection_codes": {}, "rejection_categories": {}}
    
    return _denial_codes_cache


def lookup_denial_code(code: str) -> Optional[dict]:
    """
    Look up a rejection code and get its details.
    
    Args:
        code: The rejection code (e.g., "PED-001", "MN-001", "PA-001")
        
    Returns:
        Dictionary with code details or None if not found
    """
    data = load_denial_codes()
    code_upper = code.upper().strip()
    
    # Try rejection_codes first (new India format), then denial_codes (legacy)
    codes_dict = data.get("rejection_codes", {}) or data.get("denial_codes", {})
    return codes_dict.get(code_upper)


def get_denial_category(code: str) -> Optional[dict]:
    """
    Get the category information for a rejection code.
    
    Args:
        code: The rejection code
        
    Returns:
        Category information including common appeal strategies
    """
    data = load_denial_codes()
    code_upper = code.upper().strip()
    
    # Try rejection_categories first (new India format), then denial_categories (legacy)
    categories = data.get("rejection_categories", {}) or data.get("denial_categories", {})
    
    for category_name, category_info in categories.items():
        if code_upper in category_info.get("codes", []):
            return {
                "category_name": category_name,
                **category_info
            }
    
    return None


def get_appeal_strategies(code: str) -> list:
    """
    Get recommended appeal strategies for a denial code.
    
    Args:
        code: The denial code
        
    Returns:
        List of appeal strategy recommendations
    """
    strategies = []
    
    # Get code-specific strategies
    code_info = lookup_denial_code(code)
    if code_info:
        strategies.extend(code_info.get("appeal_grounds", []))
    
    # Get category strategies
    category_info = get_denial_category(code)
    if category_info:
        strategies.extend(category_info.get("common_appeal_strategies", []))
    
    return list(set(strategies))  # Remove duplicates


def analyze_denial_codes(codes: list) -> dict:
    """
    Analyze multiple denial codes and provide comprehensive information.
    
    Args:
        codes: List of denial codes from the claim
        
    Returns:
        Comprehensive analysis of all codes
    """
    analysis = {
        "codes_found": [],
        "codes_unknown": [],
        "primary_category": None,
        "all_strategies": [],
        "overall_appeal_likelihood": "Unknown",
        "summary": "",
    }
    
    categories = []
    success_rates = []
    
    for code in codes:
        code_info = lookup_denial_code(code)
        
        if code_info:
            analysis["codes_found"].append({
                "code": code,
                "info": code_info
            })
            success_rates.append(code_info.get("success_rate", "Unknown"))
            
            category = get_denial_category(code)
            if category:
                categories.append(category.get("category_name"))
            
            strategies = get_appeal_strategies(code)
            analysis["all_strategies"].extend(strategies)
        else:
            analysis["codes_unknown"].append(code)
    
    # Determine primary category
    if categories:
        from collections import Counter
        analysis["primary_category"] = Counter(categories).most_common(1)[0][0]
    
    # Determine overall success likelihood
    if success_rates:
        if "High" in success_rates:
            analysis["overall_appeal_likelihood"] = "Good"
        elif "Medium" in success_rates:
            analysis["overall_appeal_likelihood"] = "Moderate"
        else:
            analysis["overall_appeal_likelihood"] = "Challenging"
    
    # Remove duplicate strategies
    analysis["all_strategies"] = list(set(analysis["all_strategies"]))
    
    # Generate summary
    if analysis["codes_found"]:
        primary = analysis["codes_found"][0]
        analysis["summary"] = (
            f"Primary denial reason: {primary['info']['description']}. "
            f"Appeal likelihood: {analysis['overall_appeal_likelihood']}. "
            f"Found {len(analysis['all_strategies'])} potential appeal strategies."
        )
    
    return analysis


def format_denial_analysis_report(analysis: dict) -> str:
    """
    Format the denial analysis as a readable report.
    
    Args:
        analysis: Analysis dictionary from analyze_denial_codes
        
    Returns:
        Formatted string report
    """
    lines = [
        "=" * 60,
        "DENIAL CODE ANALYSIS",
        "=" * 60,
        ""
    ]
    
    for item in analysis.get("codes_found", []):
        code = item["code"]
        info = item["info"]
        lines.append(f"Code: {code}")
        lines.append(f"Category: {info.get('category', 'Unknown')}")
        lines.append(f"Description: {info.get('description', 'No description')}")
        lines.append(f"Success Rate: {info.get('success_rate', 'Unknown')}")
        lines.append(f"Common Causes: {', '.join(info.get('common_causes', []))}")
        lines.append("")
    
    if analysis.get("codes_unknown"):
        lines.append(f"Unknown Codes: {', '.join(analysis['codes_unknown'])}")
        lines.append("")
    
    lines.append("-" * 60)
    lines.append(f"Overall Appeal Likelihood: {analysis.get('overall_appeal_likelihood', 'Unknown')}")
    lines.append("")
    
    if analysis.get("all_strategies"):
        lines.append("RECOMMENDED APPEAL STRATEGIES:")
        for i, strategy in enumerate(analysis["all_strategies"], 1):
            lines.append(f"  {i}. {strategy}")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)
