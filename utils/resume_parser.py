import PyPDF2
import docx
import streamlit as st
from typing import Dict, Any
import re
from pathlib import Path
import spacy
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
import pdfplumber  # Add pdfplumber for better PDF text extraction

class ResumeParser:
    def __init__(self):
        # Load spaCy model for NER and text processing
        try:
            self.nlp = spacy.load("en_core_web_lg")
        except OSError:
            st.info("Downloading language model for the first time...")
            from spacy.cli import download
            download("en_core_web_lg")
            self.nlp = spacy.load("en_core_web_lg")
        
        # Initialize common sections in resumes
        self.SECTIONS = [
            'education', 'experience', 'skills', 'projects',
            'certifications', 'summary', 'objective', 'work history',
            'professional experience', 'technical skills', 'achievements',
            'publications', 'languages', 'interests', 'volunteer'
        ]
        
        # Add role-related keywords
        self.ROLE_KEYWORDS = [
            'seeking', 'target', 'desired', 'role', 'position',
            'applying', 'job', 'opportunity', 'career'
        ]
        
        # Enhanced skills database with categories
        self.SKILLS_DB = {
            'programming_languages': {
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php',
                'swift', 'kotlin', 'go', 'rust', 'scala', 'perl', 'r', 'matlab', 'dart',
                'solidity', 'haskell', 'julia', 'lua', 'objective-c', 'assembly', 'cobol'
            },
            'frameworks_libraries': {
                'react', 'angular', 'vue.js', 'django', 'flask', 'spring', 'express',
                'node.js', 'next.js', 'nuxt.js', 'flutter', 'tensorflow', 'pytorch',
                'fastapi', 'laravel', 'svelte', 'nest.js', 'remix', 'gatsby', 'qwik',
                'scikit-learn', 'pandas', 'numpy', 'keras', 'transformers', 'jest',
                'cypress', 'playwright', 'selenium', 'puppeteer'
            },
            'databases': {
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
                'oracle', 'sql server', 'dynamodb', 'firebase', 'neo4j', 'cockroachdb',
                'supabase', 'planetscale', 'sqlite', 'mariadb', 'couchdb', 'graphql'
            },
            'cloud_devops': {
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'terraform',
                'ansible', 'circleci', 'github actions', 'gitlab ci', 'prometheus',
                'grafana', 'datadog', 'new relic', 'cloudflare', 'vercel', 'netlify',
                'heroku', 'digitalocean', 'vagrant', 'pulumi', 'helm'
            },
            'ai_ml': {
                'machine learning', 'deep learning', 'nlp', 'computer vision',
                'data science', 'neural networks', 'reinforcement learning',
                'statistical analysis', 'big data', 'data mining', 'gpt', 'llm',
                'chatbots', 'recommendation systems', 'anomaly detection', 'clustering',
                'classification', 'regression', 'time series analysis'
            },
            'web_mobile': {
                'html5', 'css3', 'sass', 'less', 'responsive design', 'pwa',
                'web components', 'webrtc', 'websockets', 'service workers',
                'web assembly', 'web3', 'blockchain', 'ios', 'android', 'react native',
                'xamarin', 'ionic', 'cordova', 'capacitor'
            },
            'tools_methodologies': {
                'git', 'jira', 'confluence', 'agile', 'scrum', 'kanban', 'tdd',
                'bdd', 'ci/cd', 'microservices', 'rest api', 'soap', 'graphql',
                'oauth', 'jwt', 'swagger', 'postman', 'figma', 'sketch', 'adobe xd'
            },
            'soft_skills': {
                'leadership', 'communication', 'problem solving', 'teamwork',
                'project management', 'time management', 'critical thinking',
                'adaptability', 'creativity', 'presentation', 'mentoring',
                'stakeholder management', 'conflict resolution'
            }
        }
        
        # Flatten skills for quick lookup
        self.ALL_SKILLS = {skill for category in self.SKILLS_DB.values() for skill in category}

    def extract_text_from_pdf(self, file) -> str:
        """Extract text from PDF file using multiple methods for better accuracy"""
        try:
            # Try pdfplumber first (better at maintaining formatting)
            with pdfplumber.open(file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                
                if text.strip():
                    return text

            # Fallback to PyPDF2 if pdfplumber fails
            file.seek(0)  # Reset file pointer
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def extract_text_from_docx(self, file) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            st.error(f"Error extracting text from DOCX: {str(e)}")
            return ""

    def extract_text(self, file) -> str:
        """Extract text based on file type"""
        file_extension = Path(file.name).suffix.lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file)
        elif file_extension in ['.docx', '.doc']:
            return self.extract_text_from_docx(file)
        else:
            st.error("Unsupported file format. Please upload PDF or DOCX files.")
            return ""

    def extract_target_role(self, text: str) -> str:
        """Extract target role from resume text"""
        # First try to find explicit mentions
        doc = self.nlp(text.lower())
        
        # Look for patterns like "Seeking [role]" or "Target role: [role]"
        for sent in doc.sents:
            sent_text = sent.text.lower()
            if any(keyword in sent_text for keyword in self.ROLE_KEYWORDS):
                # Try to extract the role after the keyword
                for keyword in self.ROLE_KEYWORDS:
                    if keyword in sent_text:
                        role_start = sent_text.find(keyword) + len(keyword)
                        role = sent_text[role_start:].strip('.: ')
                        if role:
                            return role.title()
        
        # Look in the objective or summary section
        sections = self.extract_sections(text)
        for section_name in ['objective', 'summary']:
            if section_name in sections:
                section_text = sections[section_name].lower()
                doc = self.nlp(section_text)
                
                # Look for job titles or role mentions
                for sent in doc.sents:
                    sent_text = sent.text.lower()
                    if any(keyword in sent_text for keyword in self.ROLE_KEYWORDS):
                        # Extract the part after the keyword
                        for keyword in self.ROLE_KEYWORDS:
                            if keyword in sent_text:
                                role_start = sent_text.find(keyword) + len(keyword)
                                role = sent_text[role_start:].strip('.: ')
                                if role:
                                    return role.title()
        
        return None

    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract different sections from the resume text"""
        sections = {}
        current_section = 'unknown'
        current_content = []
        
        # Split text into lines
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line is a section header
            line_lower = line.lower()
            if any(section in line_lower for section in self.SECTIONS):
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                    current_content = []
                current_section = line_lower
            else:
                current_content.append(line)
        
        # Add the last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
            
        # Try to extract degree information from education section
        if 'education' in sections:
            education_text = sections['education'].lower()
            # Common degree patterns
            degree_patterns = [
                r'(?:bachelor|master|phd|doctorate|b\.?s\.?|b\.?a\.?|m\.?s\.?|m\.?a\.?|ph\.?d\.?|b\.?tech|m\.?tech)',
                r'(?:bachelor\'s|master\'s)',
                r'(?:degree in|major in)'
            ]
            
            degree_info = None
            for pattern in degree_patterns:
                matches = re.finditer(pattern, education_text, re.IGNORECASE)
                for match in matches:
                    # Get the sentence containing the degree
                    start = max(0, education_text.rfind('.', 0, match.start()) + 1)
                    end = education_text.find('.', match.end())
                    if end == -1:
                        end = len(education_text)
                    degree_info = education_text[start:end].strip()
                    break
                if degree_info:
                    break
            
            if degree_info:
                sections['degree'] = degree_info

        # Extract target role
        target_role = self.extract_target_role(text)
        if target_role:
            sections['role'] = target_role
            
        return sections

    def extract_skills(self, text: str) -> set:
        """Extract technical skills from text"""
        doc = self.nlp(text.lower())
        skills = set()
        
        # Extract skills using pattern matching
        for token in doc:
            if token.text in self.ALL_SKILLS:
                skills.add(token.text)
                
        # Extract compound skills (e.g., "machine learning")
        for phrase in doc.noun_chunks:
            if phrase.text in self.ALL_SKILLS:
                skills.add(phrase.text)
                
        return skills

    def _skill_in_text(self, skill: str, text: str) -> bool:
        """Match skills using word boundaries to reduce false positives."""
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        return bool(re.search(pattern, text.lower()))

    def _is_technical_role(self, target_role: str) -> bool:
        role = (target_role or "").lower()
        tech_keywords = (
            'developer', 'engineer', 'programmer', 'software', 'data scientist',
            'data analyst', 'devops', 'sre', 'full stack', 'frontend', 'backend',
            'machine learning', 'ml', 'ai', 'cloud', 'architect', 'qa', 'test',
            'cyber', 'web', 'mobile', 'android', 'ios', 'database', 'dba'
        )
        return any(keyword in role for keyword in tech_keywords)

    def _expected_skills_for_role(self, target_role: str) -> set:
        """Return baseline skills expected for a target role."""
        role = (target_role or "").lower()
        expected = set()

        if any(k in role for k in ('python', 'data', 'ml', 'machine learning', 'ai')):
            expected.update({'python', 'sql', 'pandas', 'numpy'})
        if any(k in role for k in ('java', 'spring', 'backend')):
            expected.update({'java', 'sql', 'spring'})
        if any(k in role for k in ('javascript', 'frontend', 'react', 'web', 'full stack')):
            expected.update({'javascript', 'html5', 'css3', 'react'})
        if any(k in role for k in ('devops', 'cloud', 'sre', 'infrastructure')):
            expected.update({'docker', 'kubernetes', 'aws', 'git'})
        if any(k in role for k in ('android', 'mobile')):
            expected.update({'kotlin', 'java', 'android'})
        if any(k in role for k in ('software', 'developer', 'engineer')) and not expected:
            expected.update({'python', 'java', 'javascript', 'git'})

        return expected

    def calculate_ats_score(
        self,
        text: str,
        job_description: str = None,
        target_role: str = None,
    ) -> Dict[str, Any]:
        """Calculate ATS compatibility score with strict role-focused evaluation."""
        doc = self.nlp(text.lower())
        sections = self.extract_sections(text)
        target_role = target_role or sections.get('role') or ''
        is_technical = self._is_technical_role(target_role)
        reference_text = job_description or target_role or ''

        skills_by_category = {
            category: {
                skill for skill in skills if self._skill_in_text(skill, text)
            }
            for category, skills in self.SKILLS_DB.items()
        }

        programming_skills = skills_by_category.get('programming_languages', set())
        framework_skills = skills_by_category.get('frameworks_libraries', set())
        total_skills = sum(len(skills) for skills in skills_by_category.values())
        word_count = len(text.split())

        scores = {
            'format_score': 0,
            'content_score': 0,
            'skills_score': 0,
            'keyword_score': 0,
            'relevance_score': 0,
            'readability_score': 0,
            'total_score': 0,
            'feedback': [],
            'detected_skills': skills_by_category,
            'improvement_priority': [],
            'missing_role_skills': [],
            'target_role': target_role,
        }

        # Format Score (15 points max)
        format_points = 0
        if len(sections) >= 4:
            format_points += 5
        else:
            scores['feedback'].append("Add standard sections: Summary, Skills, Experience/Projects, and Education")
            scores['improvement_priority'].append(("Add Missing Sections", "High"))

        section_headers = sum(
            1 for line in text.split('\n') if line.strip().lower() in self.SECTIONS
        )
        if section_headers >= 4:
            format_points += 4
        elif section_headers >= 2:
            format_points += 2
            scores['feedback'].append("Use clear section headers to improve ATS parsing")
        else:
            scores['feedback'].append("Missing clear section headers")

        if 300 <= word_count <= 900:
            format_points += 6
        elif 150 <= word_count < 300:
            format_points += 3
            scores['feedback'].append("Resume content is brief — expand with role-relevant achievements")
            scores['improvement_priority'].append(("Expand Content", "High"))
        elif word_count < 150:
            scores['feedback'].append("Resume is too sparse for a competitive ATS score")
            scores['improvement_priority'].append(("Add Substantive Content", "Critical"))
        else:
            format_points += 4
            scores['feedback'].append("Resume may be too long — keep it concise and relevant")

        scores['format_score'] = min(15, format_points)

        # Content Score (25 points max)
        content_points = 0
        action_verbs = {
            'developed', 'implemented', 'created', 'managed', 'led', 'designed',
            'improved', 'increased', 'reduced', 'achieved', 'launched', 'optimized',
            'coordinated', 'streamlined', 'automated', 'architected', 'mentored', 'spearheaded'
        }
        verb_count = sum(1 for token in doc if token.text.lower() in action_verbs)
        metrics_patterns = [
            r'\d+%', r'\$\d+', r'\d+ years?', r'\d+\+',
            r'\d+x', r'\d+M', r'\d+K', r'\d+ users?',
            r'\d+ team members?', r'\d+ projects?'
        ]
        metrics_count = sum(1 for pattern in metrics_patterns if re.search(pattern, text, re.IGNORECASE))
        bullet_points = sum(
            1 for line in text.split('\n') if line.strip().startswith(('•', '-', '∙', '*'))
        )

        if verb_count >= 8:
            content_points += 8
        elif verb_count >= 4:
            content_points += 5
        elif verb_count >= 1:
            content_points += 2
        else:
            scores['feedback'].append("Use strong action verbs to describe achievements")
            scores['improvement_priority'].append(("Add Action Verbs", "High"))

        if metrics_count >= 4:
            content_points += 9
        elif metrics_count >= 2:
            content_points += 5
        elif metrics_count >= 1:
            content_points += 2
        else:
            scores['feedback'].append("Add quantifiable metrics (%, users, revenue, team size)")
            scores['improvement_priority'].append(("Add Metrics", "High"))

        if bullet_points >= 8:
            content_points += 8
        elif bullet_points >= 4:
            content_points += 4
        elif bullet_points >= 1:
            content_points += 2
        else:
            scores['feedback'].append("Organize achievements using bullet points")
            scores['improvement_priority'].append(("Add Bullet Points", "Medium"))

        scores['content_score'] = min(25, content_points)

        # Skills Score (25 points max) — strict for technical roles
        skills_points = 0
        if total_skills >= 12:
            skills_points += 10
        elif total_skills >= 8:
            skills_points += 7
        elif total_skills >= 4:
            skills_points += 4
        elif total_skills >= 1:
            skills_points += 2
        else:
            scores['feedback'].append("No technical or professional skills detected")
            scores['improvement_priority'].append(("Add Skills Section", "Critical"))

        if programming_skills:
            skills_points += min(8, len(programming_skills) * 2)
        elif is_technical:
            scores['feedback'].append(
                f"No programming languages found — required for {target_role or 'this technical role'}"
            )
            scores['improvement_priority'].append(("Add Programming Languages", "Critical"))

        if framework_skills:
            skills_points += min(4, len(framework_skills))
        elif is_technical:
            scores['feedback'].append("Add frameworks/libraries relevant to the target role")
            scores['improvement_priority'].append(("Add Frameworks", "High"))

        active_categories = len([cat for cat, skills in skills_by_category.items() if skills])
        if active_categories >= 3:
            skills_points += 3
        elif active_categories >= 2:
            skills_points += 1

        scores['skills_score'] = min(25, skills_points)

        # Keyword / Role Match Score (25 points max)
        keyword_points = 0
        if reference_text.strip():
            vectorizer = TfidfVectorizer(stop_words='english')
            try:
                tfidf_matrix = vectorizer.fit_transform([text.lower(), reference_text.lower()])
                similarity = (tfidf_matrix * tfidf_matrix.T).toarray()[0][1]
                keyword_points = int(similarity * 25)

                expected_skills = self._expected_skills_for_role(target_role)
                if expected_skills:
                    missing = sorted(
                        skill for skill in expected_skills
                        if not self._skill_in_text(skill, text)
                    )
                    scores['missing_role_skills'] = missing
                    if missing:
                        penalty = min(15, len(missing) * 3)
                        keyword_points = max(0, keyword_points - penalty)
                        scores['feedback'].append(
                            f"Missing role-critical skills: {', '.join(missing[:6])}"
                        )
                        scores['improvement_priority'].append(("Add Role-Critical Skills", "Critical"))

                if similarity < 0.2:
                    scores['feedback'].append(
                        f"Resume content does not align well with the target role: {target_role or 'specified role'}"
                    )
                    scores['improvement_priority'].append(("Improve Role Alignment", "High"))
            except Exception:
                keyword_points = 5
        else:
            keyword_points = 3
            scores['feedback'].append("Specify a target role to improve role-match scoring")

        scores['keyword_score'] = max(0, min(25, keyword_points))

        # Readability Score (10 points max)
        readability_points = 10
        sentences = list(doc.sents)
        avg_sentence_length = (
            sum(len(sent) for sent in sentences) / len(sentences) if sentences else 0
        )
        if avg_sentence_length > 25:
            readability_points -= 3
            scores['feedback'].append("Simplify long sentences for better readability")
        passive_constructs = sum(
            1 for sent in sentences if any(token.dep_ == 'auxpass' for token in sent)
        )
        if sentences and passive_constructs > len(sentences) * 0.3:
            readability_points -= 2
            scores['feedback'].append("Prefer active voice in achievement statements")

        scores['readability_score'] = max(0, readability_points)

        raw_total = (
            scores['format_score'] +
            scores['content_score'] +
            scores['skills_score'] +
            scores['keyword_score'] +
            scores['readability_score']
        )

        # Completeness penalty — prevents inflated scores on sparse resumes
        completeness_penalty = 0
        if word_count < 120:
            completeness_penalty += 25
        elif word_count < 200:
            completeness_penalty += 15
        elif word_count < 300:
            completeness_penalty += 8

        if is_technical and not programming_skills:
            completeness_penalty += 20

        if total_skills == 0:
            completeness_penalty += 15

        if not sections.get('skills') and 'technical skills' not in sections and total_skills < 3:
            completeness_penalty += 10

        scores['total_score'] = max(0, min(100, raw_total - completeness_penalty))

        if scores['total_score'] < 50:
            scores['feedback'].insert(
                0,
                "Resume is incomplete or missing fundamentals for the target role — score reflects actual readiness"
            )
        elif scores['total_score'] < 70:
            scores['feedback'].append("Focus on high-priority improvements before applying")
        elif scores['total_score'] >= 85:
            scores['feedback'].append("Strong ATS alignment for the specified role")

        return scores

    def get_parsed_data(self, file) -> Dict[str, Any]:
        """Get complete parsed data from resume"""
        text = self.extract_text(file)
        if not text:
            return None
            
        sections = self.extract_sections(text)
        skills = self.extract_skills(text)
        
        return {
            'full_text': text,
            'sections': sections,
            'skills': list(skills),
            'word_count': len(text.split()),
            'scores': self.calculate_ats_score(
                text,
                target_role=sections.get('role'),
            )
        } 