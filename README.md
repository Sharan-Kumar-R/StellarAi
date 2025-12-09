# Tamil Sales Call Analyzer

A FastAPI-based web application that analyzes Tamil sales call transcripts using Groq LLM and generates comprehensive PDF reports.

## Features

- **Tamil Language Support**: Handles Tamil text input with proper font rendering
- **AI-Powered Analysis**: Uses Groq LLM (Llama 3.3 70B) for intelligent sales call analysis
- **Comprehensive Reports**: Generates 12-page professional PDF reports including:
  - Executive Summary
  - Performance Metrics Dashboard
  - Products Analysis with Charts
  - Promise & Commitment Analysis
  - Improvement Roadmap
  - Sentiment Analysis
  - Complete Transcripts (Tamil + English)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd create
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Groq API key in `main.py`:
```python
GROQ_API_KEY = "your-api-key-here"
```

## Usage

1. Start the server:
```bash
uvicorn main:app --reload
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

3. Paste your Tamil sales call transcript and click "Analyze Call"

4. Download the generated PDF report

## Project Structure

```
create/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates
│   ├── index.html      # Home page
│   └── result.html     # Results page
├── static/             # Static files (if any)
└── reports/            # Generated PDF reports (gitignored)
```

## Technologies Used

- **FastAPI**: Web framework
- **Groq**: LLM for analysis
- **FPDF2**: PDF generation
- **Matplotlib**: Chart generation
- **Deep Translator**: Tamil to English translation
- **Tailwind CSS**: Frontend styling

## Requirements

- Python 3.10+
- Windows (for Nirmala.ttf Tamil font support)

## License

Proprietary - Sharan Enterprises

## Author

Developed for Sharan Enterprises
