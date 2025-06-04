import streamlit as st
from resume_template import generate_resume
from utils.pdf_generator import create_pdf
from utils.gemini_utils import initialize_gemini, analyze_resume_content, get_ats_optimization, apply_ai_suggestions
from utils.resume_parser import ResumeParser
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
        with st.expander("AI Resume Analysis", expanded=True):
            try:
                with st.spinner("Analyzing your resume..."):
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

                        # Get AI analysis
                        analysis = analyze_resume_content(st.session_state.gemini_model, resume_data)
                        ats_analysis = get_ats_optimization(st.session_state.gemini_model, resume_data)
                        
                        # Store analysis in session state for later use
                        st.session_state.ai_analysis = {
                            'profile_analysis': analysis['profile_analysis'],
                            'skills_analysis': analysis['skills_analysis'],
                            'ats_analysis': ats_analysis['ats_analysis']
                        }

                        # Create tabs for different analysis sections
                        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                            "ATS Score", 
                            "Profile Analysis",
                            "Skills Analysis",
                            "Optimization",
                            "Summary Report",
                            "Visualization"
                        ])
                        
                        with tab1:
                            st.subheader("ATS Compatibility Score")
                            
                            # Display scores in columns with improved styling
                            col1, col2, col3 = st.columns(3)
                            
                            # Calculate total score percentage
                            total_score = parsed_data['scores']['total_score']
                            
                            with col1:
                                st.metric(
                                    "Overall ATS Score", 
                                    f"{total_score}%",
                                    delta="Target: 85%+" if total_score < 85 else None,
                                    delta_color="inverse"
                                )
                                
                            with col2:
                                st.metric(
                                    "Keyword Match", 
                                    f"{parsed_data['scores']['keyword_score']}%",
                                    delta="Target: 80%+" if parsed_data['scores']['keyword_score'] < 80 else None,
                                    delta_color="inverse"
                                )
                                
                            with col3:
                                st.metric(
                                    "Format Score", 
                                    f"{parsed_data['scores']['format_score']}%",
                                    delta="Target: 90%+" if parsed_data['scores']['format_score'] < 90 else None,
                                    delta_color="inverse"
                                )
                                
                            # Display score breakdown with improved visualization
                            st.subheader("Detailed Score Breakdown")
                            scores_df = pd.DataFrame({
                                'Category': [
                                    'Content Quality',
                                    'Skills Coverage',
                                    'Keyword Optimization',
                                    'Format & Structure',
                                    'Readability'
                                ],
                                'Score': [
                                    parsed_data['scores']['content_score'],
                                    parsed_data['scores']['skills_score'],
                                    parsed_data['scores']['keyword_score'],
                                    parsed_data['scores']['format_score'],
                                    parsed_data['scores']['readability_score']
                                ]
                            })
                            
                            # Display as bar chart
                            st.bar_chart(scores_df.set_index('Category'))
                        
                        with tab2:
                            st.subheader("Profile Analysis")
                            st.markdown(analysis['profile_analysis'])
                        
                        with tab3:
                            st.subheader("Skills Analysis")
                            try:
                                # Get skills data based on the source (uploaded or generated)
                                skills_data = {}
                                
                                if 'parsed_resume' in st.session_state and st.session_state.parsed_resume:
                                    # For uploaded resumes
                                    skills_data = {
                                        'programming_languages': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('programming_languages', []),
                                        'frameworks_libraries': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('frameworks_libraries', []),
                                        'soft_skills': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('soft_skills', []),
                                        'tools_technologies': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('tools_technologies', [])
                                    }
                                elif 'resume_data' in st.session_state and st.session_state.resume_data:
                                    # For generated resumes
                                    skills = st.session_state.resume_data.get('skills', {})
                                    skills_data = {
                                        'programming_languages': skills.get('programming', []),
                                        'frameworks_libraries': skills.get('frameworks', []),
                                        'soft_skills': skills.get('soft_skills', []),
                                        'tools_technologies': skills.get('tools', [])
                                    }
                                    
                                    # Clean up empty strings from lists
                                    for category in skills_data:
                                        skills_data[category] = [skill.strip() for skill in skills_data[category] if skill.strip()]

                                if not any(skills_data.values()):
                                    st.warning("No skills data available. Please ensure your resume includes skills information.")
                                    return

                                # Technical Skills Analysis
                                st.markdown("### Technical Skills Analysis")
                                
                                # Programming Languages
                                if skills_data.get('programming_languages'):
                                    st.markdown("""
                                    #### Programming Languages
                                    Your resume demonstrates proficiency in multiple programming languages. Here's a detailed analysis:
                                    """)
                                    
                                    langs = sorted(skills_data['programming_languages'])
                                    st.markdown("**Core Languages:**")
                                    st.markdown("\n".join([f"• `{lang}` - Demonstrated through projects and experience" 
                                                        for lang in langs[:3]]))
                                    
                                    if len(langs) > 3:
                                        st.markdown("\n**Additional Languages:**")
                                        st.markdown("\n".join([f"• `{lang}`" for lang in langs[3:]]))
                                    
                                    st.markdown("""
                                    **Analysis:**
                                    Your programming language portfolio shows a good mix of modern and established technologies.
                                    Consider focusing on deepening expertise in your core languages while maintaining working
                                    knowledge of others.
                                    """)

                                # Frameworks and Libraries
                                if skills_data.get('frameworks_libraries'):
                                    st.markdown("""
                                    #### Frameworks & Libraries
                                    Your technical stack includes various frameworks and libraries:
                                    """)
                                    
                                    frameworks = sorted(skills_data['frameworks_libraries'])
                                    for fw in frameworks:
                                        st.markdown(f"• `{fw}`")
                                    
                                    st.markdown("""
                                    **Framework Proficiency:**
                                    Your experience with these frameworks indicates a solid foundation in software development.
                                    This diverse knowledge base allows you to adapt to different project requirements and
                                    technical environments.
                                    """)

                                # Professional Skills Analysis
                                st.markdown("### Professional Skills Analysis")
                                
                                if skills_data.get('soft_skills'):
                                    st.markdown("""
                                    #### Soft Skills & Professional Competencies
                                    Your resume demonstrates the following professional capabilities:
                                    """)
                                    
                                    soft_skills = sorted(skills_data['soft_skills'])
                                    for skill in soft_skills:
                                        st.markdown(f"• {skill}")
                                    
                                    st.markdown("""
                                    **Professional Impact:**
                                    Your soft skills complement your technical abilities, showing a well-rounded
                                    professional profile. These skills are particularly valuable for:
                                    • Team collaboration and leadership roles
                                    • Project management and coordination
                                    • Client interaction and communication
                                    """)

                                # Tools and Technologies
                                if skills_data.get('tools_technologies'):
                                    st.markdown("""
                                    #### Tools & Technologies
                                    Your proficiency extends to various development tools and technologies:
                                    """)
                                    
                                    tools = sorted(skills_data['tools_technologies'])
                                    for tool in tools:
                                        st.markdown(f"• `{tool}`")
                                    
                                    st.markdown("""
                                    **Technical Environment:**
                                    Your experience with these tools indicates familiarity with modern development
                                    practices and environments. This toolkit supports efficient development workflows
                                    and collaborative work.
                                    """)

                                # Overall Skills Assessment
                                st.markdown("### Overall Skills Assessment")
                                
                                # Calculate total skills and distributions
                                total_skills = sum(len(skills) for skills in skills_data.values())
                                
                                st.markdown(f"""
                                #### Comprehensive Analysis
                                
                                Your skill profile includes {total_skills} distinct competencies across various categories.
                                The distribution shows:
                                """)
                                
                                for category, skills in skills_data.items():
                                    if skills:
                                        percentage = (len(skills) / total_skills) * 100
                                        st.markdown(f"• **{category.replace('_', ' ').title()}**: {len(skills)} skills ({percentage:.1f}%)")
                                
                                st.markdown("""
                                #### Key Observations
                                
                                1. **Technical Depth**
                                   - Your technical skills show both breadth and depth
                                   - Good balance between fundamental and specialized technologies
                                   - Evidence of continuous learning and adaptation
                                
                                2. **Professional Development**
                                   - Strong foundation in core development practices
                                   - Demonstrated ability to work with modern tools
                                   - Clear progression in skill acquisition
                                
                                3. **Areas of Excellence**
                                   - Solid programming language foundation
                                   - Practical experience with industry-standard tools
                                   - Balance of technical and soft skills
                                """)

                                # Recommendations
                                st.markdown("""
                                ### Recommendations for Growth
                                
                                Based on your current skill set, consider:
                                
                                1. **Skill Enhancement**
                                   - Deepen expertise in your primary programming languages
                                   - Stay updated with the latest versions and features
                                   - Practice through complex projects
                                
                                2. **Knowledge Expansion**
                                   - Explore complementary technologies
                                   - Focus on high-demand areas in your field
                                   - Maintain awareness of industry trends
                                
                                3. **Professional Development**
                                   - Seek opportunities to lead technical initiatives
                                   - Share knowledge through mentoring or documentation
                                   - Contribute to open-source projects
                                """)

                            except Exception as e:
                                st.error(f"An error occurred in skills analysis: {str(e)}")
                                st.info("Please ensure your resume includes skills information and try again.")
                        
                        with tab4:
                            st.subheader("ATS Analysis")
                            
                            if 'scores' in st.session_state.parsed_resume:
                                scores = st.session_state.parsed_resume['scores']
                                
                                # Core ATS Analysis
                                st.markdown("### ATS Score Overview")
                                
                                # Display scores in a clean layout
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                        st.metric(
                                        "Overall ATS Score",
                                        f"{scores.get('total_score', 0)}%",
                                        delta="Target: 85%+" if scores.get('total_score', 0) < 85 else None,
                                            delta_color="inverse"
                                        )
                                        
                                with col2:
                                        st.metric(
                                        "Keyword Match",
                                            f"{scores.get('keyword_score', 0)}%",
                                            delta="Target: 80%+" if scores.get('keyword_score', 0) < 80 else None,
                                            delta_color="inverse"
                                        )
                                        
                                with col3:
                                        st.metric(
                                            "Format Score",
                                            f"{scores.get('format_score', 0)}%",
                                            delta="Target: 90%+" if scores.get('format_score', 0) < 90 else None,
                                            delta_color="inverse"
                                        )
                                        
                                # Score Breakdown
                                st.markdown("### Score Breakdown")
                                scores_df = pd.DataFrame({
                                    'Category': [
                                        'Content Quality',
                                        'Skills Coverage',
                                        'Keyword Optimization',
                                        'Format & Structure',
                                        'Readability'
                                    ],
                                    'Score': [
                                        scores.get('content_score', 0),
                                        scores.get('skills_score', 0),
                                        scores.get('keyword_score', 0),
                                        scores.get('format_score', 0),
                                        scores.get('readability_score', 0)
                                    ]
                                })
                                    
                                # Display as bar chart
                                st.bar_chart(scores_df.set_index('Category'))
                                    
                                # Quick Summary
                                total_score = scores.get('total_score', 0)
                                if total_score >= 85:
                                    st.success("Your resume is well-optimized for ATS systems.")
                                elif total_score >= 70:
                                    st.warning("Your resume meets basic ATS requirements but has room for improvement.")
                                else:
                                    st.error("Your resume may need optimization for better ATS performance.")
                                
                            else:
                                st.warning("No ATS analysis data available. Please ensure your resume has been properly analyzed.")
                                
                            st.markdown(ats_analysis['ats_analysis'])
                        
                        with tab5:
                            st.subheader("Executive Summary Report")
                            
                            if 'scores' in st.session_state.parsed_resume:
                                total_score = st.session_state.parsed_resume['scores'].get('total_score', 0)
                                
                                # Overall Assessment
                                st.markdown("### Overall Assessment")
                                st.markdown("""
                                Your resume has been analyzed across multiple dimensions including content quality, 
                                ATS compatibility, skills presentation, and overall professional impact. Here's a 
                                comprehensive summary of the findings:
                                """)
                                
                                # Core Metrics Summary
                                st.markdown("#### Key Performance Metrics")
                                st.markdown(f"""Your resume achieved an overall score of **{total_score}%** with the following key observations:

• **Content Strength**: {st.session_state.parsed_resume['scores'].get('content_score', 0)}%
- Measures the quality and relevance of your professional experience
- Evaluates the impact and clarity of your achievements

• **ATS Compatibility**: {st.session_state.parsed_resume['scores'].get('keyword_score', 0)}%
- Assesses how well your resume aligns with ATS systems
- Evaluates keyword optimization and format compliance

• **Skills Presentation**: {st.session_state.parsed_resume['scores'].get('skills_score', 0)}%
- Analyzes the breadth and depth of your technical capabilities
- Evaluates how effectively skills are contextualized
""")

                                # Profile Analysis Summary
                                st.markdown("#### Professional Profile Analysis")
                                st.markdown("""Your professional profile demonstrates the following characteristics:

• **Experience Presentation**
- Career progression and achievements are effectively structured
- Professional impact is quantified where applicable
- Key responsibilities align with industry expectations

• **Technical Expertise**
- Demonstrates proficiency in relevant technical domains
- Shows adaptability across different technologies
- Highlights practical application of skills

• **Professional Development**
- Shows continuous learning and skill advancement
- Indicates ability to adapt to industry changes
- Demonstrates professional growth trajectory
""")

                                # Skills Distribution
                                if 'skills_data' in locals():
                                    st.markdown("#### Skills Distribution")
                                    st.markdown("""
                                    Your skill set demonstrates the following distribution:
                                    
                                    • **Technical Competencies**
                                    - Programming Languages: Core and supplementary technologies
                                    - Frameworks & Tools: Industry-standard development tools
                                    - Technical Methodologies: Development and deployment practices
                                    
                                    • **Professional Capabilities**
                                    - Project Management: Planning and execution abilities
                                    - Team Collaboration: Communication and leadership skills
                                    - Problem Solving: Analytical and strategic thinking
                                    """)
                                
                                # Overall Impact
                                st.markdown("#### Overall Professional Impact")
                                if total_score >= 85:
                                    impact_assessment = """
                                    Your resume presents a **strong professional profile** with:
                                    
                                    • **Exceptional Qualities**
                                    - Well-optimized for ATS systems
                                    - Clear demonstration of professional expertise
                                    - Strong alignment with industry standards
                                    - Effective communication of achievements
                                    """
                                elif total_score >= 70:
                                    impact_assessment = """
                                    Your resume presents a **solid professional profile** with:
                                    
                                    • **Notable Strengths**
                                    - Good foundation for ATS compatibility
                                    - Clear presentation of professional experience
                                    - Adequate skill demonstration
                                    - Defined career progression
                                    """
                                else:
                                    impact_assessment = """
                                    Your resume presents a **developing professional profile** with:
                                    
                                    • **Core Elements**
                                    - Basic professional presentation
                                    - Fundamental skill documentation
                                    - Career experience outline
                                    - Development opportunities identified
                                    """
                                
                                st.markdown(impact_assessment)
                                
                                # Market Readiness
                                st.markdown("#### Market Readiness Assessment")
                                st.markdown(f"""
                                Based on the comprehensive analysis, your resume demonstrates:
                                
                                • **Overall Market Position**
                                - {'Strong' if total_score >= 85 else 'Moderate' if total_score >= 70 else 'Basic'} competitive standing
                                - {'Excellent' if total_score >= 85 else 'Good' if total_score >= 70 else 'Fair'} industry alignment
                                - {'High' if total_score >= 85 else 'Moderate' if total_score >= 70 else 'Basic'} professional impact
                                
                                • **Technical Readiness**
                                - {'Advanced' if st.session_state.parsed_resume['scores'].get('skills_score', 0) >= 85 else 'Intermediate' if st.session_state.parsed_resume['scores'].get('skills_score', 0) >= 70 else 'Basic'} technical proficiency
                                - {'Strong' if st.session_state.parsed_resume['scores'].get('content_score', 0) >= 85 else 'Good' if st.session_state.parsed_resume['scores'].get('content_score', 0) >= 70 else 'Basic'} experience documentation
                                - {'Excellent' if st.session_state.parsed_resume['scores'].get('keyword_score', 0) >= 85 else 'Good' if st.session_state.parsed_resume['scores'].get('keyword_score', 0) >= 70 else 'Basic'} keyword optimization
                                """)
                                
                            else:
                                st.warning("No analysis data available. Please ensure your resume has been properly analyzed.")

                        with tab6:
                            st.subheader("Interactive Resume Analysis Visualization")
                            if not 'scores' in st.session_state.parsed_resume:
                                st.warning("No analysis data available for visualization. Please ensure your resume has been properly analyzed.")
                                return
                            
                            scores = st.session_state.parsed_resume['scores']
                            
                            # Create two columns for the visualizations
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Radar Chart for Overall Scores
                                categories = ['Content', 'Skills', 'Keywords', 'Format', 'Readability']
                                values = [
                                    scores.get('content_score', 0),
                                    scores.get('skills_score', 0),
                                    scores.get('keyword_score', 0),
                                    scores.get('format_score', 0),
                                    scores.get('readability_score', 0)
                                ]
                                
                                fig_radar = go.Figure()
                                fig_radar.add_trace(go.Scatterpolar(
                                    r=values,
                                    theta=categories,
                                    fill='toself',
                                    name='Your Resume'
                                ))
                                
                                fig_radar.update_layout(
                                    polar=dict(
                                        radialaxis=dict(
                                            visible=True,
                                            range=[0, 100]
                                        )),
                                    showlegend=False,
                                    title="Resume Score Distribution"
                                )
                                
                                st.plotly_chart(fig_radar, use_container_width=True)
                            
                            with col2:
                                # Gauge chart for Overall ATS Score
                                total_score = scores.get('total_score', 0)
                                
                                fig_gauge = go.Figure(go.Indicator(
                                    mode = "gauge+number",
                                    value = total_score,
                                    domain = {'x': [0, 1], 'y': [0, 1]},
                                    gauge = {
                                        'axis': {'range': [0, 100]},
                                        'bar': {'color': "darkblue"},
                                        'steps': [
                                            {'range': [0, 50], 'color': "lightgray"},
                                            {'range': [50, 70], 'color': "gray"},
                                            {'range': [70, 85], 'color': "lightblue"},
                                            {'range': [85, 100], 'color': "royalblue"}
                                        ],
                                        'threshold': {
                                            'line': {'color': "red", 'width': 4},
                                            'thickness': 0.75,
                                            'value': 85
                                        }
                                    },
                                    title = {'text': "Overall ATS Score"}
                                ))
                                
                                st.plotly_chart(fig_gauge, use_container_width=True)
                            
                            # Skills Distribution Chart
                            if 'skills_data' in locals():
                                # Prepare skills data
                                skills_categories = list(skills_data.keys())
                                skills_counts = [len(skills) for skills in skills_data.values()]
                                
                                # Create a donut chart
                                fig_skills = go.Figure(data=[go.Pie(
                                    labels=skills_categories,
                                    values=skills_counts,
                                    hole=.3,
                                    textinfo='label+percent'
                                )])
                                
                                fig_skills.update_layout(
                                    title="Skills Distribution",
                                    annotations=[dict(text='Skills', x=0.5, y=0.5, font_size=20, showarrow=False)]
                                )
                                
                                st.plotly_chart(fig_skills, use_container_width=True)
                            
                            # Score Trends Bar Chart
                            score_data = pd.DataFrame({
                                'Category': ['Content Quality', 'Skills Coverage', 'Keyword Match', 'Format Score', 'Readability'],
                                'Score': [
                                    scores.get('content_score', 0),
                                    scores.get('skills_score', 0),
                                    scores.get('keyword_score', 0),
                                    scores.get('format_score', 0),
                                    scores.get('readability_score', 0)
                                ],
                                'Target': [90, 85, 80, 90, 85]
                            })
                            
                            fig_bars = go.Figure()
                            fig_bars.add_trace(go.Bar(
                                name='Your Score',
                                x=score_data['Category'],
                                y=score_data['Score'],
                                marker_color='royalblue'
                            ))
                            fig_bars.add_trace(go.Bar(
                                name='Target Score',
                                x=score_data['Category'],
                                y=score_data['Target'],
                                marker_color='lightgray'
                            ))
                            
                            fig_bars.update_layout(
                                title="Score Comparison with Targets",
                                barmode='group',
                                yaxis_title="Score (%)",
                                xaxis_title="Categories"
                            )
                            
                            st.plotly_chart(fig_bars, use_container_width=True)
                            
                            # Interactive Metrics Explorer
                            st.subheader("Interactive Metrics Explorer")
                            
                            # Create selection for metrics
                            selected_metrics = st.multiselect(
                                "Select metrics to compare",
                                ['Content Score', 'Skills Score', 'Keyword Score', 'Format Score', 'Readability Score'],
                                default=['Content Score', 'Skills Score']
                            )
                            
                            if selected_metrics:
                                # Prepare data for selected metrics
                                metric_values = {
                                    'Content Score': scores.get('content_score', 0),
                                    'Skills Score': scores.get('skills_score', 0),
                                    'Keyword Score': scores.get('keyword_score', 0),
                                    'Format Score': scores.get('format_score', 0),
                                    'Readability Score': scores.get('readability_score', 0)
                                }
                                
                                selected_data = {
                                    metric: metric_values[metric]
                                    for metric in selected_metrics
                                }
                                
                                # Create comparison chart
                                fig_compare = go.Figure()
                                for metric, value in selected_data.items():
                                    fig_compare.add_trace(go.Bar(
                                        name=metric,
                                        x=[metric],
                                        y=[value],
                                        text=[f"{value}%"],
                                        textposition='auto',
                                    ))
                                
                                fig_compare.update_layout(
                                    title="Metrics Comparison",
                                    yaxis_title="Score (%)",
                                    yaxis_range=[0, 100],
                                    showlegend=False
                                )
                                
                                st.plotly_chart(fig_compare, use_container_width=True)
                    else:
                        st.error("Could not parse the resume. Please check the file format and try again.")
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
                            
                            # Create tabs for different analysis sections
                            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                                "ATS Score", 
                                "Profile Analysis",
                                "Skills Analysis",
                                "Optimization",
                                "Summary Report",
                                "Visualization"
                            ])
                            
                            with tab1:
                                st.subheader("ATS Compatibility Score")
                                
                                # Display scores in columns with improved styling
                                col1, col2, col3 = st.columns(3)
                                
                                # Calculate total score percentage
                                total_score = st.session_state.parsed_resume['scores']['total_score']
                                
                                with col1:
                                    st.metric("Overall ATS Score", f"{total_score}%")
                                
                                with col2:
                                    st.metric("Keyword Match", f"{st.session_state.parsed_resume['scores']['keyword_score']}%")
                                
                                with col3:
                                    st.metric("Format Score", f"{st.session_state.parsed_resume['scores']['format_score']}%")
                                
                                # Display score breakdown with improved visualization
                                st.subheader("Detailed Score Breakdown")
                                scores_df = pd.DataFrame({
                                    'Category': [
                                        'Content Quality',
                                        'Skills Coverage',
                                        'Keyword Optimization',
                                        'Format & Structure',
                                        'Readability'
                                    ],
                                    'Score': [
                                        st.session_state.parsed_resume['scores']['content_score'],
                                        st.session_state.parsed_resume['scores']['skills_score'],
                                        st.session_state.parsed_resume['scores']['keyword_score'],
                                        st.session_state.parsed_resume['scores']['format_score'],
                                        st.session_state.parsed_resume['scores']['readability_score']
                                    ]
                                })
                                
                                # Display as bar chart
                                st.bar_chart(scores_df.set_index('Category'))
                            
                            with tab2:
                                st.subheader("Profile Analysis")
                                st.markdown(analysis['profile_analysis'])
                            
                            with tab3:
                                st.subheader("Skills Analysis")
                                try:
                                    # Get skills data based on the source (uploaded or generated)
                                    skills_data = {}
                                    
                                    if 'parsed_resume' in st.session_state and st.session_state.parsed_resume:
                                        # For uploaded resumes
                                        skills_data = {
                                            'programming_languages': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('programming_languages', []),
                                            'frameworks_libraries': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('frameworks_libraries', []),
                                            'soft_skills': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('soft_skills', []),
                                            'tools_technologies': st.session_state.parsed_resume.get('scores', {}).get('detected_skills', {}).get('tools_technologies', [])
                                        }
                                    elif 'resume_data' in st.session_state and st.session_state.resume_data:
                                        # For generated resumes
                                        skills = st.session_state.resume_data.get('skills', {})
                                        skills_data = {
                                            'programming_languages': skills.get('programming', []),
                                            'frameworks_libraries': skills.get('frameworks', []),
                                            'soft_skills': skills.get('soft_skills', []),
                                            'tools_technologies': skills.get('tools', [])
                                        }
                                        
                                        # Clean up empty strings from lists
                                        for category in skills_data:
                                            skills_data[category] = [skill.strip() for skill in skills_data[category] if skill.strip()]

                                    if not any(skills_data.values()):
                                        st.warning("No skills data available. Please ensure your resume includes skills information.")
                                        return

                                    # Technical Skills Analysis
                                    st.markdown("### Technical Skills Analysis")
                                    
                                    # Programming Languages
                                    if skills_data.get('programming_languages'):
                                        st.markdown("""
                                        #### Programming Languages
                                        Your resume demonstrates proficiency in multiple programming languages. Here's a detailed analysis:
                                        """)
                                        
                                        langs = sorted(skills_data['programming_languages'])
                                        st.markdown("**Core Languages:**")
                                        st.markdown("\n".join([f"• `{lang}` - Demonstrated through projects and experience" 
                                                            for lang in langs[:3]]))
                                        
                                        if len(langs) > 3:
                                            st.markdown("\n**Additional Languages:**")
                                            st.markdown("\n".join([f"• `{lang}`" for lang in langs[3:]]))
                                        
                                        st.markdown("""
                                        **Analysis:**
                                        Your programming language portfolio shows a good mix of modern and established technologies.
                                        Consider focusing on deepening expertise in your core languages while maintaining working
                                        knowledge of others.
                                        """)

                                    # Frameworks and Libraries
                                    if skills_data.get('frameworks_libraries'):
                                        st.markdown("""
                                        #### Frameworks & Libraries
                                        Your technical stack includes various frameworks and libraries:
                                        """)
                                        
                                        frameworks = sorted(skills_data['frameworks_libraries'])
                                        for fw in frameworks:
                                            st.markdown(f"• `{fw}`")
                                        
                                        st.markdown("""
                                        **Framework Proficiency:**
                                        Your experience with these frameworks indicates a solid foundation in software development.
                                        This diverse knowledge base allows you to adapt to different project requirements and
                                        technical environments.
                                        """)

                                    # Professional Skills Analysis
                                    st.markdown("### Professional Skills Analysis")
                                    
                                    if skills_data.get('soft_skills'):
                                        st.markdown("""
                                        #### Soft Skills & Professional Competencies
                                        Your resume demonstrates the following professional capabilities:
                                        """)
                                        
                                        soft_skills = sorted(skills_data['soft_skills'])
                                        for skill in soft_skills:
                                            st.markdown(f"• {skill}")
                                        
                                        st.markdown("""
                                        **Professional Impact:**
                                        Your soft skills complement your technical abilities, showing a well-rounded
                                        professional profile. These skills are particularly valuable for:
                                        • Team collaboration and leadership roles
                                        • Project management and coordination
                                        • Client interaction and communication
                                        """)

                                    # Tools and Technologies
                                    if skills_data.get('tools_technologies'):
                                        st.markdown("""
                                        #### Tools & Technologies
                                        Your proficiency extends to various development tools and technologies:
                                        """)
                                        
                                        tools = sorted(skills_data['tools_technologies'])
                                        for tool in tools:
                                            st.markdown(f"• `{tool}`")
                                        
                                        st.markdown("""
                                        **Technical Environment:**
                                        Your experience with these tools indicates familiarity with modern development
                                        practices and environments. This toolkit supports efficient development workflows
                                        and collaborative work.
                                        """)

                                    # Overall Skills Assessment
                                    st.markdown("### Overall Skills Assessment")
                                    
                                    # Calculate total skills and distributions
                                    total_skills = sum(len(skills) for skills in skills_data.values())
                                    
                                    st.markdown(f"""
                                    #### Comprehensive Analysis
                                    
                                    Your skill profile includes {total_skills} distinct competencies across various categories.
                                    The distribution shows:
                                    """)
                                    
                                    for category, skills in skills_data.items():
                                        if skills:
                                            percentage = (len(skills) / total_skills) * 100
                                            st.markdown(f"• **{category.replace('_', ' ').title()}**: {len(skills)} skills ({percentage:.1f}%)")
                                    
                                    st.markdown("""
                                    #### Key Observations
                                    
                                    1. **Technical Depth**
                                       - Your technical skills show both breadth and depth
                                       - Good balance between fundamental and specialized technologies
                                       - Evidence of continuous learning and adaptation
                                    
                                    2. **Professional Development**
                                       - Strong foundation in core development practices
                                       - Demonstrated ability to work with modern tools
                                       - Clear progression in skill acquisition
                                    
                                    3. **Areas of Excellence**
                                       - Solid programming language foundation
                                       - Practical experience with industry-standard tools
                                       - Balance of technical and soft skills
                                    """)

                                    # Recommendations
                                    st.markdown("""
                                    ### Recommendations for Growth
                                    
                                    Based on your current skill set, consider:
                                    
                                    1. **Skill Enhancement**
                                       - Deepen expertise in your primary programming languages
                                       - Stay updated with the latest versions and features
                                       - Practice through complex projects
                                    
                                    2. **Knowledge Expansion**
                                       - Explore complementary technologies
                                       - Focus on high-demand areas in your field
                                       - Maintain awareness of industry trends
                                    
                                    3. **Professional Development**
                                       - Seek opportunities to lead technical initiatives
                                       - Share knowledge through mentoring or documentation
                                       - Contribute to open-source projects
                                    """)

                                except Exception as e:
                                    st.error(f"An error occurred in skills analysis: {str(e)}")
                                    st.info("Please ensure your resume includes skills information and try again.")
                            
                            with tab4:
                                st.subheader("ATS Analysis")
                                
                                if 'scores' in st.session_state.parsed_resume:
                                    scores = st.session_state.parsed_resume['scores']
                                    
                                    # Core ATS Analysis
                                    st.markdown("### ATS Score Overview")
                                    
                                    # Display scores in a clean layout
                                    col1, col2, col3 = st.columns(3)
                                    
                                    with col1:
                                        st.metric(
                                            "Overall ATS Score",
                                            f"{scores.get('total_score', 0)}%",
                                            delta="Target: 85%+" if scores.get('total_score', 0) < 85 else None,
                                            delta_color="inverse"
                                        )
                                        
                                    with col2:
                                        st.metric(
                                            "Keyword Match",
                                            f"{scores.get('keyword_score', 0)}%",
                                            delta="Target: 80%+" if scores.get('keyword_score', 0) < 80 else None,
                                            delta_color="inverse"
                                        )
                                        
                                    with col3:
                                        st.metric(
                                            "Format Score",
                                            f"{scores.get('format_score', 0)}%",
                                            delta="Target: 90%+" if scores.get('format_score', 0) < 90 else None,
                                            delta_color="inverse"
                                        )
                                        
                                    # Score Breakdown
                                    st.markdown("### Score Breakdown")
                                    scores_df = pd.DataFrame({
                                        'Category': [
                                            'Content Quality',
                                            'Skills Coverage',
                                            'Keyword Optimization',
                                            'Format & Structure',
                                            'Readability'
                                        ],
                                        'Score': [
                                            scores.get('content_score', 0),
                                            scores.get('skills_score', 0),
                                            scores.get('keyword_score', 0),
                                            scores.get('format_score', 0),
                                            scores.get('readability_score', 0)
                                        ]
                                    })
                                    
                                    # Display as bar chart
                                    st.bar_chart(scores_df.set_index('Category'))
                                    
                                    # Quick Summary
                                    total_score = scores.get('total_score', 0)
                                    if total_score >= 85:
                                        st.success("Your resume is well-optimized for ATS systems.")
                                    elif total_score >= 70:
                                        st.warning("Your resume meets basic ATS requirements but has room for improvement.")
                                    else:
                                        st.error("Your resume may need optimization for better ATS performance.")
                                    
                                else:
                                    st.warning("No ATS analysis data available. Please ensure your resume has been properly analyzed.")
                                
                                st.markdown(ats_analysis['ats_analysis'])
                            
                            with tab5:
                                st.subheader("Executive Summary Report")
                                
                                if 'scores' in st.session_state.parsed_resume:
                                    total_score = st.session_state.parsed_resume['scores'].get('total_score', 0)
                                    
                                    # Overall Assessment
                                    st.markdown("### Overall Assessment")
                                    st.markdown("""
                                    Your resume has been analyzed across multiple dimensions including content quality, 
                                    ATS compatibility, skills presentation, and overall professional impact. Here's a 
                                    comprehensive summary of the findings:
                                    """)
                                    
                                    # Core Metrics Summary
                                    st.markdown("#### Key Performance Metrics")
                                    st.markdown(f"""Your resume achieved an overall score of **{total_score}%** with the following key observations:

• **Content Strength**: {st.session_state.parsed_resume['scores'].get('content_score', 0)}%
- Measures the quality and relevance of your professional experience
- Evaluates the impact and clarity of your achievements

• **ATS Compatibility**: {st.session_state.parsed_resume['scores'].get('keyword_score', 0)}%
- Assesses how well your resume aligns with ATS systems
- Evaluates keyword optimization and format compliance

• **Skills Presentation**: {st.session_state.parsed_resume['scores'].get('skills_score', 0)}%
- Analyzes the breadth and depth of your technical capabilities
- Evaluates how effectively skills are contextualized
""")

                                    # Profile Analysis Summary
                                    st.markdown("#### Professional Profile Analysis")
                                    st.markdown("""Your professional profile demonstrates the following characteristics:

• **Experience Presentation**
- Career progression and achievements are effectively structured
- Professional impact is quantified where applicable
- Key responsibilities align with industry expectations

• **Technical Expertise**
- Demonstrates proficiency in relevant technical domains
- Shows adaptability across different technologies
- Highlights practical application of skills

• **Professional Development**
- Shows continuous learning and skill advancement
- Indicates ability to adapt to industry changes
- Demonstrates professional growth trajectory
""")

                                    # Skills Distribution
                                    if 'skills_data' in locals():
                                        st.markdown("#### Skills Distribution")
                                        st.markdown("""
                                        Your skill set demonstrates the following distribution:
                                        
                                        • **Technical Competencies**
                                        - Programming Languages: Core and supplementary technologies
                                        - Frameworks & Tools: Industry-standard development tools
                                        - Technical Methodologies: Development and deployment practices
                                        
                                        • **Professional Capabilities**
                                        - Project Management: Planning and execution abilities
                                        - Team Collaboration: Communication and leadership skills
                                        - Problem Solving: Analytical and strategic thinking
                                        """)
                                    
                                    # Overall Impact
                                    st.markdown("#### Overall Professional Impact")
                                    if total_score >= 85:
                                        impact_assessment = """
                                        Your resume presents a **strong professional profile** with:
                                        
                                        • **Exceptional Qualities**
                                        - Well-optimized for ATS systems
                                        - Clear demonstration of professional expertise
                                        - Strong alignment with industry standards
                                        - Effective communication of achievements
                                        """
                                    elif total_score >= 70:
                                        impact_assessment = """
                                        Your resume presents a **solid professional profile** with:
                                        
                                        • **Notable Strengths**
                                        - Good foundation for ATS compatibility
                                        - Clear presentation of professional experience
                                        - Adequate skill demonstration
                                        - Defined career progression
                                        """
                                    else:
                                        impact_assessment = """
                                        Your resume presents a **developing professional profile** with:
                                        
                                        • **Core Elements**
                                        - Basic professional presentation
                                        - Fundamental skill documentation
                                        - Career experience outline
                                        - Development opportunities identified
                                        """
                                    
                                    st.markdown(impact_assessment)
                                    
                                    # Market Readiness
                                    st.markdown("#### Market Readiness Assessment")
                                    st.markdown(f"""
                                    Based on the comprehensive analysis, your resume demonstrates:
                                    
                                    • **Overall Market Position**
                                    - {'Strong' if total_score >= 85 else 'Moderate' if total_score >= 70 else 'Basic'} competitive standing
                                    - {'Excellent' if total_score >= 85 else 'Good' if total_score >= 70 else 'Fair'} industry alignment
                                    - {'High' if total_score >= 85 else 'Moderate' if total_score >= 70 else 'Basic'} professional impact
                                    
                                    • **Technical Readiness**
                                    - {'Advanced' if st.session_state.parsed_resume['scores'].get('skills_score', 0) >= 85 else 'Intermediate' if st.session_state.parsed_resume['scores'].get('skills_score', 0) >= 70 else 'Basic'} technical proficiency
                                    - {'Strong' if st.session_state.parsed_resume['scores'].get('content_score', 0) >= 85 else 'Good' if st.session_state.parsed_resume['scores'].get('content_score', 0) >= 70 else 'Basic'} experience documentation
                                    - {'Excellent' if st.session_state.parsed_resume['scores'].get('keyword_score', 0) >= 85 else 'Good' if st.session_state.parsed_resume['scores'].get('keyword_score', 0) >= 70 else 'Basic'} keyword optimization
                                    """)
                                    
                                else:
                                    st.warning("No analysis data available. Please ensure your resume has been properly analyzed.")

                            with tab6:
                                st.subheader("Interactive Resume Analysis Visualization")
                                if not 'scores' in st.session_state.parsed_resume:
                                    st.warning("No analysis data available for visualization. Please ensure your resume has been properly analyzed.")
                                    return
                                
                                scores = st.session_state.parsed_resume['scores']
                                
                                # Create two columns for the visualizations
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Radar Chart for Overall Scores
                                    categories = ['Content', 'Skills', 'Keywords', 'Format', 'Readability']
                                    values = [
                                        scores.get('content_score', 0),
                                        scores.get('skills_score', 0),
                                        scores.get('keyword_score', 0),
                                        scores.get('format_score', 0),
                                        scores.get('readability_score', 0)
                                    ]
                                    
                                    fig_radar = go.Figure()
                                    fig_radar.add_trace(go.Scatterpolar(
                                        r=values,
                                        theta=categories,
                                        fill='toself',
                                        name='Your Resume'
                                    ))
                                    
                                    fig_radar.update_layout(
                                        polar=dict(
                                            radialaxis=dict(
                                                visible=True,
                                                range=[0, 100]
                                            )),
                                            showlegend=False,
                                            title="Resume Score Distribution"
                                        )
                                    
                                    st.plotly_chart(fig_radar, use_container_width=True)
                                
                                with col2:
                                    # Gauge chart for Overall ATS Score
                                    total_score = scores.get('total_score', 0)
                                    
                                    fig_gauge = go.Figure(go.Indicator(
                                        mode = "gauge+number",
                                        value = total_score,
                                        domain = {'x': [0, 1], 'y': [0, 1]},
                                        gauge = {
                                            'axis': {'range': [0, 100]},
                                            'bar': {'color': "darkblue"},
                                            'steps': [
                                                {'range': [0, 50], 'color': "lightgray"},
                                                {'range': [50, 70], 'color': "gray"},
                                                {'range': [70, 85], 'color': "lightblue"},
                                                {'range': [85, 100], 'color': "royalblue"}
                                            ],
                                            'threshold': {
                                                'line': {'color': "red", 'width': 4},
                                                'thickness': 0.75,
                                                'value': 85
                                            }
                                        },
                                        title = {'text': "Overall ATS Score"}
                                    ))
                                    
                                    st.plotly_chart(fig_gauge, use_container_width=True)
                                
                                # Skills Distribution Chart
                                if 'skills_data' in locals():
                                    # Prepare skills data
                                    skills_categories = list(skills_data.keys())
                                    skills_counts = [len(skills) for skills in skills_data.values()]
                                    
                                    # Create a donut chart
                                    fig_skills = go.Figure(data=[go.Pie(
                                        labels=skills_categories,
                                        values=skills_counts,
                                        hole=.3,
                                        textinfo='label+percent'
                                    )])
                                    
                                    fig_skills.update_layout(
                                        title="Skills Distribution",
                                        annotations=[dict(text='Skills', x=0.5, y=0.5, font_size=20, showarrow=False)]
                                    )
                                    
                                    st.plotly_chart(fig_skills, use_container_width=True)
                                
                                # Score Trends Bar Chart
                                score_data = pd.DataFrame({
                                    'Category': ['Content Quality', 'Skills Coverage', 'Keyword Match', 'Format Score', 'Readability'],
                                    'Score': [
                                        scores.get('content_score', 0),
                                        scores.get('skills_score', 0),
                                        scores.get('keyword_score', 0),
                                        scores.get('format_score', 0),
                                        scores.get('readability_score', 0)
                                    ],
                                    'Target': [90, 85, 80, 90, 85]
                                })
                                
                                fig_bars = go.Figure()
                                fig_bars.add_trace(go.Bar(
                                    name='Your Score',
                                    x=score_data['Category'],
                                    y=score_data['Score'],
                                    marker_color='royalblue'
                                ))
                                fig_bars.add_trace(go.Bar(
                                    name='Target Score',
                                    x=score_data['Category'],
                                    y=score_data['Target'],
                                    marker_color='lightgray'
                                ))
                                
                                fig_bars.update_layout(
                                    title="Score Comparison with Targets",
                                    barmode='group',
                                    yaxis_title="Score (%)",
                                    xaxis_title="Categories"
                                )
                                
                                st.plotly_chart(fig_bars, use_container_width=True)
                                
                                # Interactive Metrics Explorer
                                st.subheader("Interactive Metrics Explorer")
                                
                                # Create selection for metrics
                                selected_metrics = st.multiselect(
                                    "Select metrics to compare",
                                    ['Content Score', 'Skills Score', 'Keyword Score', 'Format Score', 'Readability Score'],
                                    default=['Content Score', 'Skills Score']
                                )
                                
                                if selected_metrics:
                                    # Prepare data for selected metrics
                                    metric_values = {
                                        'Content Score': scores.get('content_score', 0),
                                        'Skills Score': scores.get('skills_score', 0),
                                        'Keyword Score': scores.get('keyword_score', 0),
                                        'Format Score': scores.get('format_score', 0),
                                        'Readability Score': scores.get('readability_score', 0)
                                    }
                                    
                                    selected_data = {
                                        metric: metric_values[metric]
                                        for metric in selected_metrics
                                    }
                                    
                                    # Create comparison chart
                                    fig_compare = go.Figure()
                                    for metric, value in selected_data.items():
                                        fig_compare.add_trace(go.Bar(
                                            name=metric,
                                            x=[metric],
                                            y=[value],
                                            text=[f"{value}%"],
                                            textposition='auto',
                                        ))
                                    
                                    fig_compare.update_layout(
                                        title="Metrics Comparison",
                                        yaxis_title="Score (%)",
                                        yaxis_range=[0, 100],
                                        showlegend=False
                                    )
                                    
                                    st.plotly_chart(fig_compare, use_container_width=True)
                    
                    except Exception as e:
                        st.error(f"An error occurred during AI analysis: {str(e)}")
                        st.info("Please check your API key or try again later.")
                
        except Exception as e:
            st.error(f"An error occurred while generating your resume: {str(e)}")
            st.info("Please try again or contact support if the issue persists.")

if __name__ == "__main__":
    main()