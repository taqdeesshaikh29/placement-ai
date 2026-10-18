"""Original sample interview questions, loaded once into an empty table."""
from app.extensions import db
from app.models import InterviewQuestion

TECHNICAL_CATEGORIES = ["Python", "SQL", "OOP", "DSA Fundamentals", "Web Development",
                        "Databases", "Software Engineering"]
HR_CATEGORIES = ["Self-introduction", "Strengths & Weaknesses", "Project Explanations",
                 "Teamwork", "Why Hire You"]

# (kind, category, difficulty, question, "concept|concept|...", sample answer)
SAMPLE_QUESTIONS = [
    # ------------------------------------------------------------ Technical: Python
    ("technical", "Python", "Easy", "What is the difference between a list and a tuple in Python?",
     "Mutability|Syntax: [] vs ()|Hashability|Typical use cases",
     "A list is mutable, so I can add, remove or change items after creating it. A tuple is immutable: once created, "
     "its contents cannot change. Because of that, a tuple of hashable items can be used as a dictionary key, "
     "while a list cannot. I use a list for a collection that grows or changes, such as a queue of tasks, and a "
     "tuple for a fixed record such as (latitude, longitude)."),
    ("technical", "Python", "Medium", "How does Python manage memory and garbage collection?",
     "Private heap|Reference counting|Cyclic garbage collector|Object lifetime",
     "Python keeps all objects in a private heap managed by the interpreter. Each object has a reference count that "
     "goes up when a new name points to it and down when a name is removed. When the count reaches zero, the memory "
     "is freed immediately. Reference counting cannot free objects that refer to each other in a cycle, so Python "
     "also runs a cyclic garbage collector that finds and cleans up unreachable cycles."),

    # ------------------------------------------------------------ Technical: SQL
    ("technical", "SQL", "Easy", "What is the difference between WHERE and HAVING?",
     "Row filtering vs group filtering|Order of execution|Aggregate functions",
     "WHERE filters individual rows before any grouping happens, so it cannot use aggregate functions. HAVING filters "
     "groups after GROUP BY has been applied, so it can use aggregates such as COUNT or AVG. For example, WHERE "
     "department = 'CSE' limits the rows first, and HAVING COUNT(*) > 5 then keeps only groups with more than five rows."),
    ("technical", "SQL", "Medium", "Explain the different types of SQL JOINs with an example.",
     "INNER JOIN|LEFT / RIGHT JOIN|FULL JOIN|Matching condition (ON)|NULLs for unmatched rows",
     "An INNER JOIN returns only rows that match in both tables. A LEFT JOIN returns every row from the left table and "
     "fills the right side with NULL when there is no match. A RIGHT JOIN is the mirror image, and a FULL JOIN returns "
     "all rows from both sides. For example, joining students to placements with LEFT JOIN lists every student, and "
     "students without a placement show NULL for the package."),

    # ------------------------------------------------------------ Technical: OOP
    ("technical", "OOP", "Easy", "What are the four pillars of object-oriented programming?",
     "Encapsulation|Abstraction|Inheritance|Polymorphism",
     "Encapsulation bundles data and the methods that work on it, and hides internal details. Abstraction exposes only "
     "what a user of the class needs. Inheritance lets a class reuse and extend another class. Polymorphism lets "
     "different classes respond to the same method call in their own way, such as different shapes each having their own area()."),
    ("technical", "OOP", "Medium", "What is the difference between method overloading and method overriding?",
     "Compile-time vs run-time polymorphism|Same class vs parent-child classes|Method signature",
     "Overloading means having several methods with the same name but different parameters in the same class. Which one "
     "runs is decided by the arguments. Overriding means a child class provides its own version of a method already "
     "defined in its parent class with the same signature, and the version used depends on the actual object at run time. "
     "Python does not support classic overloading, but supports overriding and default arguments."),

    # ------------------------------------------------------------ Technical: DSA
    ("technical", "DSA Fundamentals", "Easy", "Compare arrays and linked lists.",
     "Contiguous memory|Random access O(1)|Insertion / deletion cost|Memory overhead",
     "An array stores items in contiguous memory, so reading by index is O(1), but inserting or deleting in the middle "
     "means shifting elements, which is O(n). A linked list stores nodes connected by pointers, so inserting or deleting "
     "after a known node is O(1), but reaching the k-th item needs O(k) traversal and each node needs extra memory for the pointer. "
     "I choose arrays when I need fast lookup and linked lists when I need frequent insertions."),
    ("technical", "DSA Fundamentals", "Hard", "Explain the time complexity of quicksort and how to avoid its worst case.",
     "Divide and conquer|Pivot selection|Average O(n log n)|Worst case O(n²)|In-place",
     "Quicksort picks a pivot, partitions the array into smaller and larger elements, and sorts each part recursively. "
     "On average it takes O(n log n) time. The worst case is O(n²), which happens when the pivot is always the smallest "
     "or largest element, for example on already sorted input with a naive first-element pivot. We avoid it by choosing a random "
     "pivot or the median of three, and the algorithm sorts in place using O(log n) extra stack space on average."),

    # ------------------------------------------------------------ Technical: Web development
    ("technical", "Web Development", "Easy", "What is the difference between GET and POST requests?",
     "Idempotence|Data in URL vs body|Caching and bookmarking|Security considerations",
     "GET asks the server for data and sends parameters in the URL, so it should not change anything on the server. It can be "
     "cached and bookmarked. POST sends data in the request body and is used to create or change something, such as submitting "
     "a form. Sensitive data such as passwords should go in a POST body over HTTPS, never in a URL."),
    ("technical", "Web Development", "Medium", "How do cookies and sessions work together for user login?",
     "Stateless HTTP|Session ID cookie|Server-side session data|Cookie flags (HttpOnly, Secure)",
     "HTTP is stateless, so after a successful login the server creates a session and sends the browser a cookie with a "
     "session identifier. The browser returns the cookie on each request and the server uses it to recognise the user. "
     "To keep this safe, the cookie should be HttpOnly and Secure, the session should expire, and the identifier should "
     "be random and regenerated on login."),

    # ------------------------------------------------------------ Technical: Databases
    ("technical", "Databases", "Easy", "What is the difference between a primary key and a foreign key?",
     "Uniqueness|NOT NULL|Referential integrity|Relationships between tables",
     "A primary key uniquely identifies each row in its own table and cannot be NULL. A foreign key is a column that "
     "refers to the primary key of another table, which links the two tables and enforces referential integrity. "
     "For example, placements.student_id is a foreign key to students.id, so a placement cannot refer to a student that does not exist."),
    ("technical", "Databases", "Hard", "What is a database index, how does it speed up queries, and what does it cost?",
     "B-tree|Lookup vs full scan|Write overhead|Extra storage|Choosing columns to index",
     "An index is a separate structure, usually a B-tree, that keeps column values in sorted order with pointers to the rows. "
     "Instead of scanning the whole table, the database can search the index in O(log n) time. The cost is extra storage "
     "and slower INSERT, UPDATE and DELETE because the index must be maintained. So I index columns used often in WHERE, "
     "JOIN and ORDER BY clauses, and avoid indexing columns that change a lot or have very few distinct values."),

    # ------------------------------------------------------------ Technical: Software engineering
    ("technical", "Software Engineering", "Easy", "What is the difference between the Agile and Waterfall models?",
     "Iterative vs sequential|Handling changing requirements|Customer feedback|Delivery cadence",
     "Waterfall moves through fixed phases one after another: requirements, design, build, test, release. It suits projects "
     "with stable requirements. Agile delivers working software in short iterations, gathers feedback after each one and "
     "adapts the plan. It handles changing requirements better but needs close collaboration with the customer."),
    ("technical", "Software Engineering", "Hard", "What is technical debt and how would you manage it in a team?",
     "Short-term shortcuts|Code quality|Refactoring|Prioritisation|Tests and code review",
     "Technical debt is the future cost of choosing a quick solution now, such as skipping tests or duplicating code. "
     "It slows later changes, much like interest on a loan. I would make it visible by tracking it in the backlog, "
     "agree with the team how much capacity to spend on paying it down each sprint, and prevent new debt with code reviews, "
     "automated tests and clear coding standards. Debt in frequently changed code gets fixed first."),

    # ------------------------------------------------------------ HR: Self-introduction
    ("hr", "Self-introduction", "Easy", "Tell me about yourself.",
     "Present, past, future structure|Relevant skills|Education|Keep it under 90 seconds",
     "I'm [name], a final-year [branch] student at [college]. Over the last few years I've built a solid base in "
     "programming and databases, and I enjoy turning ideas into working projects. Recently I built [project], where I "
     "learned to [skill]. I'm now looking for a role where I can keep learning while contributing to real products, "
     "which is why this opportunity interests me."),
    ("hr", "Self-introduction", "Medium", "Walk me through your resume in two minutes.",
     "Chronological flow|Highlight achievements|Link experience to the role|Avoid reading line by line",
     "I'll start with my education in [branch], where I focused on [subjects]. In my second year I started [activity], "
     "which taught me [skill]. My main project is [project], in which I [what you did and the result]. I also completed "
     "[internship / course / certification]. Together these prepared me for an entry-level role in [area], which is what I'm applying for."),

    # ------------------------------------------------------------ HR: Strengths & weaknesses
    ("hr", "Strengths & Weaknesses", "Easy", "What are your key strengths?",
     "Relevant to the role|Back each with an example|Be specific, not generic",
     "My main strengths are problem solving and consistency. For example, when my team's project had a failing build "
     "before a demo, I traced the issue to a version conflict and fixed it that evening. I also practise a little every day, "
     "which is how I improved from [starting point] to [result] in [subject]."),
    ("hr", "Strengths & Weaknesses", "Medium", "What is your biggest weakness and how are you working on it?",
     "Honest and real weakness|Not a disguised strength|Concrete improvement steps|Progress made",
     "I used to hesitate to ask for help and would spend too long stuck on one problem. I noticed it slowed our team, "
     "so I set a rule: after 30 minutes of trying, I write down what I've tried and ask a teammate. This has made me "
     "faster and I now also help others do the same."),

    # ------------------------------------------------------------ HR: Project explanations
    ("hr", "Project Explanations", "Medium", "Describe a project you are proud of.",
     "Problem and users|Your role|Technologies and why|Result or impact|What you learned",
     "I'm proud of [project], a [type of app] that helps [users] to [goal]. I was responsible for [your part], using [tech] "
     "because [reason]. The result was [measurable outcome, e.g. reduced manual work or handled N users]. "
     "The biggest thing I learned was [lesson], and if I did it again I would [improvement]."),
    ("hr", "Project Explanations", "Hard", "Tell me about a technical challenge in your project and how you solved it.",
     "Clear problem statement|Steps you investigated|Decision and trade-offs|Outcome",
     "In [project], page loads became slow once the data grew. I measured the queries, found one without an index that "
     "scanned the whole table, and added an index and a limit on the results. Load time dropped from about [x] to [y]. "
     "I learned to measure first instead of guessing, and I now check query plans early."),

    # ------------------------------------------------------------ HR: Teamwork
    ("hr", "Teamwork", "Easy", "How do you contribute when working in a team?",
     "Communication|Reliability|Sharing knowledge|Supporting teammates",
     "I try to be clear and dependable. I agree on tasks and deadlines at the start, give regular updates and speak up early "
     "if I'm blocked. I also like sharing what I learn, for example by documenting setup steps, so the whole team moves faster."),
    ("hr", "Teamwork", "Hard", "Tell me about a time you disagreed with a teammate. How did you handle it?",
     "STAR method|Listening first|Focus on the goal, not the person|Resolution and learning",
     "In a group project, a teammate and I disagreed about the database design. I listened to their reasons first, then "
     "suggested we list the requirements and compare both options against them. It turned out their design handled one case "
     "better and mine was simpler for another, so we combined the ideas. We kept a good working relationship and I learned "
     "to settle disagreements with criteria instead of opinions."),

    # ------------------------------------------------------------ HR: Why hire you
    ("hr", "Why Hire You", "Medium", "Why should we hire you?",
     "Match skills to the job description|Evidence and examples|Attitude to learning|Company research",
     "You need someone who can contribute quickly and keep growing. I have a solid foundation in [skills required], "
     "shown by [project or result], and I learn new tools fast. I also work well in teams and take ownership of my tasks. "
     "From what I've read about [company], your work on [area] is exactly where I want to build my career."),
    ("hr", "Why Hire You", "Hard", "How are you different from other candidates with similar grades?",
     "Unique experience|Evidence beyond marks|Initiative|Be confident, not arrogant",
     "Marks show that I understand the subjects, and what I add is practical experience. Beyond coursework I built [project], "
     "[contributed to / organised something], and practised [skill] regularly. These show initiative and the ability to "
     "finish things, which I believe matters in a real team."),
]


def seed_interview_questions():
    """Insert the sample questions if the table is empty."""
    if InterviewQuestion.query.first():
        return
    for kind, category, difficulty, text, concepts, sample in SAMPLE_QUESTIONS:
        db.session.add(InterviewQuestion(kind=kind, category=category, difficulty=difficulty,
                                         text=text, key_concepts=concepts, sample_answer=sample))
    db.session.commit()
