# tasks.py

TASKS = {
    "easy": {
        "title": "Fix simple typo in helper function",
        "description": "Please review this PR. I added a new math helper.",
        "files": {
            "math_helpers.py": "1: def add_numbers(a, b):\n2:     retun a + b  # Typo here\n3: "
        },
        "bug_file": "math_helpers.py",
        "bug_line": 2,
        "should_approve": False
    },
    "medium": {
        "title": "Add Database Config",
        "description": "Adding the db connection strings for production.",
        "files": {
            "config.py": "1: import os\n2: \n3: DB_HOST = 'prod.db.local'\n4: DB_PASSWORD = 'super_secret_password_123'  # Hardcoded secret!\n5: DB_USER = 'admin'"
        },
        "bug_file": "config.py",
        "bug_line": 4,
        "should_approve": False
    },
    "hard": {
        "title": "User login feature",
        "description": "Added the login endpoint. PTAL.",
        "files": {
            "auth.py": "1: from db import execute\n2: \n3: def login(username, password):\n4:     query = f\"SELECT * FROM users WHERE user='{username}' AND pass='{password}'\"\n5:     return execute(query)  # SQL Injection vulnerability!"
        },
        "bug_file": "auth.py",
        "bug_line": 4,
        "should_approve": False
    },
    "expert": {
        "title": "Add average calculation utility",
        "description": "Implemented a quick helper to calculate the mean of a list. Please review.",
        "files": {
            "stats.py": "1: def calculate_average(numbers):\n2:     if not numbers:\n3:         return 0.0\n4:     total = sum(numbers)\n5:     return total / (len(numbers) - 1)  # Logic Error: should be divided by len(numbers)"
        },
        "bug_file": "stats.py",
        "bug_line": 5,
        "should_approve": False
    }
}