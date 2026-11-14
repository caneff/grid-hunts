# Tests that start a command as a subprocess.
code_dir(
    edges={
        "test_check.py": ["./check.py:py"],
        "test_hunt_9x9.py": ["./hunt.py:py"],
        "test_links.py": ["./hunt.py:py"],
        "test_opening.py": ["./check.py:py"],
        "test_spec_66_e2e.py": ["./check.py:py", "./hunt.py:py"],
        "test_spec_116_e2e.py": [
            "./check.py:py",
            "./hunt.py:py",
            "finders/halver_between/report.py:py",
            "finders/halver_lockout/check.py:py",
        ],
    }
)
