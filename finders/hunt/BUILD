# The toy finders each test starts as a subprocess.
code_dir(
    edges={
        "test_finder_config.py": ["./toy_config_finder.py:py"],
        "test_hunt_verify.py": ["./toy_finder.py:py", "./toy_stateful_finder.py:py"],
        "test_render_dir.py": ["./toy_finder.py:py", "./toy_render_finder.py:py"],
        "test_summary_links.py": [
            "./toy_finder.py:py",
            "./toy_summary_finder.py:py",
        ],
        "test_toy_hunt.py": ["./toy_finder.py:py", "./toy_slow_finder.py:py"],
        # Spec #118's end-to-end test starts or loads these in fresh processes.
        "test_spec_118_e2e.py": [
            "//finders/counting_shaded/connected.py:py",
            "//finders/counting_shaded/fastclimb.py:py",
            "//finders/halver/halver_brute_c.py:py",
            "//finders/qqrr/hunt/hunt_common.py:py",
            "//finders/qqrr/hunt/tie_finder.py:py",
        ],
    }
)
