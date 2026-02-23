
import re
import sys
import os

# Set up path to import backend modules
sys.path.append(os.getcwd())

from backend.utils.srcc_form_extractor import SRCCFormExtractor
from backend.utils.intelligent_extractor import IntelligentFieldExtractor

# Raw text provided by user in Step 1549
RAW_TEXT = """
--- Page 1 ---
SHRI RAM COLLEGE OF COMMERCE
ACADEMIC SESSION_
COURSE (Please ✓ )
STUDENT'S DATA FORM
All informations need to be filled in capital letters.
2024-2027
B.COM.(H) ✓ B.A.(H) ECO
Admission Category (Please ✓) GEN OBC SC ST Sports PWD EWS
Other (Specify)
DU Portal Form Number
Foreign CW
KM Others ECA
243550516046
747
21
CUET Score
College Roll No.
Date of Admission
1.
NAME IN BLOCK LETTERS
KARAN
First Name
2. Gender {Tick (✓)}
3. Date of Birth
24BC105
20
08
2024
D D
M M
YYYY
Middle Name
Transgender
Taran fidav
Signature of Student
YADAV
Surname
Male
Female
27
D D
06
M M
2006
YYYY
4. Permanent
Address
5. Local Address for
Correspondence
(if different from 4)
SHANTI
,
ROAD
33281267
CIRCULAR
State HARYANA
State
>
NAGAR
REWARI
>
PIN 1 234 01
PIN
6. Email
YADAV
KARAN5044@GMAI
L
•
COM
7. Contact Numbers
9468290142
8708352061
8. Mother's Name
PUSHPA YADAV
9. Father's Name
ANI L YADAV
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

--- Page 2 ---
1
DECLARATION & UNDERTAKING BY THE STUDENT
1. 1, Karan Yadav
hereby declare that particulars filled in this form are
true and correct to the best of my knowledge and documents attached are genuine in all
respects.
...
Date
Place
24-3-25¨¨¨
Rewari, Haryana
lavis
Signature of Candidate
DECLARATION & UNDERTAKING BY PARENT / GUARDIAN OF THE STUDENT
I,
guardian of
Yadav
Pushpa
Karan Yadav
✓
...
"""

def test_full_extraction():
    print("Testing Full Extraction from User Raw Text...")
    
    # 1. Test Intelligent Extractor (General)
    print("\n--- Intelligent Extractor Results ---")
    ie = IntelligentFieldExtractor()
    ie_results = ie.extract(RAW_TEXT)
    
    fields_to_check = [
        'student_name', 'father_name', 'mother_name', 'email', 'phone_number',
        'cuet_score', 'cuet_section', 'academic_session', 'college_roll_no',
        'permanent_address', 'correspondence_address'
    ]
    
    for field in fields_to_check:
        val = ie_results.get(field, "NOT FOUND")
        if field == 'cuet_section': continue 
        print(f"{field}: {val}")
        
    # Check CUET details specifically
    print("\n--- CUET Details Formatted ---")
    cuet_keys = [k for k in ie_results.keys() if 'cuet_' in k]
    for k in sorted(cuet_keys):
        print(f"{k}: {ie_results[k]}")

    # 2. Test SRCC Extractor (Specialized)
    print("\n--- SRCC Extractor Results ---")
    srcc = SRCCFormExtractor()
    srcc_results = srcc.extract(RAW_TEXT) # Pass text, not previous results
    
    for field in fields_to_check:
        val = srcc_results.get(field, "NOT FOUND")
        print(f"{field}: {val}")

if __name__ == "__main__":
    test_full_extraction()
