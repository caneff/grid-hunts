# The one shape of a code directory's BUILD file: `code_dir(...)`, its Python
# and its data. Pants infers the imports; what no import shows is passed here.
#
# Every Python file of the directory depends on the directory's data: the
# fixtures, boards, links and C sources under it, at any depth, and the BUILD
# file itself. A change to one selects every suite in the directory and every
# suite that reads code from it, which is coarse on purpose: a suite reads its
# fixtures by path, and a BUILD change can move any edge.
#
#   edges   {python file: [target addresses]}: what the file reads or starts
#           that no import shows, a script run as a subprocess above all.
#           tests/test_pants_edges.py fails on a `.py` file a source names
#           in a string and does not reach.


def code_dir(edges=None):
    python_sources(
        name="py",
        sources=["*.py"],
        dependencies=[":data"],
        overrides={
            file: {"dependencies": [":data", *deps]}
            for file, deps in (edges or {}).items()
        },
    )
    files(name="data", sources=["**/*", "!**/*.py", "!**/*.md"])
