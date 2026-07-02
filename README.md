🚀 AI Resume Analyzer & Ranker
A comprehensive dashboard designed to streamline the recruitment process using AI-driven resume parsing and ranking.

📋 Table of Contents
Project Overview

Features

Tech Stack

Installation Guide

How to Run

Project Structure

🎯 Project Overview
This tool helps recruiters analyze candidate resumes against job descriptions. It uses FAISS for vector-based similarity search to ensure you find the most qualified candidates quickly.

✨ Features
Intelligent Ranking: Automatically calculates match percentages based on skills and experience.

KPI Dashboard: Visual summaries of candidate match quality (Excellent, Good, Average).

Detailed View: Easy navigation to candidate profiles and resume insights.

Customizable: Easily extendable to support different resume formats.

🛠️ Tech Stack
Frontend: Streamlit

Backend Logic: Python, Pandas

AI/ML: Sentence-Transformers, FAISS

Data Processing: PyMuPDF, python-docx

⚙️ Installation Guide
1. Setup Virtual Environment
Bash
# Open terminal in project folder
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1
2. Install Dependencies
Bash
pip install -r requirements.txt
🚀 How to Run
Once installed, execute the application using the following command:

Bash
python -m streamlit run frontend/app.py
📂 Project Structure
Plaintext
ai-resume-analyzer/
├── backend/            # Business logic (Ranking, Scoring)
│   ├── ranking.py
│   └── scoring.py
├── frontend/           # Streamlit UI files
│   ├── app.py
│   └── pages/
├── requirements.txt    # Project dependencies
└── README.md
