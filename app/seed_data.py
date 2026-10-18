"""Original sample aptitude questions, loaded once into an empty questions table."""
from app.extensions import db
from app.models import Question

QUANT = "Quantitative Aptitude"
LOGIC = "Logical Reasoning"
VERBAL = "Verbal Ability"

# (category, difficulty, text, [4 options], correct option 1-4, explanation)
SAMPLE_QUESTIONS = [
    # ---- Quantitative Aptitude ----
    (QUANT, "Easy", "A shirt costs ₹800 and is sold at a 25% discount. What is the selling price?",
     ["₹500", "₹600", "₹650", "₹700"], 2,
     "Discount = 25% of 800 = ₹200, so the selling price is 800 − 200 = ₹600."),
    (QUANT, "Easy", "What is the average of 12, 18, 24 and 30?",
     ["19", "20", "21", "22"], 3,
     "Sum = 84; 84 ÷ 4 = 21."),
    (QUANT, "Easy", "If 6 pens cost ₹90, how much do 10 pens cost at the same rate?",
     ["₹120", "₹135", "₹150", "₹180"], 3,
     "One pen costs 90 ÷ 6 = ₹15, so 10 pens cost ₹150."),
    (QUANT, "Medium", "A train 150 m long passes a pole in 10 seconds. What is its speed in km/h?",
     ["45", "54", "60", "72"], 2,
     "Speed = 150/10 = 15 m/s. Multiply by 18/5 to convert: 15 × 3.6 = 54 km/h."),
    (QUANT, "Medium", "The ratio of boys to girls in a class is 3:2. If there are 30 students, how many are girls?",
     ["10", "12", "15", "18"], 2,
     "Girls = 2/5 of 30 = 12."),
    (QUANT, "Medium", "A can finish a job in 12 days and B in 6 days. Working together, how many days do they need?",
     ["3", "4", "5", "9"], 2,
     "Combined rate = 1/12 + 1/6 = 3/12 = 1/4 of the job per day, so they need 4 days."),
    (QUANT, "Hard", "A sum of money doubles itself in 5 years at simple interest. In how many years will it become four times?",
     ["10", "15", "20", "25"], 2,
     "Doubling means the interest equals the principal in 5 years. Becoming four times needs interest of 3× the principal, i.e. 3 × 5 = 15 years."),
    (QUANT, "Hard", "The compound interest on ₹10,000 at 10% per annum for 2 years, compounded annually, is:",
     ["₹2,000", "₹2,100", "₹2,200", "₹2,400"], 2,
     "Amount = 10,000 × 1.1 × 1.1 = ₹12,100, so the compound interest is ₹2,100."),
    (QUANT, "Hard", "How many different 3-letter arrangements can be made from the letters A, B, C, D, E with no letter repeated?",
     ["10", "30", "60", "125"], 3,
     "5 × 4 × 3 = 60 ordered arrangements."),

    # ---- Logical Reasoning ----
    (LOGIC, "Easy", "Find the next number in the series: 3, 6, 12, 24, ?",
     ["30", "36", "42", "48"], 4,
     "Each term is double the previous one, so the next is 24 × 2 = 48."),
    (LOGIC, "Easy", "Which word does not belong with the others: Apple, Mango, Carrot, Banana?",
     ["Apple", "Mango", "Carrot", "Banana"], 3,
     "Apple, Mango and Banana are fruits; a carrot is a vegetable."),
    (LOGIC, "Easy", "If CAT is written as DBU, how is DOG written in the same code?",
     ["EPH", "EOH", "DPH", "FPH"], 1,
     "Each letter moves one place forward: D→E, O→P, G→H, giving EPH."),
    (LOGIC, "Medium", "Pointing to a man, Rita says, \"He is the son of my mother's only brother.\" How is the man related to Rita?",
     ["Brother", "Cousin", "Uncle", "Nephew"], 2,
     "Rita's mother's only brother is Rita's maternal uncle; his son is Rita's cousin."),
    (LOGIC, "Medium", "Find the missing term: 2, 5, 10, 17, 26, ?",
     ["35", "36", "37", "38"], 3,
     "The terms are n² + 1 (1+1 is skipped): 2, 5, 10, 17, 26, 37. The differences 3, 5, 7, 9, 11 confirm 26 + 11 = 37."),
    (LOGIC, "Medium", "All roses are flowers. Some flowers fade quickly. Which conclusion must be true?",
     ["All flowers are roses", "Some roses fade quickly", "All roses are flowers", "No rose fades quickly"], 3,
     "Only the first statement is guaranteed: every rose is a flower. We cannot conclude anything about roses fading."),
    (LOGIC, "Hard", "Five friends A, B, C, D and E sit in a row. A is left of B, C is right of B, and D is at the extreme left. Who could be at the extreme right?",
     ["A", "B", "D", "C or E"], 4,
     "D is leftmost. A must be left of B and B left of C, so A, B, C appear in that order. E can be placed anywhere after D, so the right end can be C or E; A and B cannot be last because C is right of B."),
    (LOGIC, "Hard", "If the day before yesterday was Thursday, what day will it be the day after tomorrow?",
     ["Sunday", "Monday", "Tuesday", "Wednesday"], 2,
     "The day before yesterday was Thursday, so today is Saturday. The day after tomorrow is Monday."),
    (LOGIC, "Hard", "In a certain code, 'sky is blue' is 'ka mo ti' and 'blue is deep' is 'mo ti ru'. What is the code for 'sky'?",
     ["ka", "mo", "ti", "ru"], 1,
     "'is blue' is common to both and maps to 'mo ti'. In the first sentence the leftover word 'sky' matches the leftover code 'ka'."),

    # ---- Verbal Ability ----
    (VERBAL, "Easy", "Choose the synonym of 'RAPID'.",
     ["Slow", "Quick", "Late", "Weak"], 2,
     "Rapid means moving at great speed, the same as quick."),
    (VERBAL, "Easy", "Choose the antonym of 'ANCIENT'.",
     ["Old", "Modern", "Historic", "Aged"], 2,
     "Ancient means very old; the opposite is modern."),
    (VERBAL, "Easy", "Fill in the blank: She ____ to school every day.",
     ["go", "going", "goes", "gone"], 3,
     "The subject 'She' is third person singular, so the verb takes -es: goes."),
    (VERBAL, "Medium", "Choose the correctly spelt word.",
     ["Accomodate", "Acommodate", "Accommodate", "Acomodate"], 3,
     "Accommodate is spelt with double c and double m."),
    (VERBAL, "Medium", "Choose the word that best completes the sentence: The manager's ____ decision surprised everyone, as nobody had expected it.",
     ["predictable", "sudden", "routine", "gradual"], 2,
     "Surprising and unexpected points to 'sudden'. The other options suggest something foreseen or slow."),
    (VERBAL, "Medium", "Identify the part of the sentence with an error: 'Neither of the students (A) have (B) submitted (C) the assignment (D).'",
     ["A", "B", "C", "D"], 2,
     "'Neither' is singular, so it needs 'has', not 'have'."),
    (VERBAL, "Hard", "Choose the meaning of the idiom 'to burn the midnight oil'.",
     ["To waste resources", "To work late into the night", "To start a fire", "To avoid responsibility"], 2,
     "The idiom means to work or study late at night."),
    (VERBAL, "Hard", "Choose the option that is closest in meaning to 'EPHEMERAL'.",
     ["Everlasting", "Short-lived", "Valuable", "Hidden"], 2,
     "Ephemeral describes something that lasts only a very short time."),
    (VERBAL, "Hard", "Rearrange to form a meaningful sentence: P. the committee  Q. approved  R. the proposal  S. unanimously",
     ["PQRS", "PSQR", "PRQS", "QPRS"], 2,
     "'The committee unanimously approved the proposal' reads correctly: P S Q R."),
]


def seed_questions():
    """Insert the sample questions if the table is empty."""
    if Question.query.first():
        return
    for category, difficulty, text, options, correct, explanation in SAMPLE_QUESTIONS:
        db.session.add(Question(
            category=category, difficulty=difficulty, text=text,
            option_1=options[0], option_2=options[1], option_3=options[2], option_4=options[3],
            correct_option=correct, explanation=explanation,
        ))
    db.session.commit()
