import google.generativeai as genai
from typing import Dict, List, Tuple, Any
import streamlit as st
import time
import json
from datetime import date, datetime

# gemini-2.5-flash is the model
PREFERRED_GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
)


def _create_verified_model(model_name: str):
    """Create a GenerativeModel and verify it responds."""
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Reply with OK.")
    if response and response.text:
        return model
    raise RuntimeError(f"Model {model_name} returned an empty response")


def initialize_gemini(api_key: str):
    """Initialize Gemini API with the provided key"""
    try:
        genai.configure(api_key=api_key)

        last_error = None
        for model_name in PREFERRED_GEMINI_MODELS:
            try:
                return _create_verified_model(model_name)
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise last_error

    except Exception as e:
        if "429" in str(e):  # Rate limit error
            st.error("Rate limit exceeded. Please wait a few minutes before trying again.")
            st.info("""
            To avoid rate limits:
            1. Wait a few minutes between requests
            2. Keep your prompts concise
            3. Consider upgrading to a paid API tier
            """)
        else:
            st.error(f"Failed to initialize Gemini API: {str(e)}")
            st.info("""
            Please check:
            1. Your API key is valid
            2. You have internet connection
            3. The API service is available in your region
            4. Your project has access to a current Gemini model (e.g. gemini-2.5-flash)
            """)
        return None

def _json_safe(value: Any) -> Any:
    """Convert values to JSON-serializable forms."""
    if isinstance(value, datetime):
        return value.strftime("%B %Y") if value else ""
    if isinstance(value, date):
        return value.strftime("%B %Y")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _build_role_context(resume_data: Dict) -> str:
    """Build structured resume context for prompts."""
    skills = resume_data.get('skills', {})
    projects = resume_data.get('projects', [])
    payload = {
        'target_role': resume_data.get('profile_summary', {}).get('target_role', 'Not specified'),
        'summary': resume_data.get('profile_summary', {}).get('summary', ''),
        'programming_skills': skills.get('programming', []),
        'frameworks': skills.get('frameworks', []),
        'tools': skills.get('tools', []),
        'other_skills': skills.get('other', []),
        'soft_skills': skills.get('soft_skills', []),
        'education': resume_data.get('education', {}),
        'projects': [
            {
                'title': p.get('title', ''),
                'tools': p.get('tools', ''),
                'description': p.get('description', ''),
            }
            for p in projects
        ],
    }
    return json.dumps(_json_safe(payload), indent=2)


def _role_focused_instructions(target_role: str) -> str:
    return f"""
STRICT EVALUATION RULES:
- Analyze ONLY for the target role: "{target_role}".
- Compare the resume against the expected tech stack, tools, and competencies for this role.
- If programming languages or core role skills are missing, state that clearly and score harshly.
- Do NOT give optimistic feedback when content is missing or generic.
- Do NOT assume skills that are not explicitly present in the resume data.
- Use professional tone with sections and bullet points using "-" only.
- Keep each section concise, ordered by priority (most critical gaps first).
"""


def analyze_resume_content(model, resume_data: Dict) -> Dict:
    """Analyze resume content using Gemini API with rate limit handling"""
    if not model:
        return {
            'profile_analysis': "AI analysis unavailable. Please check API configuration.",
            'skills_analysis': "AI analysis unavailable. Please check API configuration."
        }

    target_role = resume_data.get('profile_summary', {}).get('target_role', 'Not specified')
    context = _build_role_context(resume_data)

    try:
        time.sleep(2)

        profile_prompt = f"""
You are a senior hiring manager evaluating a resume ONLY for: {target_role}.

RESUME DATA:
{context}

{_role_focused_instructions(target_role)}

Provide analysis in EXACTLY these sections (use "-" for every bullet):

**Role Alignment Summary**
- State how well the profile matches {target_role}
- Mention missing fundamentals if any

**Profile Strengths**
- List only strengths backed by resume content

**Critical Gaps**
- List missing qualifications, skills, or experience for {target_role}

**Content Improvements**
- Specific rewrites or additions needed

**Recommended Keywords for {target_role}**
- Role-specific keywords to add (only those relevant to this role)
"""

        profile_response = model.generate_content(profile_prompt)
        time.sleep(2)

        skills_prompt = f"""
You are a technical recruiter specializing in {target_role}.

RESUME DATA:
{context}

{_role_focused_instructions(target_role)}

Provide analysis in EXACTLY these sections (use "-" for every bullet):

**Expected Tech Stack for {target_role}**
- List standard languages, frameworks, and tools for this role

**Skills Found in Resume**
- Only skills explicitly present in the resume data

**Missing Core Skills**
- Critical skills absent from the resume for {target_role}

**Skills Match Rating**
- Rate match as: Poor / Fair / Good / Strong — with one-line justification

**Priority Upskilling Plan**
- Top 5 skills to add, ordered by impact for {target_role}

**Project & Experience Gaps**
- How projects/experience fail to demonstrate the required stack
"""

        skills_response = model.generate_content(skills_prompt)

        return {
            'profile_analysis': profile_response.text if profile_response else "Analysis failed",
            'skills_analysis': skills_response.text if skills_response else "Analysis failed"
        }
    except Exception as e:
        if "429" in str(e):  # Rate limit error
            st.error("Rate limit exceeded. Please wait a few minutes before trying again.")
            return {
                'profile_analysis': "Analysis paused: Rate limit exceeded. Please try again in a few minutes.",
                'skills_analysis': "Analysis paused: Rate limit exceeded. Please try again in a few minutes."
            }
        st.error(f"Error during resume analysis: {str(e)}")
        return {
            'profile_analysis': f"Analysis failed: {str(e)}",
            'skills_analysis': f"Analysis failed: {str(e)}"
        }

def get_ats_optimization(model, resume_data: Dict) -> Dict:
    """Get ATS optimization suggestions using Gemini API"""
    if not model:
        return {'ats_analysis': "ATS analysis unavailable. Please check API configuration."}

    target_role = resume_data.get('profile_summary', {}).get('target_role', 'Not specified')
    context = _build_role_context(resume_data)

    try:
        time.sleep(2)

        prompt = f"""
You are an ATS analyst. Evaluate this resume ONLY for: {target_role}.

RESUME DATA:
{context}

{_role_focused_instructions(target_role)}

SCORING RULES:
- Incomplete resumes with no programming languages (for technical roles) must receive Poor ATS readiness.
- Do not inflate scores for sparse content.
- Base every recommendation on gaps visible in the resume data.

Provide analysis in EXACTLY these sections (use "-" for every bullet):

**ATS Readiness Verdict**
- One of: Poor / Fair / Good / Excellent — with brief justification for {target_role}

**Keyword Analysis**
- Keywords present that match {target_role}
- Missing essential keywords for this role

**Format & Structure**
- Section organization issues
- ATS parsing risks

**Content Quality**
- Action verbs, metrics, and achievement clarity

**Role-Specific Recommendations**
- Top 5 changes to improve ATS score for {target_role}

**Quick Wins**
- Changes that can be made immediately
"""

        response = model.generate_content(prompt)
        return {
            'ats_analysis': response.text if response else "ATS analysis failed"
        }
    except Exception as e:
        if "429" in str(e):  # Rate limit error
            st.error("Rate limit exceeded. Please wait a few minutes before trying again.")
            return {
                'ats_analysis': "Analysis paused: Rate limit exceeded. Please try again in a few minutes."
            }
        st.error(f"Error during ATS analysis: {str(e)}")
        return {
            'ats_analysis': f"Analysis failed: {str(e)}"
        }

def generate_achievements_suggestions(model, resume_data: Dict) -> List[str]:
    """Generate achievement suggestions based on experience"""
    
    prompt = f"""
    Based on this professional profile:
    Role: {resume_data['profile_summary']['target_role']}
    Skills: {', '.join(resume_data['skills']['programming'] + resume_data['skills']['frameworks'])}
    Projects: {', '.join(p['title'] for p in resume_data['projects'])}
    
    Suggest 5 quantifiable achievements that would strengthen this resume.
    Format each achievement with:
    1. Action verb
    2. Specific metric
    3. Impact statement
    """
    
    response = model.generate_content(prompt)

def extract_improved_content(analysis_text: str) -> Dict[str, str]:
    """Extract improved content from AI analysis"""
    try:
        # Split analysis into sections
        sections = analysis_text.split('\n')
        improved_content = {}
        
        current_section = None
        current_content = []
        
        for line in sections:
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            if line.startswith('1.') and ('Enhanced Version' in line or 'Version' in line):
                if current_section and current_content:
                    improved_content[current_section] = '\n'.join(current_content)
                current_section = 'enhanced_version'
                current_content = []
            elif line.startswith('2.') and 'Key Improvements' in line:
                if current_section and current_content:
                    improved_content[current_section] = '\n'.join(current_content)
                current_section = 'improvements'
                current_content = []
            elif line.startswith('3.') and 'Missing Keywords' in line:
                if current_section and current_content:
                    improved_content[current_section] = '\n'.join(current_content)
                current_section = 'keywords'
                current_content = []
            elif line.startswith('4.') and 'Metrics' in line:
                if current_section and current_content:
                    improved_content[current_section] = '\n'.join(current_content)
                current_section = 'metrics'
                current_content = []
            elif current_section:
                if not line.startswith(('1.', '2.', '3.', '4.')):
                    current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            improved_content[current_section] = '\n'.join(current_content)
            
        return improved_content
    except Exception as e:
        st.error(f"Error extracting improvements: {str(e)}")
        return {}

def apply_ai_suggestions(resume_data: Dict, analysis_data: Dict) -> Tuple[Dict, List[str]]:
    """Apply AI suggestions to resume data"""
    try:
        updated_data = resume_data.copy()
        changes_made = []
        
        # Extract improvements from profile analysis
        if 'profile_analysis' in analysis_data:
            profile_improvements = extract_improved_content(analysis_data['profile_analysis'])
            
            # Apply enhanced version of summary if available
            if 'enhanced_version' in profile_improvements:
                old_summary = updated_data['profile_summary']['summary']
                new_summary = profile_improvements['enhanced_version']
                if new_summary and new_summary != old_summary:
                    updated_data['profile_summary']['summary'] = new_summary
                    changes_made.append("Updated profile summary with AI suggestions")
            
            # Add suggested keywords to skills
            if 'keywords' in profile_improvements:
                keywords = [k.strip() for k in profile_improvements['keywords'].split(',') 
                          if k.strip() and k.strip() not in updated_data['skills'].get('other', [])]
                if keywords:
                    if 'other' not in updated_data['skills']:
                        updated_data['skills']['other'] = []
                    updated_data['skills']['other'].extend(keywords)
                    changes_made.append(f"Added {len(keywords)} suggested keywords to skills")
        
        # Apply skills improvements
        if 'skills_analysis' in analysis_data:
            skills_improvements = extract_improved_content(analysis_data['skills_analysis'])
            
            # Add missing critical skills
            if 'Critical Missing Skills' in skills_improvements:
                new_skills = [s.strip() for s in skills_improvements['Critical Missing Skills'].split(',')
                            if s.strip() and s.strip() not in updated_data['skills'].get('programming', [])]
                if new_skills:
                    if 'programming' not in updated_data['skills']:
                        updated_data['skills']['programming'] = []
                    updated_data['skills']['programming'].extend(new_skills)
                    changes_made.append(f"Added {len(new_skills)} suggested technical skills")
        
        # Apply ATS optimization suggestions
        if 'ats_analysis' in analysis_data:
            ats_improvements = extract_improved_content(analysis_data['ats_analysis'])
            
            # Add format improvements to the changes list
            if 'Format Improvements' in ats_improvements:
                changes_made.append("ATS Format Suggestions:")
                for line in ats_improvements['Format Improvements'].split('\n'):
                    if line.strip():
                        changes_made.append(f"- {line.strip()}")
        
        if not changes_made:
            changes_made.append("No changes were necessary - your resume already follows the suggestions!")
            
        return updated_data, changes_made
        
    except Exception as e:
        st.error(f"Error applying suggestions: {str(e)}")
        return resume_data, [f"Failed to apply suggestions: {str(e)}"]
 