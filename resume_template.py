def generate_resume(data):
    """Generate HTML resume based on the template structure"""
    
    # Extract data
    personal = data["personal_info"]
    education = data["education"]
    profile = data["profile_summary"]
    skills = data["skills"]
    projects = data["projects"]
    achievements = data.get("achievements", [])
    
    # Helper for bolding keywords in bullets
    def bold_keywords(text, keywords):
        for kw in keywords:
            text = text.replace(kw, f'<strong>{kw}</strong>')
        return text
    
    # Helper to format responsibilities into bullet points
    def format_responsibilities(responsibilities_text):
        # Handle both string and list inputs
        if isinstance(responsibilities_text, list):
            responsibilities = responsibilities_text
        else:
            # Split the text by newlines and remove empty lines
            responsibilities = [r.strip() for r in responsibilities_text.split('\n') if r.strip()]
        
        # Format each responsibility as a bullet point
        formatted_bullets = []
        for resp in responsibilities:
            # Remove leading dash or bullet if present
            if isinstance(resp, str):  # Handle string items
                resp = resp.lstrip('•- ').strip()
                if resp:  # Only add non-empty responsibilities
                    formatted_bullets.append(f"<li>{resp}</li>")
            elif resp:  # Handle non-string items that are truthy
                formatted_bullets.append(f"<li>{str(resp)}</li>")
        return '\n'.join(formatted_bullets)
    
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>{personal.get('name', '')} - Resume</title>
        <style>
            body {{
                font-family: 'Calibri (Headings)', 'Calibri Light', Arial, sans-serif;
                color: #000;
                font-size: 13pt;
                margin: 0;
                padding: 0 30px;
                overflow-x: hidden;
            }}
            @page {{
                size: A4;
                margin: 20mm 25mm;
            }}
            .section {{
                page-break-inside: avoid;
                margin-bottom: 8px;
            }}
            .project {{
                page-break-inside: avoid;
            }}
            .project-responsibilities {{
                page-break-inside: avoid;
                margin-left: 20px;
            }}
            .achievements {{
                page-break-inside: avoid;
            }}
            .skills-list {{
                page-break-inside: avoid;
            }}
            .header {{
                text-align: center;
                margin-top: 18px;
                margin-bottom: 8px;
            }}
            .name {{
                font-family: 'Calibri', Arial, sans-serif;
                font-size: 20pt;
                font-weight: bold;
                margin-bottom: 2px;
            }}
            .contact-info {{
                font-size: 11pt;
                margin-bottom: 10px;
            }}
            .contact-info a {{
                color: #0563c1;
                text-decoration: underline;
            }}
            .section-title {{
                font-family: 'Calibri', Arial, sans-serif;
                font-size: 14pt;
                font-weight: bold;
                text-transform: uppercase;
                color: #000;
                border-bottom: 1px solid #000;
                padding-bottom: 0;
                margin-bottom: 2px;
                margin-top: 15px;
                letter-spacing: 0.5px;
                text-align: left;
            }}
            /* First section (Education) shouldn't have the extra top margin */
            .section:first-of-type .section-title {{
                margin-top: 0;
            }}
            .edu-row {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                line-height: 1;
                margin: 0;
                padding: 0;
                margin-bottom: 3px;
            }}
            .edu-left {{
                font-family: 'Calibri (Headings)', 'Calibri Light', Arial, sans-serif;
                font-size: 13pt;
                margin: 0;
                padding: 0;
                display: inline-block;
                vertical-align: baseline;
            }}
            .edu-right {{
                font-family: 'Calibri (Headings)', 'Calibri Light', Arial, sans-serif;
                font-size: 13pt;
                text-align: right;
                margin: 0;
                padding: 0;
                white-space: nowrap;
                display: inline-block;
                vertical-align: baseline;
            }}
            .edu-left em {{
                font-style: italic;
            }}
            .edu-details {{
                font-size: 11pt;
                font-style: italic;
                margin-left: 0;
                margin-top: 2px;
            }}
            .cgpa {{
                font-family: 'Calibri (Headings)', 'Calibri Light', Arial, sans-serif;
                font-size: 13pt;
                font-style: italic;
                margin-top: 0;
            }}
            .project-row {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
            }}
            .project-title {{
                font-family: 'Calibri', Arial, sans-serif;
                font-weight: bold;
                font-size: 13pt;
            }}
            .project-duration {{
                font-size: 13pt;
                font-style: italic;
                text-align: right;
                margin-left: 10px;
                white-space: nowrap;
            }}
            .project-tools strong,
            .responsibilities-label {{
                font-family: 'Calibri', Arial, sans-serif;
                font-weight: bold;
                font-size: 13pt;
            }}
            .project-tools {{
                margin-bottom: 2px;
                font-size: 13pt;
            }}
            ul {{
                margin: 4px 0 8px 22px;
                padding: 0;
                list-style-type: disc;
            }}
            li {{
                font-size: 13pt;
                margin-bottom: 2px;
            }}
            .skills-list strong {{
                font-family: 'Calibri', Arial, sans-serif;
                font-weight: bold;
            }}
            .achievements ul {{
                margin: 4px 0 0 22px;
            }}
            .profile-bullets ul {{
                margin: 4px 0 0 40px;
                padding: 0;
                list-style-type: disc;
            }}
            .profile-bullets li {{
                font-size: 13pt;
                margin-bottom: 4px;
                padding-left: 10px;
                text-indent: -5px;
            }}
            .project-responsibilities ul {{
                margin: 4px 0 8px 22px;
                padding: 0;
                list-style-type: disc;
            }}
            .project-responsibilities li {{
                font-size: 13pt;
                margin-bottom: 4px;
                padding-left: 10px;
            }}
        </style>
    </head>
    <body>
        <div class='header'>
            <div class='name'>{personal.get('name', '')}</div>
            <div class='contact-info'>
                <a href='mailto:{personal.get('email', '')}'>{personal.get('email', '')}</a> |
                {personal.get('phone', '')} |
                LinkedIn: {personal.get('linkedin', '')} |
                GitHub: {personal.get('github', '')}
            </div>
        </div>
        <div class='section'>
            <div class='section-title'>EDUCATION</div>
            <div style="line-height: 1.2; margin: 0; padding: 0;">
                <div class='edu-row'>
                    <div class='edu-left'><strong>{education.get('university', '')}</strong></div>
                </div>
                <div class='edu-row'>
                    <div class='edu-left'><strong>{education.get('degree', '')}</strong></div>
                </div>
                <div class='edu-row' style="margin-bottom: 0;">
                    <div class='edu-left'><strong>CGPA:</strong> {education.get('gpa', '')} | <strong>{personal.get('location', '')}</strong> | <strong>Expected Graduation:</strong> {education.get('graduation_date', '').strftime('%B %Y') if education.get('graduation_date') else ''}</div>
                </div>
            </div>
        </div>
        <div class='section'>
            <div class='section-title'>PROFILE SUMMARY</div>
            <div class='profile-bullets'>
                <p>Targeting <strong>{profile.get('target_role', '')}</strong> roles with an organization of high repute with a scope of improving knowledge and further career growth.</p>
                <ul>
                    {format_responsibilities(profile.get('summary', ''))}
                </ul>
            </div>
        </div>
        <div class='section'>
            <div class='section-title'>PROJECTS</div>
    """
    
    # Add projects dynamically
    for project in projects:
        # Make each tool bold
        tools_list = [f"<strong>{tool.strip()}</strong>" for tool in project.get('tools', '').split(',') if tool.strip()]
        tools_text = ', '.join(tools_list)
        
        html += f"""
            <div class='project'>
                <div class='project-row'>
                    <div class='project-title'>• {project.get('title', '')} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>{project.get('duration', '')}</strong></div>
                </div>
                <div class='project-tools'><strong>Tools:</strong> {tools_text}</div>
                <div>{project.get('description', '')}</div>
                <div class='responsibilities-label'><strong>Responsibilities:</strong></div>
                <div class='project-responsibilities'>
                    <ul>
                        {format_responsibilities(project.get('responsibilities', ''))}
                    </ul>
                </div>
            </div>
        """
    
    # Add achievements
    html += """
        <div class='section'>
            <div class='section-title'>ACADEMIC ACHIEVEMENTS</div>
            <div class='achievements'>
                <ul>
    """
    
    for achievement in achievements:
        if achievement:  # Only add non-empty achievements
            html += f"<li>{achievement}</li>"
    
    html += """
                </ul>
            </div>
        </div>
    """
    
    # Add skills
    html += f"""
        <div class='section'>
            <div class='section-title'>SKILLS</div>
            <div class='skills-list'>
                <div><strong>Programming:</strong> {', '.join(skills.get('programming', []))}</div>
                <div><strong>Soft Skills:</strong> {', '.join(skills.get('soft_skills', []))}</div>
                <div><strong>Library / Frameworks:</strong> {', '.join(skills.get('frameworks', []))}</div>
                <div><strong>Other Skills:</strong> {', '.join(skills.get('other', []))}</div>
                <div><strong>Tools:</strong> {', '.join(skills.get('tools', []))}</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html