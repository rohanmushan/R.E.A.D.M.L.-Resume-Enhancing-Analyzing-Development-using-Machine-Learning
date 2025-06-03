import streamlit as st
from resume_template import generate_resume
from utils.pdf_generator import create_pdf
from utils.gemini_utils import initialize_gemini, analyze_resume_content, get_ats_optimization, apply_ai_suggestions
from utils.resume_parser import ResumeParser
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

def initialize_session_state():
    """Initialize all session state variables"""
    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = None
    if 'pdf_path' not in st.session_state:
        st.session_state.pdf_path = None
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
    if 'parsed_resume' not in st.session_state:
        st.session_state.parsed_resume = None

def save_form_data(form_data):
    """Save form data to session state"""
    st.session_state.form_data = form_data

def validate_form(form_data, projects):
    """Validate all required fields"""
    errors = []
    
    # Personal info validation
    if not form_data['personal_info'].get('name'):
        errors.append("Full name is required")
    if not form_data['personal_info'].get('email'):
        errors.append("Email is required")
    if not form_data['personal_info'].get('phone'):
        errors.append("Phone number is required")
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
    if not form_data['skills'].get('programming'):
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

def render_resume_upload_section():
    """Render the resume upload and analysis section"""
    # Ensure Gemini model is initialized
    if 'gemini_model' not in st.session_state:
        try:
            api_key = st.secrets.api_keys.GEMINI_API_KEY
            if not api_key:
                st.error("Gemini API key not found. Please check your secrets.toml file.")
                return
            model = initialize_gemini(api_key)
            if model:
                st.session_state.gemini_model = model
        except Exception as e:
            st.error(f"Error initializing AI: {str(e)}")
            return

    st.markdown("""
    <div class="section-title text-center">
        <h2>Resume Analysis</h2>
        <p>Upload your existing resume for comprehensive AI-powered analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload your resume (PDF or DOCX)",
        type=['pdf', 'docx'],
        help="We support PDF and DOCX formats"
    )
    
    job_description = st.text_area(
        "Paste the job description (optional)",
        height=150,
        help="Adding a job description will help us provide more targeted analysis"
    )
    
    # Center the analyze button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("Analyze Resume", use_container_width=True)
    
    if uploaded_file and analyze_button:
        with st.spinner("Analyzing your resume..."):
            try:
                # Parse resume
                parsed_data = st.session_state.resume_parser.get_parsed_data(uploaded_file)
                
                if parsed_data:
                    # Calculate ATS score with job description if provided
                    if job_description:
                        parsed_data['scores'] = st.session_state.resume_parser.calculate_ats_score(
                            parsed_data['full_text'],
                            job_description
                        )
                    
                    st.session_state.parsed_resume = parsed_data
                    
                    # Convert parsed data to format expected by Gemini analysis
                    resume_data = {
                        'profile_summary': {
                            'target_role': job_description[:100] if job_description else parsed_data['sections'].get('role', parsed_data['sections'].get('objective', '').split('\n')[0] if parsed_data['sections'].get('objective') else 'Not specified'),
                            'summary': parsed_data['sections'].get('summary', parsed_data['sections'].get('objective', ''))
                        },
                        'skills': {
                            'programming': [skill.strip() for skill in parsed_data['skills'] if skill.strip()],
                            'frameworks': [skill.strip() for skill in parsed_data.get('frameworks', []) if skill.strip()],
                            'other': [skill.strip() for skill in parsed_data.get('other_skills', []) if skill.strip()]
                        },
                        'education': {
                            'university': parsed_data['sections'].get('education', '').split('\n')[0] if parsed_data['sections'].get('education') else 'Not specified',
                            'degree': parsed_data['sections'].get('degree', parsed_data['sections'].get('education', 'Not specified'))
                        },
                        'projects': [
                            {
                                'title': project.get('title', ''),
                                'description': project.get('description', ''),
                                'responsibilities': project.get('responsibilities', '').split('\n'),
                                'tools': project.get('tools', ''),
                                'duration': project.get('duration', '')
                            }
                            for project in parsed_data.get('projects', [])
                        ] if parsed_data.get('projects') else []
                    }

                    # Add any additional sections found in parsed data
                    for section_name, content in parsed_data['sections'].items():
                        if section_name.lower() not in ['summary', 'objective', 'education', 'skills', 'projects']:
                            resume_data[section_name.lower()] = content
                    
                    # Get AI analysis using the same functions as generated resumes
                    if not st.session_state.gemini_model:
                        st.error("AI model not initialized. Please check your API configuration.")
                        return

                    with st.expander("AI Resume Analysis", expanded=True):
                        try:
                            with st.spinner("Analyzing your resume with AI..."):
                                # Get AI analysis
                                analysis = analyze_resume_content(st.session_state.gemini_model, resume_data)
                                ats_analysis = get_ats_optimization(st.session_state.gemini_model, resume_data)
                                
                                # Store analysis in session state for later use
                                st.session_state.ai_analysis = {
                                    'profile_analysis': analysis['profile_analysis'],
                                    'skills_analysis': analysis['skills_analysis'],
                                    'ats_analysis': ats_analysis['ats_analysis']
                                }
                                
                                # Display Profile Summary Analysis
                                st.subheader("Profile Summary Analysis")
                                st.markdown(analysis['profile_analysis'])
                                
                                # Display Skills Analysis
                                st.subheader("Skills Analysis")
                                st.markdown(analysis['skills_analysis'])
                                
                                # Display ATS Optimization
                                st.subheader("ATS Optimization")
                                st.markdown(ats_analysis['ats_analysis'])
                                
                                # Add download button for current analysis
                                current_suggestions = (
                                    f"AI Resume Analysis Report\n"
                                    f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                    f"For: {resume_data['profile_summary']['target_role']}\n\n"
                                    f"=== Profile Summary Analysis ===\n"
                                    f"{analysis['profile_analysis']}\n\n"
                                    f"=== Skills Analysis ===\n"
                                    f"{analysis['skills_analysis']}\n\n"
                                    f"=== ATS Optimization ===\n"
                                    f"{ats_analysis['ats_analysis']}\n"
                                )
                                
                                st.download_button(
                                    label="Download Analysis Report",
                                    data=current_suggestions,
                                    file_name=f"AI_Resume_Analysis_{datetime.now().strftime('%Y%m%d')}.txt",
                                    mime="text/plain"
                                )
                        except Exception as e:
                            st.error(f"An error occurred during AI analysis: {str(e)}")
                            st.info("Please check your API key or try again later.")
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.info("Please try again or contact support if the issue persists.")

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
                                "programming": [s.strip() for s in programming_skills.split(",")],
                                "soft_skills": [s.strip() for s in soft_skills.split(",")] if soft_skills else [],
                                "frameworks": [s.strip() for s in frameworks.split(",")] if frameworks else [],
                                "other": [s.strip() for s in other_skills.split(",")] if other_skills else [],
                                "tools": [s.strip() for s in tools.split(",")] if tools else []
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
                            
                            # Store in session state
                            st.session_state.resume_data = resume_data
                            st.session_state.show_preview = True  # Flag to show preview section

    with tab2:
        # New resume upload and analysis section
        render_resume_upload_section()

    # Preview and Download section (outside form)
    if st.session_state.get('show_preview', False):
        try:
            with st.spinner("Generating your resume..."):
                # Generate HTML resume
                html_resume = generate_resume(st.session_state.resume_data)
                
                # Create PDF
                try:
                    # Clean up old PDF if it exists
                    if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
                        try:
                            os.remove(st.session_state.pdf_path)
                        except:
                            pass
                            
                    pdf_path = create_pdf(html_resume, st.session_state.resume_data["personal_info"]["name"])
                    st.session_state.pdf_path = pdf_path
                    
                    # Download button (outside form)
                    if os.path.exists(st.session_state.pdf_path):
                        with open(st.session_state.pdf_path, "rb") as f:
                            pdf_data = f.read()
                            st.download_button(
                                label="Download PDF",
                                data=pdf_data,
                                file_name=f"{st.session_state.resume_data['personal_info']['name'].replace(' ', '_')}_Resume.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.error("PDF file was not created successfully. Please try again.")
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
                
            # AI Analysis Section (after resume generation)
            if st.session_state.get('show_preview', False) and st.session_state.resume_data:
                with st.expander("AI Resume Analysis", expanded=True):
                    try:
                        with st.spinner("Analyzing your resume with AI..."):
                            # Get AI analysis
                            analysis = analyze_resume_content(st.session_state.gemini_model, st.session_state.resume_data)
                            ats_analysis = get_ats_optimization(st.session_state.gemini_model, st.session_state.resume_data)
                            
                            # Store analysis in session state for later use
                            st.session_state.ai_analysis = {
                                'profile_analysis': analysis['profile_analysis'],
                                'skills_analysis': analysis['skills_analysis'],
                                'ats_analysis': ats_analysis['ats_analysis']
                            }
                            
                            # Display Profile Summary Analysis
                            st.subheader("Profile Summary Analysis")
                            st.markdown(analysis['profile_analysis'])
                            
                            # Display Skills Analysis
                            st.subheader("Skills Analysis")
                            st.markdown(analysis['skills_analysis'])
                            
                            # Display ATS Optimization
                            st.subheader("ATS Optimization")
                            st.markdown(ats_analysis['ats_analysis'])
                            
                            # Add download button for current analysis
                            current_suggestions = (
                                f"AI Resume Analysis Report\n"
                                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"For: {st.session_state.resume_data['personal_info']['name']}\n\n"
                                f"=== Profile Summary Analysis ===\n"
                                f"{analysis['profile_analysis']}\n\n"
                                f"=== Skills Analysis ===\n"
                                f"{analysis['skills_analysis']}\n\n"
                                f"=== ATS Optimization ===\n"
                                f"{ats_analysis['ats_analysis']}\n"
                            )
                            
                            st.download_button(
                                label="Download Analysis Report",
                                data=current_suggestions,
                                file_name=f"AI_Resume_Analysis_{datetime.now().strftime('%Y%m%d')}.txt",
                                mime="text/plain"
                            )
                    except Exception as e:
                        st.error(f"An error occurred during AI analysis: {str(e)}")
                        st.info("Please check your API key or try again later.")
                
        except Exception as e:
            st.error(f"An error occurred while generating your resume: {str(e)}")
            st.info("Please try again or contact support if the issue persists.")

if __name__ == "__main__":
    main()