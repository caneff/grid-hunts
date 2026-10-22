code_dir(
    edges={
        # The finders and timers each test starts as a subprocess.
        "test_penpa.py": ["./ubahn_finder.py:py"],
        "test_ubahn_battenberg_e2e.py": ["./brute.py:py", "./hybrid_finder.py:py"],
        "test_ubahn_hunt.py": ["./ubahn_finder.py:py"],
        "test_ubahn_hybrid_e2e.py": [
            "./brute.py:py",
            "./hybrid_finder.py:py",
            "./time_engines.py:py",
            "./ubahn_finder.py:py",
        ],
        "test_ubahn_hybrid_links.py": ["./hybrid_finder.py:py"],
        # Also: `render` is finders/hunt's, on its sys.path, not counting_shaded's.
        "hybrid_render.py": ["finders/hunt/render.py:py"],
        "test_ubahn_hybrid_render.py": ["./hybrid_finder.py:py"],
    }
)
