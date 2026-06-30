import streamlit as st
from resume_template import generate_resume
from utils.pdf_generator import create_pdf
from utils.gemini_utils import initialize_gemini, analyze_resume_content, get_ats_optimization, apply_ai_suggestions
from utils.resume_parser import ResumeParser
from utils.validators import validate_personal_contact
from utils.analysis_ui import render_analysis_dashboard
import os
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="R.E.A.D.M.L.",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for minimalistic design
def load_css():
    with open("static/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

def _empty_analysis():
    return {'profile_analysis': '', 'skills_analysis': '', 'ats_analysis': ''}


def _empty_scores():
    return {
        'total_score': 0,
        'content_score': 0,
        'skills_score': 0,
        'keyword_score': 0,
        'format_score': 0,
        'readability_score': 0,
        'detected_skills': {
            'programming_languages': [],
            'frameworks_libraries': [],
            'soft_skills': [],
            'tools_technologies': [],
        },
        'feedback': [],
        'improvement_priority': [],
        'missing_role_skills': [],
    }


def initialize_session_state():
    """Initialize all session state variables"""
    if 'projects' not in st.session_state:
        st.session_state.projects = [{
            'title': '',
            'duration': '',
            'tools': '',
            'description': '',
            'responsibilities': ''
        }]
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'personal_info': {},
            'education': {},
            'profile_summary': {},
            'skills': {},
            'achievements': {}
        }
    if 'resume_parser' not in st.session_state:
        st.session_state.resume_parser = ResumeParser()
    if 'create_workflow' not in st.session_state:
        st.session_state.create_workflow = {
            'resume_data': None,
            'parsed_scores': _empty_scores(),
            'ai_analysis': _empty_analysis(),
            'show_preview': False,
            'pdf_path': None,
        }
    if 'upload_workflow' not in st.session_state:
        st.session_state.upload_workflow = {
            'parsed_resume': None,
            'ai_analysis': _empty_analysis(),
            'analyzed': False,
            'target_role': '',
        }

def save_form_data(form_data):
    """Save form data to session state"""
    st.session_state.form_data = form_data

def validate_form(form_data, projects):
    """Validate all required fields"""
    errors = []

    # Personal info validation
    if not form_data['personal_info'].get('name'):
        errors.append("Full name is required")
    errors.extend(validate_personal_contact(
        form_data['personal_info'].get('email', ''),
        form_data['personal_info'].get('phone', ''),
    ))
    if not form_data['personal_info'].get('location'):
        errors.append("Current location is required")
    
    # Education validation
    if not form_data['education'].get('university'):
        errors.append("University name is required")
    if not form_data['education'].get('degree'):
        errors.append("Degree is required")
    
    # Profile validation
    if not form_data['profile_summary'].get('target_role'):
        errors.append("Target role is required")
    if not form_data['profile_summary'].get('summary'):
        errors.append("Profile summary is required")
    
    # Skills validation
    programming = [s.strip() for s in form_data['skills'].get('programming', []) if s.strip()]
    if not programming:
        errors.append("Programming skills are required")
    
    # Projects validation
    for i, project in enumerate(projects):
        if not project.get('title'):
            errors.append(f"Project {i+1} title is required")
        if not project.get('duration'):
            errors.append(f"Project {i+1} duration is required")
        if not project.get('tools'):
            errors.append(f"Project {i+1} tools are required")
        if not project.get('description'):
            errors.append(f"Project {i+1} description is required")
        if not project.get('responsibilities'):
            errors.append(f"Project {i+1} responsibilities are required")
    
    return errors


def resume_data_to_text(resume_data: dict) -> str:
    """Convert structured resume data to plain text for ATS scoring."""
    parts = []
    profile = resume_data.get('profile_summary', {})
    parts.append(f"Target Role: {profile.get('target_role', '')}")
    parts.append(profile.get('summary', ''))

    skills = resume_data.get('skills', {})
    for label, key in [
        ('Programming', 'programming'),
        ('Frameworks', 'frameworks'),
        ('Tools', 'tools'),
        ('Other Skills', 'other'),
        ('Soft Skills', 'soft_skills'),
    ]:
        values = skills.get(key, [])
        if values:
            parts.append(f"{label}: {', '.join(values)}")

    education = resume_data.get('education', {})
    parts.append(f"Education: {education.get('degree', '')} at {education.get('university', '')}")

    for project in resume_data.get('projects', []):
        parts.append(
            f"Project: {project.get('title', '')}. Tools: {project.get('tools', '')}. "
            f"{project.get('description', '')}. "
            f"{' '.join(project.get('responsibilities', []))}"
        )

    return '\n'.join(part for part in parts if part)


def build_resume_data_from_parsed(parsed_data: dict, target_role: str) -> dict:
    """Convert parser output into Gemini-ready resume data."""
    sections = parsed_data.get('sections', {})
    role = target_role or sections.get('role') or sections.get('objective', '').split('\n')[0] or 'Not specified'
    return {
        'profile_summary': {
            'target_role': role,
            'summary': sections.get('summary', sections.get('objective', '')),
        },
        'skills': {
            'programming': [s.strip() for s in parsed_data.get('skills', []) if s.strip()],
            'frameworks': [s.strip() for s in parsed_data.get('frameworks', []) if s.strip()],
            'other': [s.strip() for s in parsed_data.get('other_skills', []) if s.strip()],
            'soft_skills': [],
            'tools': [],
        },
        'education': {
            'university': sections.get('education', '').split('\n')[0] if sections.get('education') else 'Not specified',
            'degree': sections.get('degree', sections.get('education', 'Not specified')),
        },
        'projects': [
            {
                'title': project.get('title', ''),
                'description': project.get('description', ''),
                'responsibilities': project.get('responsibilities', '').split('\n'),
                'tools': project.get('tools', ''),
                'duration': project.get('duration', ''),
            }
            for project in parsed_data.get('projects', [])
        ] if parsed_data.get('projects') else [],
    }


def skills_data_from_scores(scores: dict, resume_data: dict = None) -> dict:
    """Build skills display data from parser scores or form resume data."""
    detected = scores.get('detected_skills', {})
    if detected and any(detected.values()):
        return {
            'programming_languages': sorted(list(detected.get('programming_languages', []))),
            'frameworks_libraries': sorted(list(detected.get('frameworks_libraries', []))),
            'soft_skills': sorted(list(detected.get('soft_skills', []))),
            'tools_technologies': sorted(list(detected.get('tools_technologies', []))),
        }
    if resume_data:
        skills = resume_data.get('skills', {})
        return {
            'programming_languages': sorted([s for s in skills.get('programming', []) if s.strip()]),
            'frameworks_libraries': sorted([s for s in skills.get('frameworks', []) if s.strip()]),
            'soft_skills': sorted([s for s in skills.get('soft_skills', []) if s.strip()]),
            'tools_technologies': sorted([s for s in skills.get('tools', []) if s.strip()]),
        }
    return {
        'programming_languages': [],
        'frameworks_libraries': [],
        'soft_skills': [],
        'tools_technologies': [],
    }


def run_resume_analysis(resume_data: dict, resume_text: str, target_role: str, job_description: str = None):
    """Run ATS scoring and AI analysis, returning scores and analysis dicts."""
    scores = st.session_state.resume_parser.calculate_ats_score(
        resume_text,
        job_description=job_description or target_role,
        target_role=target_role,
    )
    if not st.session_state.gemini_model:
        raise RuntimeError("AI model not initialized. Please check your API configuration.")

    analysis = analyze_resume_content(st.session_state.gemini_model, resume_data)
    ats_analysis = get_ats_optimization(st.session_state.gemini_model, resume_data)
    return scores, {
        'profile_analysis': analysis['profile_analysis'],
        'skills_analysis': analysis['skills_analysis'],
        'ats_analysis': ats_analysis['ats_analysis'],
    }


# Initialize Gemini API
def initialize_ai():
    """Initialize AI components"""
    if 'gemini_model' not in st.session_state:
        try:
            api_key = st.secrets.api_keys.GEMINI_API_KEY
            if not api_key:
                st.error("Gemini API key not found. Please check your secrets.toml file.")
                return
            
            model = initialize_gemini(api_key)
            if model:
                st.session_state.gemini_model = model
            else:
                st.error("Failed to initialize AI analysis system. Please check your API key.")
        except Exception as e:
            st.error(f"Error initializing AI: {str(e)}")
            st.info("""
            Please check:
            1. Your API key is correct in .streamlit/secrets.toml
            2. You have internet connection
            3. The API service is available
            """)
            return None

def render_create_preview_and_analysis():
    """Show PDF download and analysis for the create-resume workflow only."""
    workflow = st.session_state.create_workflow
    if not workflow.get('show_preview') or not workflow.get('resume_data'):
        return

    resume_data = workflow['resume_data']
    try:
        with st.spinner("Generating your resume..."):
            html_resume = generate_resume(resume_data)
            try:
                if workflow.get('pdf_path') and os.path.exists(workflow['pdf_path']):
                    try:
                        os.remove(workflow['pdf_path'])
                    except OSError:
                        pass
                pdf_path = create_pdf(html_resume, resume_data["personal_info"]["name"])
                workflow['pdf_path'] = pdf_path
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="Download PDF",
                            data=f.read(),
                            file_name=f"{resume_data['personal_info']['name'].replace(' ', '_')}_Resume.pdf",
                            mime="application/pdf",
                        )
                else:
                    st.error("PDF file was not created successfully. Please try again.")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")

        with st.expander("AI Resume Analysis", expanded=True):
            target_role = resume_data.get('profile_summary', {}).get('target_role', '')
            scores = workflow.get('parsed_scores', _empty_scores())
            analysis = workflow.get('ai_analysis', _empty_analysis())
            skills_data = skills_data_from_scores(scores, resume_data)
            render_analysis_dashboard(analysis, scores, target_role, skills_data)
    except Exception as e:
        st.error(f"An error occurred while generating your resume: {str(e)}")


def render_resume_upload_section():
    """Render the resume upload and analysis section (isolated workflow state)."""
    workflow = st.session_state.upload_workflow

    st.markdown("""
    <div class="section-title text-center">
        <h2>Resume Analysis</h2>
        <p>Upload your existing resume for role-focused AI analysis</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload your resume (PDF or DOCX)",
        type=['pdf', 'docx'],
        help="We support PDF and DOCX formats",
        key="upload_resume_file",
    )

    detected_role = ''
    if workflow.get('parsed_resume'):
        detected_role = workflow['parsed_resume'].get('sections', {}).get('role', '')

    target_role = st.text_input(
        "Target Role*",
        value=workflow.get('target_role') or detected_role,
        placeholder="e.g., Software Developer, Data Analyst",
        help="All analysis tabs focus exclusively on this role and its tech stack",
        key="upload_target_role",
    )
    workflow['target_role'] = target_role

    job_description = st.text_area(
        "Job Description (optional)",
        height=150,
        help="Paste a job description for more precise keyword matching",
        key="upload_job_description",
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("Analyze Resume", use_container_width=True, key="analyze_uploaded_resume")

    if not (uploaded_file and analyze_button):
        if workflow.get('analyzed') and workflow.get('parsed_resume'):
            _render_upload_results(workflow)
        return

    if not target_role.strip():
        st.error("Target role is required. Enter the role you are applying for.")
        return

    try:
        parsed_data = st.session_state.resume_parser.get_parsed_data(uploaded_file)
        if not parsed_data:
            st.error("Could not parse the uploaded resume.")
            return

        resume_data = build_resume_data_from_parsed(parsed_data, target_role.strip())
        resume_data['profile_summary']['target_role'] = target_role.strip()

        with st.spinner("Analyzing your resume with AI..."):
            scores, analysis = run_resume_analysis(
                resume_data,
                parsed_data['full_text'],
                target_role.strip(),
                job_description=job_description or None,
            )

        parsed_data['scores'] = scores
        workflow.update({
            'parsed_resume': parsed_data,
            'parsed_scores': scores,
            'ai_analysis': analysis,
            'analyzed': True,
            'target_role': target_role.strip(),
        })
        _render_upload_results(workflow)
    except Exception as e:
        st.error(f"An error occurred during AI analysis: {str(e)}")
        st.info("Please check your API key or try again later.")


def _render_upload_results(workflow: dict):
    """Render analysis dashboard for uploaded resume."""
    parsed_data = workflow.get('parsed_resume') or {}
    scores = parsed_data.get('scores') or workflow.get('parsed_scores') or _empty_scores()
    analysis = workflow.get('ai_analysis') or _empty_analysis()
    target_role = workflow.get('target_role') or scores.get('target_role', '')

    resume_data = build_resume_data_from_parsed(parsed_data, target_role)
    resume_data['profile_summary']['target_role'] = target_role
    skills_data = skills_data_from_scores(scores, resume_data)

    st.markdown("## AI Resume Analysis")
    render_analysis_dashboard(analysis, scores, target_role, skills_data)


def main():
    """Main application function"""
    initialize_session_state()
    initialize_ai()
    load_css()
    
    # Header
    st.markdown(""" <div class="header">
        <div class="header-content">
            <h1 class="header-title">R.E.A.D.M.L.</h1>
            <h2 class="header-subtitle">Resume Enhancing, Analyzing & Developing using Machine Learning</h2>
            <div class="header-divider"></div>
            <div class="header-description">
                    Elevate your resume with AI-powered optimization. Our intelligent system crafts professional, 
    ATS-friendly resumes while providing smart suggestions to make your experience stand out.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add tabs for different features
    tab1, tab2 = st.tabs(["Create New Resume", "Analyze Existing Resume"])
    
    with tab1:
        # Existing resume creation form
        with st.container():
            with st.expander("Fill the Resume Details", expanded=True):
                # First Form (Personal Info, Education, Profile, Skills)
                with st.form("resume_form"):
                    # Personal Information
                    st.markdown("### Personal Information")
                    col1, col2 = st.columns(2)
                    full_name = col1.text_input("Full Name*", placeholder="Enter your full name", 
                                               value=st.session_state.form_data['personal_info'].get('name', ''))
                    email = col2.text_input("Email*", placeholder="Enter your email address", 
                                          value=st.session_state.form_data['personal_info'].get('email', ''))
                    
                    col1, col2 = st.columns(2)
                    phone = col1.text_input("Phone*", placeholder="Enter your phone number", 
                                          value=st.session_state.form_data['personal_info'].get('phone', ''))
                    linkedin = col2.text_input("LinkedIn", placeholder="Enter your LinkedIn profile URL", 
                                             value=st.session_state.form_data['personal_info'].get('linkedin', ''))
                    col1, col2 = st.columns(2)
                    github = col1.text_input("GitHub", placeholder="Enter your GitHub profile URL", 
                                           value=st.session_state.form_data['personal_info'].get('github', ''))
                    location = col2.text_input("Current Location*", placeholder="Enter your current location (e.g., City, State)", 
                                           value=st.session_state.form_data['personal_info'].get('location', ''))
                    
                    # Education
                    st.markdown("### Education")
                    university = st.text_input("University*", placeholder="Enter your university name", 
                                             value=st.session_state.form_data['education'].get('university', ''))
                    degree = st.text_input("Degree in*", placeholder="Enter your degree and major", 
                                         value=st.session_state.form_data['education'].get('degree', ''))
                    
                    # Handle graduation date input
                    grad_date = st.session_state.form_data['education'].get('graduation_date')
                    if grad_date:
                        try:
                            if isinstance(grad_date, str):
                                grad_date = datetime.strptime(grad_date, "%B %Y")
                        except ValueError:
                            grad_date = datetime.now()
                    else:
                        grad_date = datetime.now()
                        
                    graduation_date = st.date_input("Expected Graduation*", value=grad_date)
                    gpa = st.text_input("CGPA/GPA", placeholder="Enter your GPA (e.g., 3.8)", 
                                      value=st.session_state.form_data['education'].get('gpa', ''))
                    
                    # Profile Summary
                    st.markdown("### Profile Summary")
                    target_role = st.text_input("Target Role*", placeholder="Enter your target role", 
                                              value=st.session_state.form_data['profile_summary'].get('target_role', ''))
                    profile_summary = st.text_area("Summary*", 
                        placeholder="Enter your professional background and career goals in bullet points:\n- First point\n- Second point\n- Third point", 
                        height=200,
                        value=st.session_state.form_data['profile_summary'].get('summary', ''))
                    
                    # Skills
                    st.markdown("### Skills")
                    programming_skills = st.text_input("Programming Skills (comma separated)*", 
                        placeholder="List your programming languages (e.g., Python, Java, JavaScript)",
                        value=", ".join(st.session_state.form_data['skills'].get('programming', [])))
                    soft_skills = st.text_input("Soft Skills (comma separated)", 
                        placeholder="List your soft skills (e.g., Leadership, Communication, Team Management)",
                        value=", ".join(st.session_state.form_data['skills'].get('soft_skills', [])))
                    frameworks = st.text_input("Library / Frameworks (comma separated)", 
                        placeholder="List your frameworks and libraries (e.g., React, Node.js, TensorFlow)",
                        value=", ".join(st.session_state.form_data['skills'].get('frameworks', [])))
                    other_skills = st.text_input("Other Skills (comma separated)", 
                        placeholder="List your other relevant skills (e.g., Agile, System Design)",
                        value=", ".join(st.session_state.form_data['skills'].get('other', [])))
                    tools = st.text_input("Tools (comma separated)", 
                        placeholder="List the tools and technologies you use (e.g., Git, Docker, VS Code)",
                        value=", ".join(st.session_state.form_data['skills'].get('tools', [])))
                    
                    # Projects Section
                    st.markdown("### Projects")
                    for i, project in enumerate(st.session_state.projects):
                        st.markdown(f"#### Project {i+1}")
                        project['title'] = st.text_input(
                            f"Project {i+1} Title*", 
                            value=project.get('title', ''),
                            placeholder="Enter project title",
                            key=f"title_{i}")
                        project['duration'] = st.text_input(
                            f"Project {i+1} Duration*", 
                            value=project.get('duration', ''),
                            placeholder="Enter project duration (e.g., Jan 2023 - Present)",
                            key=f"duration_{i}")
                        project['tools'] = st.text_input(
                            f"Project {i+1} Tools*", 
                            value=project.get('tools', ''),
                            placeholder="List technologies used (e.g., React, Node.js, MongoDB)",
                            key=f"tools_{i}")
                        project['description'] = st.text_area(
                            f"Project {i+1} Description*", 
                            value=project.get('description', ''),
                            placeholder="Describe your project's purpose and key features...",
                            height=150,
                            key=f"desc_{i}")
                        project['responsibilities'] = st.text_area(
                            f"Project {i+1} Responsibilities*", 
                            value=project.get('responsibilities', ''),
                            placeholder="List your key responsibilities and achievements:\n- Responsibility 1\n- Responsibility 2",
                            height=200,
                            key=f"resp_{i}")
                        
                        if i < len(st.session_state.projects) - 1:
                            st.markdown("---")
                    
                    # Achievements
                    st.markdown("### Academic Achievements")
                    achievements = st.session_state.form_data.get('achievements', [])
                    achievement1 = st.text_input("Achievement 1", 
                        value=achievements[0] if len(achievements) > 0 else '',
                        placeholder="Enter your academic achievement (e.g., Dean's List, Scholarships)")
                    achievement2 = st.text_input("Achievement 2", 
                        value=achievements[1] if len(achievements) > 1 else '',
                        placeholder="Enter another academic achievement (e.g., Research Awards, Competitions)")
                    
                    # Project management buttons inside form
                    button_cols = st.columns([1, 1])
                    add_clicked = button_cols[0].form_submit_button("Add Project")
                    if len(st.session_state.projects) > 1:
                        remove_clicked = button_cols[1].form_submit_button("Remove Project")

                    if add_clicked:
                        st.session_state.projects.append({
                            'title': '',
                            'duration': '',
                            'tools': '',
                            'description': '',
                            'responsibilities': ''
                        })
                        st.rerun()

                    if len(st.session_state.projects) > 1 and 'remove_clicked' in locals() and remove_clicked:
                        st.session_state.projects.pop()
                        st.rerun()

                    # Generate Resume button in center
                    st.markdown("<div style='text-align: center; margin: 2rem 0;'>", unsafe_allow_html=True)
                    generate_clicked = st.form_submit_button("Generate Resume", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    if generate_clicked:
                        # Prepare form data dictionary
                        form_data = {
                            "personal_info": {
                                "name": full_name,
                                "email": email,
                                "phone": phone,
                                "linkedin": linkedin,
                                "github": github,
                                "location": location
                            },
                            "education": {
                                "university": university,
                                "degree": degree,
                                "graduation_date": graduation_date,
                                "gpa": gpa
                            },
                            "profile_summary": {
                                "target_role": target_role,
                                "summary": profile_summary
                            },
                            "skills": {
                                "programming": [s.strip() for s in programming_skills.split(",") if s.strip()],
                                "soft_skills": [s.strip() for s in soft_skills.split(",") if s.strip()] if soft_skills else [],
                                "frameworks": [s.strip() for s in frameworks.split(",") if s.strip()] if frameworks else [],
                                "other": [s.strip() for s in other_skills.split(",") if s.strip()] if other_skills else [],
                                "tools": [s.strip() for s in tools.split(",") if s.strip()] if tools else []
                            },
                            "achievements": [
                                achievement1,
                                achievement2
                            ] if achievement1 or achievement2 else []
                        }
                        
                        # Validate form
                        errors = validate_form(form_data, st.session_state.projects)
                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            save_form_data(form_data)
                            
                            # Prepare final resume data
                            resume_data = {
                                **st.session_state.form_data,
                                "projects": [
                                    {
                                        "title": project['title'],
                                        "duration": project['duration'],
                                        "tools": project['tools'],
                                        "description": project['description'],
                                        "responsibilities": project['responsibilities'].split("\n")
                                    }
                                    for project in st.session_state.projects
                                ]
                            }
                            
                            resume_text = resume_data_to_text(resume_data)
                            role = resume_data.get('profile_summary', {}).get('target_role', '')

                            try:
                                with st.spinner("Analyzing your resume with AI..."):
                                    scores, analysis = run_resume_analysis(
                                        resume_data,
                                        resume_text,
                                        role,
                                        job_description=role,
                                    )

                                st.session_state.create_workflow.update({
                                    'resume_data': resume_data,
                                    'parsed_scores': scores,
                                    'ai_analysis': analysis,
                                    'show_preview': True,
                                    'pdf_path': None,
                                })
                                st.session_state.create_workflow['parsed_scores']['detected_skills'] = {
                                    'programming_languages': resume_data.get('skills', {}).get('programming', []),
                                    'frameworks_libraries': resume_data.get('skills', {}).get('frameworks', []),
                                    'soft_skills': resume_data.get('skills', {}).get('soft_skills', []),
                                    'tools_technologies': resume_data.get('skills', {}).get('tools', []),
                                }
                            except Exception as e:
                                st.error(f"An error occurred during analysis: {str(e)}")
                                st.info("Please check your input data and try again.")

        render_create_preview_and_analysis()

    with tab2:
        render_resume_upload_section()


if __name__ == "__main__":
    main()