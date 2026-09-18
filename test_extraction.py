"""
Test script to validate action item extraction across multiple real-world meeting scenarios.
Run: python test_extraction.py
"""

import re, sys

# ---- Copy of the extraction functions from app.py ----

def is_bilingual_or_tamil(text):
    if re.search(r'[\u0B80-\u0BFF]', text):
        return True
    tanglish_words = {
        'naan','nanga','neenga','avanga','enna','edhu','epdi','eppadi',
        'romba','nalla','irukku','irukanga','pannunga','pannalam','panren',
        'panniten','solren','sollunga','sonnaru','kudunga','vaanga','ponga',
        'illai','illa','aama','appo','ippo','adhu','idhu','pathu','pathi',
        'kooda','mattum','mudiyum','mudiyathu','theva','venum','theriyum',
        'pesalam','pesunga','pannu','tharen','mudinjuthu','aachu'
    }
    tokens = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    return len(tokens.intersection(tanglish_words)) >= 1

def extract_actions(formatted_text, speaker_data):
    all_speakers = list(speaker_data.keys())
    
    action_pattern = re.compile(
        r'\b(upload|send|share|submit|create|prepare|update|check|verify|fix|deploy|complete|'
        r'finish|schedule|mail|email|write|draft|organize|test|implement|review|follow up on|'
        r'will|shall|need to|needs to|must|should|have to|has to|let\'s|can you|could you|'
        r'please|kindly|make sure to)\b',
        re.IGNORECASE
    )
    tanglish_action_pattern = re.compile(
        r'\b(upload\s*pannu|upload\s*pannunga|share\s*pannu|share\s*pannunga|anupu|anupunga|'
        r'check\s*pannu|check\s*pannunga|prepare\s*pannu|prepare\s*pannunga|complete\s*pannu|'
        r'mudichaachu|mudikanum|mudikkanum|panren|anupuren)\b',
        re.IGNORECASE
    )

    action_items = []
    seen_tasks = set()

    for spk, texts in speaker_data.items():
        full_text = " ".join(texts)
        sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', full_text) if s.strip()]
        for s in sentences:
            s_clean = s.strip()
            if (action_pattern.search(s_clean) or tanglish_action_pattern.search(s_clean)) and len(s_clean) > 10:
                s_lower = s_clean.lower()
                
                if re.search(r'\b(i will|i\'ll|i am going to|i need to|i\'m going to|i can handle|panren|anupuren)\b', s_lower):
                    assigned = spk
                else:
                    found_target = False
                    for other_spk in all_speakers:
                        if other_spk.lower() in s_lower:
                            assigned = other_spk
                            found_target = True
                            break
                    if not found_target:
                        if re.search(r'\b(can you|could you|please|kindly|you should|you will|pannunga|anupunga)\b', s_lower):
                            other_speakers = [s_name for s_name in all_speakers if s_name != spk]
                            assigned = other_speakers[0] if other_speakers else "Assigned Participant"
                        elif re.search(r'\b(we will|we\'ll|let\'s|team)\b', s_lower):
                            assigned = "Entire Team"
                        else:
                            assigned = spk

                task_text = re.sub(r'^(and|so|also|then|well|yeah|okay|ok)\s+', '', s_clean, flags=re.IGNORECASE).strip()
                if task_text:
                    task_text = task_text[0].upper() + task_text[1:]
                
                task_key = task_text.lower()[:50]
                if task_key not in seen_tasks and len(action_items) < 10:
                    seen_tasks.add(task_key)
                    action_items.append({
                        "task": task_text,
                        "raised_by": spk,
                        "assigned_to": assigned
                    })
    return action_items

# ---- TEST CASES ----

tests = [
    # T1: English - explicit task delegation
    {
        "name": "T1: English – clear delegation",
        "speaker_data": {
            "Speaker A": [
                "John, can you upload the resource files to the shared drive by end of day?",
                "I will send the updated presentation to the client tonight.",
                "The team should review the Q3 report before Friday."
            ],
            "Speaker B": [
                "Sure, I'll upload the files.",
                "I need to prepare the test environment for tomorrow's demo."
            ]
        }
    },
    # T2: Tanglish – mixed Tamil-English action items
    {
        "name": "T2: Tanglish – bilingual action items",
        "speaker_data": {
            "Speaker A": [
                "Neenga resource files upload pannunga.",
                "Design documents share pannu.",
                "Sprint review meeting schedule pannunga by Friday."
            ],
            "Speaker B": [
                "Sure, panren.",
                "API integration complete pannunga by Wednesday."
            ]
        }
    },
    # T3: English – soft/implied tasks (might match action_pattern word "should/will")
    {
        "name": "T3: English – soft commitments",
        "speaker_data": {
            "Speaker A": [
                "We should probably look at the budget next week.",
                "I think the team will be fine with the current deadline.",
                "The client needs to know about the delay. Can someone email them?"
            ],
            "Speaker B": [
                "Yes I'll handle the email to the client.",
                "We need to fix the login bug before release."
            ]
        }
    },
    # T4: No real action items – general discussion
    {
        "name": "T4: No action items – pure discussion",
        "speaker_data": {
            "Speaker A": [
                "The project is going well overall.",
                "The design looks really clean.",
                "I liked the color scheme they proposed."
            ],
            "Speaker B": [
                "Agreed, the typography is really good too.",
                "I think the team has done an excellent job so far."
            ]
        }
    },
    # T5: Multiple speakers, chained assignments
    {
        "name": "T5: Multiple speakers with chained tasks",
        "speaker_data": {
            "Speaker A": [
                "I will draft the project proposal document.",
                "Can you verify the test results and share the report?"
            ],
            "Speaker B": [
                "Yes, I'll verify the test results.",
                "We need to deploy the hotfix to production immediately.",
                "Please schedule a call with the client team."
            ],
            "Speaker C": [
                "I'll schedule the call.",
                "We should also update the documentation on Confluence."
            ]
        }
    },
    # T6: Tanglish – spoken action with no clear assignee
    {
        "name": "T6: Tanglish – no explicit assignee",
        "speaker_data": {
            "Speaker A": [
                "Database migration script ready panna venum.",
                "Testing environment setup pannalam."
            ],
            "Speaker B": [
                "Reports generate panni manager kita anupunga."
            ]
        }
    },
]

# ---- Run Tests ----
print("=" * 65)
print("  ACTION ITEM EXTRACTION TEST RESULTS")
print("=" * 65)

all_correct = 0
total = 0

for t in tests:
    spk_data = t["speaker_data"]
    formatted = "\n".join(f"{spk}: {' '.join(txts)}" for spk, txts in spk_data.items())
    results = extract_actions(formatted, spk_data)
    bilingual = is_bilingual_or_tamil(formatted)
    
    print(f"\n{'─'*65}")
    print(f"TEST: {t['name']}")
    print(f"Bilingual detected: {bilingual}")
    print(f"Action items found: {len(results)}")
    
    if results:
        for i, item in enumerate(results, 1):
            print(f"  [{i}] Task      : {item['task'][:90]}")
            print(f"       Raised by  : {item['raised_by']}")
            print(f"       Assigned to: {item['assigned_to']}")
    else:
        print("  → (No action items detected)")
    total += 1

print(f"\n{'=' * 65}")
print(f"  Completed {total} test cases.")
print("=" * 65)
