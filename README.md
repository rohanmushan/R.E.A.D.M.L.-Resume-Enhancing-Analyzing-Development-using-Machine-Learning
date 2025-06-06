# R.E.A.D.M.L. - Resume Enhancement System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)

## 📝 Overview

R.E.A.D.M.L. (Resume Enhancing, Analyzing & Developing using Machine Learning) is an advanced AI-powered resume creation and analysis platform. It helps users create professional, ATS-friendly resumes while providing intelligent suggestions for improvement using Google's Gemini AI technology.

## 🎥 Demo

![Dashboard Preview](assets/dashboard.png)
*Main dashboard of R.E.A.D.M.L.*

Check out our video demo: [Watch on YouTube](https://youtube.com/your-demo-link)

### Sample Outputs
- [Example Resume 1](examples/resume1.pdf) - Software Engineer Resume
- [Example Resume 2](examples/resume2.pdf) - Data Scientist Resume


## 🌟 Key Features

### 1. Smart Resume Creation
- Interactive form-based resume builder
- Real-time AI suggestions for content improvement
- Professional template with modern design
- Automatic formatting and layout optimization

### 2. AI-Powered Analysis
- ATS (Applicant Tracking System) compatibility scoring
- Content quality assessment
- Keyword optimization suggestions
- Profile strength analysis

### 3. Resume Enhancement
- Smart content suggestions using Gemini AI
- Skills gap analysis
- Industry-specific keyword recommendations
- Professional language improvements

### 4. Technical Features
- PDF generation with custom formatting
- Resume parsing and analysis
- Real-time AI feedback
- Multi-page support
- Responsive design

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.8+
- **AI/ML**: 
  - Google Gemini AI
  - spaCy for NLP
  - scikit-learn for text analysis
- **Document Processing**:
  - pdfkit for PDF generation
  - python-docx for DOCX handling
  - PyPDF2 for PDF parsing

## 📋 Prerequisites

1. Python 3.8 or higher
2. PostgreSQL database
3. Google Gemini API key
4. wkhtmltopdf (for PDF generation)

## 🚀 Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone hhttps://github.com/rohanmushan/R.E.A.D.M.L..git
   cd R.E.A.D.M.L.
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv readml
   # For Windows
   .\readml\Scripts\activate
   # For Unix/MacOS
   source readml/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install wkhtmltopdf**
   - Windows: Download from [wkhtmltopdf downloads](https://wkhtmltopdf.org/downloads.html)
   - Linux: `sudo apt-get install wkhtmltopdf`
   - MacOS: `brew install wkhtmltopdf`

5. **Configure Environment**
   Create `.streamlit/secrets.toml`:
   ```toml
   [api_keys]
   GEMINI_API_KEY = "your-gemini-api-key"
   ```

6. **Run the Application**
   ```bash
   streamlit run app.py
   ```

## 📁 Project Structure

```
R.E.A.D.M.L/
├── app.py                 # Main Streamlit application
├── resume_template.py     # Resume generation template
├── requirements.txt       # Project dependencies
├── .streamlit/           # Streamlit configuration
├── static/              # CSS and static assets
│   └── styles.css
├──assets/
│   ├── SS-1.png
    └── SS-1.png
├── templates/           # HTML templates
│   └── resumeTemplate.docx # Resume template
├── utils/              # Utility modules
│   ├── pdf_generator.py   # PDF generation utilities
│   ├── gemini_utils.py   # AI integration
│   └── resume_parser.py  # Resume parsing
└── output/             # Generated resumes
```

## 🔧 Configuration

### API Keys
1. Get a Gemini API key from Google Cloud Console
2. Add it to `.streamlit/secrets.toml`

## 🎯 Usage

1. **Create New Resume**
   - Fill in the interactive form
   - Get real-time AI suggestions
   - Generate professional PDF

2. **Analyze Existing Resume**
   - Upload existing resume
   - Get ATS compatibility score
   - Receive improvement suggestions

## 📋 Use Cases

### 1. Fresh Graduate
- Create a professional resume from scratch
- Get AI suggestions for highlighting academic projects
- Optimize keywords for entry-level positions

### 2. Career Transition
- Analyze existing resume against target job requirements
- Identify transferable skills
- Get suggestions for industry-specific keywords

### 3. Resume Enhancement
- Upload existing resume for ATS compatibility check
- Receive actionable improvement suggestions
- Generate an optimized version with better formatting

## 🎯 Usage Examples

### Creating a New Resume
```python
# Run the application
streamlit run app.py

# Access via browser at http://localhost:8501
```

### Analyzing Existing Resume
1. Navigate to "Resume Analysis" section
2. Upload your PDF resume
3. Get instant feedback:

### Generating Enhanced Resume
```bash
# Generate PDF with custom template
python utils/pdf_generator.py --template modern --output resume.pdf

# Parse existing resume
python utils/resume_parser.py --input existing_resume.pdf
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Rohan Mushan** - *Initial work* - [MyGithub](http://github.com/rohanmushan)

## 🙏 Acknowledgments

- Google Gemini AI for providing the AI capabilities
- Streamlit for the amazing web framework
- The open-source community for various tools and libraries
- Special thanks to all contributors who have helped shape this project

## 📧 Contact & Support

- Project Maintainer: [rohanmushan08@gmail.com](mailto:rohanmushan08@gmail.com)
- Project Link: [git@github.com:rohanmushan/R.E.A.D.M.L.-Resume-Enhancing-Analysing-Development-using-Machine-Learning-.git](https://github.com/rohanmushan/R.E.A.D.M.L.)
- Report Issues: [Issue Tracker](https://github.com/rohanmushan/R.E.A.D.M.L./issues)
- Documentation: [Wiki](https://github.com/rohanmushan/R.E.A.D.M.L./wiki)
