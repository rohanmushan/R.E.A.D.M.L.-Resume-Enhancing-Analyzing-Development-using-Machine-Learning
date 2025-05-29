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
            'professional experience', 'technical skills'
        ]
        
        # Initialize skills database (can be expanded)
        self.TECHNICAL_SKILLS = set([
            'python', 'java', 'javascript', 'c++', 'ruby', 'php',
            'sql', 'mysql', 'postgresql', 'mongodb', 'react',
            'angular', 'vue', 'node.js', 'express', 'django',
            'flask', 'spring', 'docker', 'kubernetes', 'aws',
            'azure', 'gcp', 'machine learning', 'ai', 'data science'
        ])

    def extract_text_from_pdf(self, file) -> str:
        """Extract text from PDF file"""
        try:
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
            if token.text in self.TECHNICAL_SKILLS:
                skills.add(token.text)
                
        # Extract compound skills (e.g., "machine learning")
        for phrase in doc.noun_chunks:
            if phrase.text in self.TECHNICAL_SKILLS:
                skills.add(phrase.text)
                
        return skills

    def calculate_ats_score(self, text: str, job_description: str = None) -> Dict[str, Any]:
        """Calculate ATS compatibility score"""
        doc = self.nlp(text)
        sections = self.extract_sections(text)
        skills = self.extract_skills(text)
        
        scores = {
            'format_score': 0,
            'content_score': 0,
            'skills_score': 0,
            'keyword_score': 0,
            'total_score': 0,
            'feedback': []
        }
        
        # Format Score (20 points)
        format_points = 20
        if len(sections) < 3:
            format_points -= 10
            scores['feedback'].append("Missing key sections in resume")
        if len(list(doc.sents)) < 10:
            format_points -= 5
            scores['feedback'].append("Resume content seems too brief")
        scores['format_score'] = max(0, format_points)
        
        # Content Score (30 points)
        content_points = 30
        words = len(text.split())
        if words < 200:
            content_points -= 15
            scores['feedback'].append("Resume content is too short")
        elif words > 1000:
            content_points -= 10
            scores['feedback'].append("Resume might be too lengthy")
            
        # Check for action verbs
        action_verbs = ['developed', 'implemented', 'created', 'managed', 'led', 'designed']
        verb_count = sum(1 for token in doc if token.text.lower() in action_verbs)
        if verb_count < 5:
            content_points -= 10
            scores['feedback'].append("Use more action verbs to describe experiences")
        scores['content_score'] = max(0, content_points)
        
        # Skills Score (25 points)
        skills_points = 25
        if len(skills) < 5:
            skills_points -= 15
            scores['feedback'].append("Add more technical skills")
        scores['skills_score'] = max(0, skills_points)
        
        # Keyword Score (25 points)
        keyword_points = 25
        if job_description:
            # Calculate similarity between resume and job description
            job_doc = self.nlp(job_description)
            similarity = doc.similarity(job_doc)
            keyword_points = int(similarity * 25)
            
            if similarity < 0.5:
                scores['feedback'].append("Resume doesn't match job description well")
        scores['keyword_score'] = max(0, keyword_points)
        
        # Calculate total score
        scores['total_score'] = (
            scores['format_score'] +
            scores['content_score'] +
            scores['skills_score'] +
            scores['keyword_score']
        )
        
        # Add improvement suggestions
        if scores['total_score'] < 70:
            scores['feedback'].append("Consider professional resume review")
        if scores['total_score'] < 50:
            scores['feedback'].append("Major improvements needed in content and format")
            
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