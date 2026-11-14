code_dir(
    edges={
        # The finders and timers each test starts as a subprocess.
        "test_penpa.py": ["./ubahn_finder.py:py"],
        "test_ubahn_battenberg_e2e.py": ["./brute.py:py", "./hybrid_finder.py:py"],
        "test_ubahn_hunt.py": ["./ubahn_finder.py:py"],
        "test_ubahn_brute.py": ["./hybrid_finder.py:py", "./ubahn_finder.py:py"],
        "test_ubahn_hybrid_e2e.py": [
            "./brute.py:py",
            "./hybrid_finder.py:py",
            "./time_engines.py:py",
            "./ubahn_finder.py:py",
        ],
        "test_ubahn_hybrid_links.py": ["./hybrid_finder.py:py"],
        # Reads the sources for an import of the command line.
        "test_ubahn_hybrid_searches.py": ["./hybrid_finder.py:py"],
        "test_ubahn_battenberg_hunt.py": ["./hybrid_finder.py:py"],
        "test_ubahn_fewest_markings.py": ["./hybrid_finder.py:py"],
        "test_ubahn_fewest_markings_e2e.py": ["./hybrid_finder.py:py"],
        "test_ubahn_hybrid_bananas.py": ["./hybrid_finder.py:py"],
        "test_ubahn_hybrid_hunt.py": ["./hybrid_finder.py:py"],
        "test_ubahn_hybrid_sat_hunt.py": ["./hybrid_finder.py:py"],
        "test_ubahn_number_circles_hunt.py": ["./hybrid_finder.py:py"],
        # Also: `render` is finders/hunt's, on its sys.path, not counting_shaded's.
        "hybrid_render.py": ["finders/hunt/render.py:py"],
        "test_ubahn_hybrid_render.py": ["./hybrid_finder.py:py"],
    }
)
