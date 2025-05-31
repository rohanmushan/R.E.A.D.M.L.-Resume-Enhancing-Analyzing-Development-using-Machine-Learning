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
        
        # Enhanced skills database with categories
        self.SKILLS_DB = {
            'programming_languages': {
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php',
                'swift', 'kotlin', 'go', 'rust', 'scala', 'perl', 'r', 'matlab'
            },
            'frameworks': {
                'react', 'angular', 'vue.js', 'django', 'flask', 'spring', 'express',
                'node.js', 'next.js', 'nuxt.js', 'flutter', 'tensorflow', 'pytorch'
            },
            'databases': {
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
                'oracle', 'sql server', 'dynamodb', 'firebase'
            },
            'cloud_devops': {
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'terraform',
                'ansible', 'circleci', 'github actions', 'gitlab ci'
            },
            'ai_ml': {
                'machine learning', 'deep learning', 'nlp', 'computer vision',
                'data science', 'neural networks', 'reinforcement learning',
                'statistical analysis', 'big data', 'data mining'
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

    def calculate_ats_score(self, text: str, job_description: str = None) -> Dict[str, Any]:
        """Calculate enhanced ATS compatibility score"""
        doc = self.nlp(text.lower())
        sections = self.extract_sections(text)
        
        # Extract skills with categories
        skills_by_category = {
            category: {skill for skill in skills 
                      if skill in text.lower()}
            for category, skills in self.SKILLS_DB.items()
        }
        
        scores = {
            'format_score': 0,
            'content_score': 0,
            'skills_score': 0,
            'keyword_score': 0,
            'relevance_score': 0,
            'total_score': 0,
            'feedback': [],
            'detected_skills': skills_by_category
        }
        
        # Format Score (20 points)
        format_points = 20
        if len(sections) < 4:
            format_points -= 5
            scores['feedback'].append("Missing key sections - add more sections to your resume")
        if len(list(doc.sents)) < 10:
            format_points -= 5
            scores['feedback'].append("Content is too brief - add more detailed descriptions")
        
        # Check for section headers formatting
        section_headers = sum(1 for line in text.split('\n') 
                            if line.strip().lower() in self.SECTIONS)
        if section_headers < 4:
            format_points -= 5
            scores['feedback'].append("Use clear section headers to organize your resume")
        
        scores['format_score'] = max(0, format_points)
        
        # Content Score (30 points)
        content_points = 30
        words = len(text.split())
        if words < 300:
            content_points -= 10
            scores['feedback'].append("Resume is too short - aim for 300-700 words")
        elif words > 1000:
            content_points -= 5
            scores['feedback'].append("Resume might be too long - consider condensing")
        
        # Check for action verbs and metrics
        action_verbs = ['developed', 'implemented', 'created', 'managed', 'led',
                       'designed', 'improved', 'increased', 'reduced', 'achieved']
        verb_count = sum(1 for token in doc if token.text.lower() in action_verbs)
        
        metrics_patterns = [r'\d+%', r'\$\d+', r'\d+ years', r'\d+\+']
        metrics_count = sum(1 for pattern in metrics_patterns 
                          if re.search(pattern, text, re.IGNORECASE))
        
        if verb_count < 5:
            content_points -= 10
            scores['feedback'].append("Use more action verbs to describe your experiences")
        if metrics_count < 3:
            content_points -= 5
            scores['feedback'].append("Add more quantifiable achievements and metrics")
        
        scores['content_score'] = max(0, content_points)
        
        # Skills Score (25 points)
        skills_points = 25
        total_skills = sum(len(skills) for skills in skills_by_category.values())
        
        if total_skills < 5:
            skills_points -= 15
            scores['feedback'].append("Add more technical skills relevant to your field")
        elif total_skills < 10:
            skills_points -= 10
            scores['feedback'].append("Consider adding more diverse technical skills")
        
        # Check for skills distribution
        if not any(skills_by_category[cat] for cat in ['programming_languages', 'frameworks']):
            skills_points -= 5
            scores['feedback'].append("Add core technical skills (programming languages/frameworks)")
        
        scores['skills_score'] = max(0, skills_points)
        
        # Keyword and Relevance Score (25 points)
        keyword_points = 25
        if job_description:
            # Calculate TF-IDF similarity
            vectorizer = TfidfVectorizer(stop_words='english')
            try:
                tfidf_matrix = vectorizer.fit_transform([text.lower(), job_description.lower()])
                similarity = (tfidf_matrix * tfidf_matrix.T).toarray()[0][1]
                keyword_points = int(similarity * 25)
                
                # Extract key terms from job description
                job_doc = self.nlp(job_description.lower())
                key_terms = [token.text for token in job_doc 
                           if not token.is_stop and not token.is_punct]
                
                # Check for missing important terms
                missing_terms = [term for term in set(key_terms) 
                               if term not in text.lower() 
                               and len(term) > 3]
                
                if missing_terms:
                    scores['feedback'].append(f"Consider adding these keywords: {', '.join(missing_terms[:5])}")
                
                if similarity < 0.3:
                    scores['feedback'].append("Resume doesn't match job description well - tailor it more")
            except Exception as e:
                st.warning(f"Error in keyword analysis: {str(e)}")
                keyword_points = 15  # Default if analysis fails
        
        scores['keyword_score'] = max(0, keyword_points)
        
        # Calculate total score
        scores['total_score'] = (
            scores['format_score'] +
            scores['content_score'] +
            scores['skills_score'] +
            scores['keyword_score']
        )
        
        # Add improvement suggestions based on total score
        if scores['total_score'] < 70:
            scores['feedback'].append("Consider professional resume review for major improvements")
        if scores['total_score'] < 50:
            scores['feedback'].append("Significant improvements needed in content and formatting")
        
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
            'scores': self.calculate_ats_score(text)
        } 