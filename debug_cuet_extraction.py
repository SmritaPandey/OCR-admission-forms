
import re

# Actual raw text form the user
raw_text_user = """
10. Details of marks obtained in Qualifying Examination: [CUET]
SI.
Subjects
No.
Total
Score
Score
Obtained
(1)
ENGLISH
200
165
(11)
ACCOUNTANCY / BOOK-KEEPING
200
194
(11) BUSINESS STUDIES
200
194
(IV)
ECONOMICS | BUSINESS ECONOMICS
200
194
(V)
3|3
MATHEMATICS (APPLIED MATHEMATICS
200
80
(VI)
GENERAL TEST
250
136
(VII) TOTAL CUET SCORE OBTAINED
1250
963
"""

mock_raw_texts = [raw_text_user]

def extract_cuet_marks(raw_text):
    print(f"\n--- Testing Raw Text Segment ---")
    subjects = []
    
    # regex from intelligent_extractor.py
    # Updated to what is currently in the file (approximating from previous steps)
    row_pattern = re.compile(
        r'(?:\(([IVX\d]{1,3})\))?\s*'
        r'(?:\s*\.\s*)?'
        r'([A-Za-z][A-Za-z\s&.]{2,25})\s+'  # Subject name (Still strict!)
        r'(?:\s*\.\s*)?'
        r'(\d{2,3}(?:\.\d+)?)\s+'
        r'(?:\s*\.\s*)?'
        r'(\d{1,3}(?:\.\d+)?)',
        re.IGNORECASE
    )
    
    # Try regex first
    matches = list(row_pattern.finditer(raw_text))
    print(f"Found {len(matches)} matches via Regex")
    
    for match in matches:
        subject_name = match.group(2).strip()
        total_score = match.group(3)
        score_obtained = match.group(4)
        print(f"Captured: {subject_name} | Max: {total_score} | Obt: {score_obtained}")
        
    print("-" * 20)
    
    # Improved Regex Proposal
    print("Testing Improved Regex...")
    
    # Relaxation explanation:
    # 1. Subject name: Allow '/', '-', '|', '(', ')', more length (up to 50)
    # 2. Before subject name: Allow optional "noise" like "3|3" or digits if they are not the main subject
    # 3. Handling '\s+' vs '\s*': Ensure multiline matching works if there are newlines.
    
    better_pattern = re.compile(
        r'(?:\(([IVX\d]{1,3})\))?\s*'   # Optional numeral
        r'(?:[\d|]+\s+)?'               # NEW: Optional noise like "3|3" or digits before subject
        r'(?:\.\s*)?'                   # Optional dot
        r'([A-Za-z][A-Za-z\s&./|\(\)-]{2,50})\s+'  # Subject: Expanded charset and length
        r'(?:\.\s*)?'
        r'(\d{2,3}(?:\.\d+)?)\s+'
        r'(?:\.\s*)?'
        r'(\d{1,3}(?:\.\d+)?)',
        re.IGNORECASE
    )
    
    matches_new = list(better_pattern.finditer(raw_text))
    print(f"Found {len(matches_new)} matches via Improved Regex")
    
    for match in matches_new:
        subject_name = match.group(1).strip() # Group index shifted due to non-capturing groups? No, should be group 1 if noise is non-capturing
        total_score = match.group(2)
        score_obtained = match.group(3)
        print(f"Captured: {subject_name} | Max: {total_score} | Obt: {score_obtained}")

for text in mock_raw_texts:
    extract_cuet_marks(text)
