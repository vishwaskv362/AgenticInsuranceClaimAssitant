"""
CrewAI Crew Definition for Insurance Claim Assistant (India).

This module defines the multi-agent crew that analyzes insurance claim denials
and generates appeal letters for Indian insurance companies.
"""

import os
from dotenv import load_dotenv

# Load environment variables BEFORE importing CrewAI
load_dotenv()

# Disable telemetry 
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

# Set a dummy OpenAI key to prevent CrewAI initialization errors
# CrewAI checks for this but we'll override with Mistral LLM
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-not-used"

from crewai import Agent, Task, Crew, Process, LLM
from pathlib import Path

import config
from tools.denial_codes import (
    analyze_denial_codes,
    format_denial_analysis_report,
    get_appeal_strategies,
)


# Initialize LLM using CrewAI's native LLM with Mistral via LiteLLM
def get_llm():
    """Get the Mistral LLM instance configured for CrewAI."""
    return LLM(
        model="mistral/mistral-small-latest",
        api_key=config.MISTRAL_API_KEY,
        temperature=0.3,
    )


# Load knowledge base
def load_knowledge(filename: str) -> str:
    """Load knowledge base file content."""
    knowledge_path = Path(__file__).parent / "knowledge" / filename
    if knowledge_path.exists():
        return knowledge_path.read_text()
    return ""


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

def create_document_analyzer(llm) -> Agent:
    """Create the Document Analyzer agent."""
    return Agent(
        role="Insurance Document Analyst",
        goal="Extract and structure all relevant information from insurance claim documents",
        backstory="""You are an expert at reading and interpreting Indian insurance documents 
        including claim rejection letters, pre-authorization denials, cashless claim rejections,
        and health insurance policies. You have 15 years of experience in medical billing at 
        top Indian insurers like Star Health, ICICI Lombard, HDFC ERGO, and government schemes 
        like PMJAY. You can quickly identify key information like claim numbers, rejection codes, 
        policy numbers, TPA details, and denial reasons as per IRDAI guidelines. You are 
        meticulous and never miss important details.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_policy_expert(llm) -> Agent:
    """Create the Policy Expert agent."""
    return Agent(
        role="Insurance Policy Expert",
        goal="Analyze insurance policies to determine coverage and identify policy violations",
        backstory="""You are a seasoned insurance policy analyst with deep knowledge 
        of Indian health insurance regulations under IRDAI (Insurance Regulatory and 
        Development Authority of India). You understand policy wordings, exclusions, 
        coverage limits, waiting periods, sub-limits, and policyholder rights under 
        the Insurance Act 1938 and IRDAI Health Insurance Regulations 2016. You can 
        quickly determine if a claim should be covered and identify when insurers 
        incorrectly apply policy terms or violate IRDAI guidelines.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_denial_reviewer(llm) -> Agent:
    """Create the Denial Reviewer agent."""
    regulations = load_knowledge("regulations.md")
    
    return Agent(
        role="Claims Denial Reviewer",
        goal="Analyze denial reasons and determine if the denial is valid or can be appealed",
        backstory=f"""You are a claims denial specialist who has reviewed thousands of 
        insurance claim denials. You know every denial code, what they mean, and most 
        importantly, when insurers use them incorrectly. You can spot procedural errors, 
        factual mistakes, and policy misapplications that make denials invalid.
        
        You are familiar with insurance regulations:
        {regulations[:2000]}...""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_appeal_strategist(llm) -> Agent:
    """Create the Appeal Strategist agent."""
    regulations = load_knowledge("regulations.md")
    
    return Agent(
        role="Insurance Appeal Strategist",
        goal="Develop the strongest possible appeal strategy based on IRDAI regulations and precedents",
        backstory=f"""You are a legal researcher specializing in Indian insurance appeals. 
        You know IRDAI regulations, Insurance Act 1938, Consumer Protection Act 2019, 
        IRDAI Health Insurance Regulations, and Insurance Ombudsman Rules. You understand 
        the grievance redressal mechanisms including IGMS portal, Insurance Ombudsman, 
        and Consumer Forum. You can identify the strongest legal grounds for an appeal 
        that insurance companies cannot easily dismiss.
        
        Key regulations you reference:
        {regulations}""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_letter_writer(llm) -> Agent:
    """Create the Letter Writer agent."""
    templates = load_knowledge("appeal_templates.md")
    
    return Agent(
        role="Professional Appeal Letter Writer",
        goal="Write compelling, professional appeal letters that maximize chance of success",
        backstory=f"""You are a professional writer specializing in insurance appeal 
        letters. You know exactly how to structure an appeal, what tone to use, and 
        how to present arguments persuasively. Your letters are clear, factual, and 
        assertive without being aggressive. You include all required elements and 
        reference specific policy sections and regulations.
        
        You use these proven templates as inspiration:
        {templates[:3000]}...""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_quality_reviewer(llm) -> Agent:
    """Create the Quality Reviewer agent."""
    return Agent(
        role="Quality Assurance Reviewer",
        goal="Ensure the appeal letter is accurate, complete, professional, and persuasive",
        backstory="""You are a meticulous editor and quality reviewer. You check 
        appeal letters for factual accuracy, proper formatting, persuasive language, 
        and completeness. You ensure all required elements are present, the tone is 
        appropriate, and the arguments are logically structured. You also verify that 
        any claims made are supported by the provided documentation.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


# =============================================================================
# TASK DEFINITIONS
# =============================================================================

def create_document_analysis_task(agent: Agent, document_text: str) -> Task:
    """Create the document analysis task."""
    return Task(
        description=f"""Analyze the following insurance document and extract ALL relevant information.

DOCUMENT TEXT:
{document_text}

Extract and structure:
1. Claim Details:
   - Claim number
   - Member/Policy ID
   - Date of service
   - Provider name
   - Billed amount
   - Allowed amount
   - Denied amount

2. Denial Information:
   - Denial date
   - Denial code(s)
   - Stated denial reason
   - Any specific policy sections referenced

3. Patient/Member Information:
   - Patient name (if visible)
   - Coverage type

4. Important Deadlines:
   - Appeal deadline (if mentioned)
   - Any other time-sensitive information

If any information is not found, indicate "Not found in document".
Be thorough - missing information could hurt the appeal.""",
        expected_output="""A structured report containing all extracted claim information,
denial details, and relevant deadlines. Format as a clear document with sections.""",
        agent=agent,
    )


def create_policy_analysis_task(agent: Agent, claim_info: str, policy_text: str = None) -> Task:
    """Create the policy analysis task."""
    policy_context = ""
    if policy_text:
        policy_context = f"""
POLICY DOCUMENT:
{policy_text[:5000]}
"""
    
    return Task(
        description=f"""Analyze the claim information and determine coverage.

CLAIM INFORMATION:
{claim_info}

{policy_context}

Determine:
1. Is this type of service typically covered by health insurance?
2. Are there common exclusions that might apply?
3. Would prior authorization typically be required?
4. Are there any obvious policy violations by the insurer?
5. What policy sections would be relevant to this claim?

Even without the full policy, use your expertise to assess:
- Standard coverage expectations
- Common insurer mistakes
- Typical policy language for this type of service""",
        expected_output="""A coverage analysis report including:
- Assessment of whether service should be covered
- Potential exclusions to watch for
- Prior authorization considerations
- Any suspected policy violations
- Recommendations for appeal arguments""",
        agent=agent,
    )


def create_denial_review_task(agent: Agent, claim_info: str, denial_analysis: str) -> Task:
    """Create the denial review task."""
    return Task(
        description=f"""Review the denial and determine if it is valid or should be appealed.

CLAIM INFORMATION:
{claim_info}

DENIAL CODE ANALYSIS:
{denial_analysis}

Your analysis should cover:
1. Is the denial code appropriate for the stated reason?
2. Did the insurer follow proper procedures before denying?
3. Are there any factual errors in the denial?
4. Does the denial contradict standard insurance practices?
5. Are there regulatory violations in how the denial was handled?

Provide:
- Assessment: VALID, LIKELY INVALID, or UNCERTAIN
- Confidence level (Low/Medium/High)
- Specific issues found
- Key weaknesses in the insurer's position""",
        expected_output="""A denial validity assessment including:
- Overall assessment (Valid/Likely Invalid/Uncertain)
- Confidence level
- List of specific issues found
- Recommended grounds for appeal
- Estimated success probability (Low/Medium/High)""",
        agent=agent,
    )


def create_appeal_strategy_task(agent: Agent, claim_info: str, denial_review: str) -> Task:
    """Create the appeal strategy task."""
    return Task(
        description=f"""Develop a comprehensive appeal strategy.

CLAIM INFORMATION:
{claim_info}

DENIAL REVIEW:
{denial_review}

Create an appeal strategy that includes:
1. Primary legal/regulatory grounds for appeal
2. Secondary supporting arguments
3. Required documentation to include
4. Specific policy sections to reference
5. State/federal regulations that support the appeal
6. Recommended appeal level (internal vs external)
7. Timeline and deadlines to mention

Focus on the STRONGEST arguments. Insurance companies respond to:
- Clear policy violations
- Regulatory non-compliance
- Factual errors
- Precedent from similar cases""",
        expected_output="""A detailed appeal strategy document including:
- Ranked list of appeal arguments (strongest first)
- Legal/regulatory citations
- Required supporting documents
- Recommended timeline
- Specific language to include
- Potential insurer counterarguments and rebuttals""",
        agent=agent,
    )


def create_letter_writing_task(agent: Agent, claim_info: str, strategy: str, patient_info: dict) -> Task:
    """Create the letter writing task."""
    return Task(
        description=f"""Write a professional appeal letter based on the strategy.

CLAIM INFORMATION:
{claim_info}

APPEAL STRATEGY:
{strategy}

PATIENT INFORMATION:
Name: {patient_info.get('name', '[PATIENT NAME]')}
Address: {patient_info.get('address', '[ADDRESS]')}
Phone: {patient_info.get('phone', '[PHONE]')}
Email: {patient_info.get('email', '[EMAIL]')}

Write a formal appeal letter that:
1. Clearly states this is a formal appeal
2. References the specific claim and denial
3. Presents arguments in order of strength
4. Cites specific policy sections and regulations
5. Includes all required formal elements
6. Requests specific action (reverse denial, process claim)
7. Mentions relevant deadlines
8. Lists enclosures/attachments

Tone should be:
- Professional and respectful
- Firm and assertive
- Factual, not emotional
- Clear and well-organized

Use placeholders like [CLAIM_NUMBER] for any missing information.""",
        expected_output="""A complete, professional appeal letter ready to be sent.
Include:
- Full letter text with proper formatting
- List of recommended enclosures
- Next steps for the patient""",
        agent=agent,
    )


def create_quality_review_task(agent: Agent, letter: str, claim_info: str) -> Task:
    """Create the quality review task."""
    return Task(
        description=f"""Review and improve the appeal letter.

DRAFT APPEAL LETTER:
{letter}

ORIGINAL CLAIM INFO:
{claim_info}

Review for:
1. Factual Accuracy:
   - All claim numbers and dates correct
   - No factual claims that aren't supported
   
2. Completeness:
   - All required elements present
   - Claim details included
   - Specific request made
   - Deadline mentioned
   
3. Professionalism:
   - Appropriate tone
   - No emotional language
   - Clear and concise
   
4. Persuasiveness:
   - Arguments logically ordered
   - Evidence cited properly
   - Strong opening and closing
   
5. Formatting:
   - Proper letter format
   - Easy to read
   - Enclosures listed

Provide the FINAL, polished version of the letter with all improvements made.
Also provide a brief summary of changes and any remaining concerns.""",
        expected_output="""The final, polished appeal letter with:
- All corrections made
- Improved language where needed
- Proper formatting
- Summary of changes made
- List of recommended next steps for patient
- Any remaining concerns or caveats""",
        agent=agent,
    )


# =============================================================================
# CREW CREATION
# =============================================================================

def create_claim_assistant_crew(
    document_text: str,
    denial_codes: list = None,
    policy_text: str = None,
    patient_info: dict = None,
) -> tuple[Crew, dict]:
    """
    Create the Insurance Claim Assistant crew.
    
    Args:
        document_text: Text extracted from denial letter/documents
        denial_codes: List of denial codes found (optional, will be extracted)
        policy_text: Text from insurance policy (optional)
        patient_info: Dictionary with patient name, address, etc.
        
    Returns:
        Tuple of (Crew object, context dictionary)
    """
    if patient_info is None:
        patient_info = {}
    
    # Initialize LLM
    llm = get_llm()
    
    # Create agents
    document_analyzer = create_document_analyzer(llm)
    policy_expert = create_policy_expert(llm)
    denial_reviewer = create_denial_reviewer(llm)
    appeal_strategist = create_appeal_strategist(llm)
    letter_writer = create_letter_writer(llm)
    quality_reviewer = create_quality_reviewer(llm)
    
    # Analyze denial codes if provided
    denial_analysis = ""
    if denial_codes:
        analysis = analyze_denial_codes(denial_codes)
        denial_analysis = format_denial_analysis_report(analysis)
    
    # Create tasks
    task1 = create_document_analysis_task(document_analyzer, document_text)
    
    task2 = Task(
        description=f"""Analyze the claim for coverage based on the document analysis.
        
Use the extracted claim information from the previous task.
Policy text (if available): {policy_text[:3000] if policy_text else 'Not provided'}

Determine coverage expectations and identify any insurer errors.""",
        expected_output="Coverage analysis with recommendations",
        agent=policy_expert,
        context=[task1],
    )
    
    task3 = Task(
        description=f"""Review the denial validity based on document analysis and coverage assessment.

Denial code analysis:
{denial_analysis}

Determine if the denial should be appealed and estimate success likelihood.""",
        expected_output="Denial validity assessment with appeal recommendation",
        agent=denial_reviewer,
        context=[task1, task2],
    )
    
    task4 = Task(
        description="""Develop a comprehensive appeal strategy based on all previous analysis.
        
Focus on the strongest legal and factual arguments.
Include specific regulations and policy references.""",
        expected_output="Detailed appeal strategy document",
        agent=appeal_strategist,
        context=[task1, task2, task3],
    )
    
    task5 = Task(
        description=f"""Write a professional appeal letter using the strategy.

Patient information:
{patient_info}

Create a complete, ready-to-send appeal letter.""",
        expected_output="Complete professional appeal letter",
        agent=letter_writer,
        context=[task1, task4],
    )
    
    task6 = Task(
        description="""Review and finalize the appeal letter.
        
Ensure accuracy, completeness, professionalism, and persuasiveness.
Provide the final polished version.""",
        expected_output="Final polished appeal letter with next steps",
        agent=quality_reviewer,
        context=[task1, task5],
    )
    
    # Create crew with explicit manager_llm to avoid OpenAI fallback
    crew = Crew(
        agents=[
            document_analyzer,
            policy_expert,
            denial_reviewer,
            appeal_strategist,
            letter_writer,
            quality_reviewer,
        ],
        tasks=[task1, task2, task3, task4, task5, task6],
        process=Process.sequential,
        verbose=True,
        manager_llm=llm,  # Use Mistral for management to avoid OpenAI fallback
    )
    
    context = {
        "document_text": document_text,
        "denial_codes": denial_codes,
        "denial_analysis": denial_analysis,
        "policy_text": policy_text,
        "patient_info": patient_info,
    }
    
    return crew, context


def run_claim_analysis(
    document_text: str,
    denial_codes: list = None,
    policy_text: str = None,
    patient_info: dict = None,
) -> str:
    """
    Run the full claim analysis and generate appeal letter.
    
    Args:
        document_text: Text from denial letter/documents
        denial_codes: List of denial codes (optional)
        policy_text: Policy document text (optional)
        patient_info: Patient information dictionary
        
    Returns:
        Final appeal letter and analysis
    """
    crew, context = create_claim_assistant_crew(
        document_text=document_text,
        denial_codes=denial_codes,
        policy_text=policy_text,
        patient_info=patient_info,
    )
    
    result = crew.kickoff()
    
    return result
