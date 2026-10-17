# Demo video script (about 8.5 minutes)

Read the lines in quotes in your own words. Text in [brackets] is what to do on screen, not what to say.

## Before you press record
1. `python samples/make_samples.py` (so the sample dates are fresh).
2. Open VS Code on the `kims` folder, a terminal in it with `(.venv)` active, and the app (`streamlit run app.py`) in the browser.
3. Close notifications. Do a 10-second test recording to check the sound.
4. Have this ready to paste later (Sample must be set to `(none)`):
```
Named insured: Lakeside Dental Group
Business type: Dental clinic
TIV: $4.2 million
Claims in the past 5 years: none
Year built: 1972
Sprinklers: full
Effective date: December 20, 2026
```

---

## 1. Introduction (0:00 - 0:50)  [show the app home screen]
"Hi, I'm [your name]. This is my first-round project for the AI Solutions Developer role at Knight Management Insurance Services.
The app reads a fictional broker email and its attachments, extracts the key facts, and shows the exact line of evidence each fact came from. It then checks five rules, writes a summary for the underwriter, and drafts a follow-up email to the broker.
I want to be upfront about my tools: I used Claude, an AI coding assistant, to help generate the first version of the code. I then read and tested it, and I'll explain how every part works. The app can also use an LLM at run time, either a local Ollama model or the Claude API, but it works without one."

## 2. Code tour (0:50 - 2:10)  [switch to VS Code, expand the `core` folder]
"Let me show how it's built. Everything is in the `core` folder, and each file does one job.
`ingest.py` turns files into text. It handles PDF, Word, Excel, CSV and email files, and for an email it opens the attachments too. If a file is corrupt, it records a warning and carries on instead of crashing.
`fields.py` lists the seven facts we extract, like insured value and year built, and how to clean each one, for example turning '$14.0 million' into 14,000,000.
`llm.py` and `extract.py` do the extraction. This is the key design idea: the LLM only proposes. It must give a value and a word-for-word quote. My code then checks that the quote really exists in that document. If it doesn't, the answer is thrown away and the rule-based extractor is used instead. So the app can't invent evidence.
`rules.py` holds the five rules as plain code, not the LLM, so each one is predictable and testable. [If you have swapped in the real rules from the brief, say: 'These are the five rules from the brief.' Otherwise say: 'These five rules are placeholders I defined, and they are easy to replace.']
`report.py` builds the verdict, the summary and the follow-up email. And `app.py` is the Streamlit screen."

## 3. Demo: clean submission (2:10 - 3:20)  [browser; Sample = 1_harbor_bakes_clean; click Analyze submission]
"First, the clean case: Harbor Bakes. The sample is an email with a PDF application and an Excel sheet of values.
The verdict is 'Ready to quote', and all five rules pass.
Let me open an extracted field. [expand 'Total insured value'] Here the value is 3.4 million, and the evidence shows the exact line and which file it came from, the Excel sheet. [expand 'Year built'] And year built comes from the PDF.
The follow-up email says we have everything we need, so it doesn't ask the broker for anything."

## 4. Demo: outside appetite (3:20 - 4:20)  [Sample = 2_redline_pyrotech...; Analyze]
"Second case: Redline Pyrotech, a fireworks business. Here the data comes from a Word document and a CSV file.
The verdict is 'Outside appetite' because four rules fail, and each one shows why. The insured value of 14 million is over the 10 million limit. Fireworks are a prohibited operation. There are three losses where the limit is two. And the building is from 1974 with no sprinklers.
The date rule passes. [point to the summary] The underwriter summary lists exactly those failures. The follow-up email only asks about missing or conflicting information, so failed rules go to the underwriter instead."

## 5. Demo: conflicting and missing information (4:20 - 5:50)  [Sample = 3_meridian...; Analyze]  (the most important part)
"Third case, the one that tests judgement: Meridian Cold Storage.
Look at the insured value. [expand the field] The email says 8.2 million, but the Excel sheet says 12.5 million. The app doesn't pick one. It shows both, with the source of each, and marks it as a conflict.
Because of that, rule 1 says 'Needs info' instead of pass or fail. The loss history is not mentioned anywhere, so rule 3 also says 'Needs info'.
The start date is only six days away, so that rule does fail.
Now the draft email. [scroll down] It asks the broker which insured value is correct, naming both documents, and asks for the loss history. It asks for nothing else. The rule is: never guess, always ask."

## 6. Live test with my own data (5:50 - 6:50)  [Sample = (none); paste the Lakeside text; Analyze]
"To show this isn't hardcoded, I'll paste a new submission. Note the labels and formats are different: 'TIV', '4.2 million', 'none', and a written-out date.
It passes. The 1972 building passes rule 4 only because of the sprinklers. [delete the 'Sprinklers: full' line, click Analyze] Now with that line removed, the result changes to 'Hold for information' and the email asks about sprinklers.
[change it to 'Sprinklers: no', Analyze] And with 'no', it fails. The result changes with the data."

## 7. Tests (6:50 - 7:50)  [switch to the terminal; run `python -m pytest -q`]
"I wrote 28 automated tests, and they all pass.
They cover the three samples end to end with real PDF, Word, Excel and CSV files. They test every rule right at its boundary and one step past it, for example exactly 10 million passes and 10,000,001 fails, 14 days passes and 13 fails.
They test missing data, conflicting data, and a case where the same value appears twice and is correctly not a conflict.
They also test the LLM path with a simulated model: a real quote is accepted, a made-up quote is rejected, and a timeout or bad answer falls back safely. And they test that a corrupt file doesn't crash the app."

## 8. Limitations and wrap-up (7:50 - 8:40)  [show README.md]
"Here are the limits. The rule-based extractor needs lines like 'label: value', so unusual wording is where the LLM helps. Scanned PDFs are not read, because I didn't add OCR. I tested the live LLM connection with a fake server, but not with a real model. [Add anything else you didn't finish, for example: 'I didn't have time for X.']
The README has the setup steps, the design decisions, how to switch the LLM on, and how to add a new rule or field.
Thank you for watching. I'm happy to explain any part of the code."
