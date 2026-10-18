"""Predefined Python practice questions.

Answers are checked by comparing text to the accepted answers. No student code is ever
executed. Question types:
  output - read `code` and type what it prints
  fill   - replace ___ in `code` so the program prints `expected_output`
  choice - pick one of `options` (accepted = [index of the right option])
"""

TOPICS = ["Variables", "Data types", "Conditions", "Loops", "Functions", "Strings", "Lists", "Dictionaries"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
POINTS = {"Easy": 10, "Medium": 20, "Hard": 30}


def _q(qid, topic, difficulty, title, kind, description, hint, explanation, accepted,
       example_code, example_output, code=None, expected_output=None, options=None, solution=None):
    return {
        "id": qid, "topic": topic, "difficulty": difficulty, "title": title, "type": kind,
        "description": description, "code": code, "options": options,
        "expected_output": expected_output, "accepted": accepted,
        "example_code": example_code, "example_output": example_output,
        "hint": hint, "explanation": explanation, "solution": solution,
    }


QUESTIONS = [
    # ------------------------------------------------------------ Variables
    _q(1, "Variables", "Easy", "Reassigning a variable", "output",
       "What does this program print?",
       "Work line by line. The right side of x = x + y is evaluated using the current values.",
       "x starts at 5, then x = x + y becomes 5 + 3 = 8. The new value replaces the old one.",
       ["8"],
       "n = 10\nn = n - 4\nprint(n)", "6",
       code="x = 5\ny = 3\nx = x + y\nprint(x)"),
    _q(2, "Variables", "Medium", "Swap two variables", "fill",
       "Fill in the blank so the values of a and b are swapped and the program prints the output shown.",
       "Python lets you assign several variables in one line: x, y = y, x.",
       "Tuple unpacking evaluates the right side first (7 and 2 swapped), then assigns both names at once, "
       "so no temporary variable is needed.",
       ["b, a"],
       "x, y = 1, 5\nx, y = y, x\nprint(x, y)", "5 1",
       code="a = 7\nb = 2\na, b = ___\nprint(a, b)", expected_output="2 7",
       solution="a, b = b, a"),
    _q(3, "Variables", "Hard", "Two names, one list", "output",
       "What does this program print?",
       "b = a does not copy the list. Both names point to the same object.",
       "Assignment copies the reference, not the list. b.append(3) changes the one shared list, "
       "so printing a shows the new item too. Use a.copy() to make an independent copy.",
       ["[1, 2, 3]"],
       "x = [5]\ny = x\ny.append(6)\nprint(len(x))", "2",
       code="a = [1, 2]\nb = a\nb.append(3)\nprint(a)"),

    # ------------------------------------------------------------ Data types
    _q(4, "Data types", "Easy", "Type of a number", "choice",
       "What is the type of the value 3.0 in Python?",
       "Look at the decimal point.",
       "Any number written with a decimal point is a float, even if the fractional part is zero.",
       [1],
       "print(type(7))", "<class 'int'>",
       options=["int", "float", "str", "bool"]),
    _q(5, "Data types", "Medium", "Division operators", "output",
       "What does this program print?",
       "// is floor division, % is the remainder and / always gives a float.",
       "7 // 2 is 3 (floor division), 7 % 2 is 1 (remainder) and 7 / 2 is 3.5 (true division). "
       "print separates the values with spaces.",
       ["3 1 3.5"],
       "print(9 // 4, 9 % 4)", "2 1",
       code="print(7 // 2, 7 % 2, 7 / 2)"),
    _q(6, "Data types", "Hard", "Truthy and falsy", "choice",
       "Which of these expressions evaluates to True?",
       "Only empty or zero-like values are falsy. Remember that \"0\" is a string.",
       "bool(0), bool(\"\") and bool([]) are False because 0 and empty containers are falsy. "
       "bool(\"0\") is True because a non-empty string is truthy, whatever it contains.",
       [2],
       "print(bool(\"\"), bool(\" \"))", "False True",
       options=["bool(0)", "bool(\"\")", "bool(\"0\")", "bool([])"]),

    # ------------------------------------------------------------ Conditions
    _q(7, "Conditions", "Easy", "If / else", "output",
       "What does this program print?",
       "Check whether age >= 18 is true for age = 17.",
       "17 is not greater than or equal to 18, so the if branch is skipped and the else branch runs.",
       ["minor"],
       "temp = 30\nif temp > 25:\n    print(\"hot\")\nelse:\n    print(\"cool\")", "hot",
       code="age = 17\nif age >= 18:\n    print(\"adult\")\nelse:\n    print(\"minor\")"),
    _q(8, "Conditions", "Medium", "Grade boundaries", "fill",
       "Students scoring 60 or more (but less than 90) get grade B. Fill in the blank with the correct "
       "number so the program prints B.",
       "The elif only runs when the first condition failed, so you only need the lower limit.",
       "Marks of 72 fail the first test (>= 90), so Python checks the elif. 72 >= 60 is true, so grade is \"B\".",
       ["60"],
       "score = 45\nif score >= 50:\n    print(\"pass\")\nelif score >= 40:\n    print(\"retry\")\nelse:\n    print(\"fail\")",
       "retry",
       code="marks = 72\nif marks >= 90:\n    grade = \"A\"\nelif marks >= ___:\n    grade = \"B\"\nelse:\n    grade = \"C\"\nprint(grade)",
       expected_output="B", solution="elif marks >= 60:"),
    _q(9, "Conditions", "Hard", "Combining conditions", "output",
       "What does this program print?",
       "Evaluate each comparison separately, then apply and / or / not. Print shows the three results.",
       "x > 3 and x < 10 is True. x > 3 and not x < 10 is True and False, giving False. "
       "x < 3 or x == 5 is False or True, giving True.",
       ["True False True"],
       "y = 4\nprint(y > 1 and y < 3)", "False",
       code="x = 5\nprint(x > 3 and x < 10, x > 3 and not x < 10, x < 3 or x == 5)"),

    # ------------------------------------------------------------ Loops
    _q(10, "Loops", "Easy", "range() basics", "output",
       "What does this program print? Write each printed line on its own line.",
       "range(3) produces 0, 1, 2 (it stops before 3).",
       "range(3) starts at 0 and stops before 3, so the loop prints 0, 1 and 2, one per line.",
       ["0\n1\n2"],
       "for i in range(1, 4):\n    print(i * 2)", "2\n4\n6",
       code="for i in range(3):\n    print(i)"),
    _q(11, "Loops", "Medium", "Running total", "output",
       "What does this program print?",
       "range(1, 6) gives 1, 2, 3, 4, 5. Add them up.",
       "The loop adds 1 + 2 + 3 + 4 + 5 to total, which equals 15.",
       ["15"],
       "total = 0\nfor n in range(1, 4):\n    total += n\nprint(total)", "6",
       code="total = 0\nfor n in range(1, 6):\n    total += n\nprint(total)"),
    _q(12, "Loops", "Hard", "While with continue", "output",
       "What does this program print?",
       "Trace i and count each time through the loop. continue skips the rest of that pass.",
       "i goes 3 (count 1), 6 (skipped by continue), 9 (count 2), 12 (count 3). "
       "Then 12 < 10 is false and the loop ends, so it prints 3 12.",
       ["3 12"],
       "i = 0\nwhile i < 3:\n    i += 1\nprint(i)", "3",
       code="count = 0\ni = 0\nwhile i < 10:\n    i += 3\n    if i == 6:\n        continue\n    count += 1\nprint(count, i)"),

    # ------------------------------------------------------------ Functions
    _q(13, "Functions", "Easy", "Return a square", "fill",
       "Complete the function so it returns the square of n. The program should print 16.",
       "The square of n is n multiplied by itself.",
       "return sends a value back to the caller. n * n (or n ** 2) is 4 * 4 = 16 for the call square(4).",
       ["n * n", "n ** 2"],
       "def double(n):\n    return n * 2\n\nprint(double(5))", "10",
       code="def square(n):\n    return ___\n\nprint(square(4))", expected_output="16",
       solution="return n * n"),
    _q(14, "Functions", "Medium", "Default arguments", "output",
       "What does this program print? Write each printed line on its own line.",
       "If you do not pass the second argument, the default value is used.",
       "greet(\"Asha\") uses the default greeting \"Hello\". greet(\"Ravi\", \"Hi\") replaces it with \"Hi\".",
       ["Hello, Asha\nHi, Ravi"],
       "def add(a, b=10):\n    return a + b\n\nprint(add(1))", "11",
       code="def greet(name, greeting=\"Hello\"):\n    return greeting + \", \" + name\n\nprint(greet(\"Asha\"))\nprint(greet(\"Ravi\", \"Hi\"))"),
    _q(15, "Functions", "Hard", "Mutable default argument", "output",
       "What does this program print?",
       "The default list is created once, when the function is defined, not on every call.",
       "box=[] is evaluated only once, so every call that omits box shares the same list. "
       "The first call adds 1 and the second adds 2 to that same list. A safer pattern is box=None, then create the list inside the function.",
       ["[1, 2]"],
       "def f(x, items=[]):\n    items.append(x)\n    return len(items)\n\nf(\"a\")\nprint(f(\"b\"))", "2",
       code="def add_item(item, box=[]):\n    box.append(item)\n    return box\n\nadd_item(1)\nprint(add_item(2))"),

    # ------------------------------------------------------------ Strings
    _q(16, "Strings", "Easy", "Indexing a string", "output",
       "What does this program print?",
       "Index 0 is the first character and -1 is the last. len() counts the characters.",
       "\"python\" has 6 characters: s[0] is \"p\", s[-1] is \"n\" and len(s) is 6.",
       ["p n 6"],
       "s = \"code\"\nprint(s[0], s[-1], len(s))", "c e 4",
       code="s = \"python\"\nprint(s[0], s[-1], len(s))"),
    _q(17, "Strings", "Medium", "String methods", "fill",
       "Fill in the blank with a method name so the program prints the word in capital letters.",
       "The method that converts text to capitals is spelled like the opposite of lower.",
       "str.upper() returns a new string with every letter in uppercase. Strings are immutable, so the original is unchanged.",
       ["upper"],
       "print(\"Hello\".lower())", "hello",
       code="word = \"placement\"\nprint(word.___())", expected_output="PLACEMENT",
       solution="print(word.upper())"),
    _q(18, "Strings", "Hard", "Split and join", "output",
       "What does this program print?",
       "Splitting on \",\" keeps empty strings between consecutive commas.",
       "\"a,b,,c\".split(\",\") gives ['a', 'b', '', 'c']: 4 parts, and parts[2] is the empty string. "
       "Joining them with \"-\" gives a-b--c.",
       ["4 True a-b--c"],
       "print(\"1-2-3\".split(\"-\"))", "['1', '2', '3']",
       code="s = \"a,b,,c\"\nparts = s.split(\",\")\nprint(len(parts), parts[2] == \"\", \"-\".join(parts))"),

    # ------------------------------------------------------------ Lists
    _q(19, "Lists", "Easy", "Appending to a list", "output",
       "What does this program print?",
       "append adds one item at the end of the list.",
       "append(16) adds 16 to the end, so the list becomes [4, 8, 15, 16].",
       ["[4, 8, 15, 16]"],
       "items = [1]\nitems.append(2)\nprint(len(items))", "2",
       code="nums = [4, 8, 15]\nnums.append(16)\nprint(nums)"),
    _q(20, "Lists", "Medium", "Sort and slice", "output",
       "What does this program print?",
       "sort() changes the list in place. nums[:2] is the first two items.",
       "After sorting, nums is [1, 3, 5, 9]. nums[:2] is [1, 3] and nums[-1] is the last item, 9.",
       ["[1, 3] 9"],
       "print([10, 20, 30, 40][1:3])", "[20, 30]",
       code="nums = [5, 3, 9, 1]\nnums.sort()\nprint(nums[:2], nums[-1])"),
    _q(21, "Lists", "Hard", "List comprehension", "fill",
       "Fill in the blank with a condition so the list comprehension keeps only the even numbers.",
       "A number is even when its remainder after dividing by 2 is 0.",
       "A comprehension [n for n in nums if condition] keeps items for which the condition is true. "
       "n % 2 == 0 is true for 2, 4 and 6.",
       ["n % 2 == 0", "not n % 2"],
       "squares = [n * n for n in [1, 2, 3]]\nprint(squares)", "[1, 4, 9]",
       code="nums = [1, 2, 3, 4, 5, 6]\nevens = [n for n in nums if ___]\nprint(evens)",
       expected_output="[2, 4, 6]", solution="evens = [n for n in nums if n % 2 == 0]"),

    # ------------------------------------------------------------ Dictionaries
    _q(22, "Dictionaries", "Easy", "Looking up a key", "output",
       "What does this program print?",
       "d[\"b\"] returns the value stored under the key \"b\".",
       "A dictionary maps keys to values. The key \"b\" maps to 2.",
       ["2"],
       "marks = {\"math\": 90}\nprint(marks[\"math\"])", "90",
       code="d = {\"a\": 1, \"b\": 2}\nprint(d[\"b\"])"),
    _q(23, "Dictionaries", "Medium", "Updating a dictionary", "output",
       "What does this program print? (Dictionaries print with curly braces and quotes around string keys.)",
       "+= changes an existing value; assigning to a new key adds it.",
       "stock[\"pen\"] becomes 5 + 3 = 8, and assigning to the new key \"book\" adds it at the end.",
       ["{'pen': 8, 'book': 2}"],
       "d = {}\nd[\"k\"] = 1\nprint(d)", "{'k': 1}",
       code="stock = {\"pen\": 5}\nstock[\"pen\"] += 3\nstock[\"book\"] = 2\nprint(stock)"),
    _q(24, "Dictionaries", "Hard", "Counting with get()", "output",
       "What does this program print?",
       "counts.get(ch, 0) returns 0 when the letter has not been seen yet. Keys keep the order they were first added.",
       "The loop builds a letter count: b appears once, a three times and n twice. "
       "Dictionaries preserve insertion order, so the keys appear as b, a, n.",
       ["{'b': 1, 'a': 3, 'n': 2}"],
       "counts = {}\nfor ch in \"aab\":\n    counts[ch] = counts.get(ch, 0) + 1\nprint(counts)", "{'a': 2, 'b': 1}",
       code="text = \"banana\"\ncounts = {}\nfor ch in text:\n    counts[ch] = counts.get(ch, 0) + 1\nprint(counts)"),
]

_BY_ID = {q["id"]: q for q in QUESTIONS}


def get_question(qid):
    return _BY_ID.get(qid)


def _norm_lines(text):
    lines = [line.strip() for line in text.strip().splitlines()]
    return "\n".join(lines).replace('"', "'")


def _norm_loose(text):
    return "".join(text.split()).replace('"', "'")


def check_answer(q, answer):
    """Compare a submitted answer to the accepted answers. Never evaluates the answer."""
    if q["type"] == "choice":
        return answer in q["accepted"]
    if q["type"] == "output":
        return any(_norm_lines(answer) == _norm_lines(a) for a in q["accepted"])
    return any(_norm_loose(answer) == _norm_loose(a) for a in q["accepted"])  # fill


def solution_text(q):
    """What is revealed after submission."""
    if q["type"] == "choice":
        return q["options"][q["accepted"][0]]
    if q["type"] == "output":
        return q["accepted"][0]
    return q["solution"] or q["accepted"][0]
