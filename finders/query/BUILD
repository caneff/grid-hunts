# query.py loads a finder's query_finder.py by path, and imports `render`
# through finders/hunt on its sys.path (counting_shaded has a module of the
# same name); test_query.py starts the toy finder as a subprocess argument.
code_dir(
    edges={
        "query.py": [
            "finders/hunt/render.py:py",
            "finders/halver_between/query_finder.py:py",
            "finders/halver_lockout/query_finder.py:py",
        ],
        "test_query.py": ["./toy_finder.py:py"],
    }
)
