import json
S = "/tmp/claude-1000/-home-caneff-src-grid-hunts/3702cf19-92f5-4309-b53e-71ca692fbe21/scratchpad/"
J = "/home/caneff/.cache/agent-jobs/"
def found(job, n):
    L = open(job if job.startswith("/") else J + job + "/progress").read().splitlines()
    i = next(k for k, l in enumerate(L) if l.endswith(f"FOUND {n}"))
    g = lambda j, t: L[i + j].split(t, 1)[1].split()
    out = {a: int(b) for a, b in (s.split("=") for s in g(3, "outside"))}
    return dict(REG=g(1, "regions"), DIG=g(2, "digits"), OUT=out, GRIDC=[t for t in g(4, "circles") if t[-1] not in "LRTB"])
D = [tuple(x) for x in json.load(open(S + "newrooms_list.json"))]
src = open(S + "runrooms.html").read()
head = src[:src.index("<main>")].replace("<title>Run Rooms Drafts</title>", "<title>New Rooms Drafts</title>")
js = src[src.index("const S = 50"):src.index("const D4 =")]
body = ['<main>', '  <h1>New Rooms drafts</h1>',
 '  <p><b>Rule:</b> Let N be the first digit looking in from a circled outside cell. Cells 1 to N share one region, and cell N+1, if it exists, is in a different region. The clue is the Nth digit. Counting circles apply inside and outside the grid.</p>',
 '  <p>Every draft: 36 circles, full top side circled, r1L circled, r2L not, outside values one 1 (except the 10-clue drafts) plus ten from 5–8. Unique by the hunt model; rules re-checked in plain Python. Not test-solved.</p>']
data = []
for id_, title, job, n, link, note in D:
    d = found(job, n); data.append((id_, d))
    body += [f'  <h2 style="margin:0;font-size:20px">{title}</h2>',
             f'  <p>{len(d["OUT"])} outside, {len(d["GRIDC"])} inside. {note} SudokuMaker: sudokumaker.app/p/{link}</p>',
             '  <div class="row">',
             f'    <figure><div id="puz{id_}"></div><figcaption>Puzzle: circles only.</figcaption></figure>',
             f'    <figure><div id="sol{id_}"></div><figcaption>Solution: regions shaded, outside clue values in blue.</figcaption></figure>',
             '  </div>']
body.append('</main>')
script = "<script>\n" + js + "const DR = " + json.dumps({i: d for i, d in data}) + ";\nfor (const [id,d] of Object.entries(DR)) {\n  document.getElementById('puz'+id).innerHTML=draw(false,d.REG,d.DIG,d.OUT,d.GRIDC);\n  document.getElementById('sol'+id).innerHTML=draw(true,d.REG,d.DIG,d.OUT,d.GRIDC); }\n</script>\n</body>\n</html>\n"
open(S + "newrooms.html", "w").write(head + "\n".join(body) + "\n" + script)
print({i: len(d["OUT"]) + len(d["GRIDC"]) for i, d in data})
