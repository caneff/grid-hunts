"""SCRATCH: tiling feasibility of the known 10-outside jigsaw grids under stricter shape rules (no straight region).
sky7Jcxk.py <per_s>"""
import sys, time, importlib.util
args = sys.argv; spec = importlib.util.spec_from_file_location("t", args[0].replace("sky7Jcxk.py", "sky7J2s.py"))
sys.argv = [args[0].replace("sky7Jcxk.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N = T.cp_model, T.cells, T.N
PER = float(args[1])
GR = {"jig1": "234167895345216789456392178513489267728543916869754321172938654987621543691875432",
      "jig2": "345791268426983175659874321798165432987612543134527689213456897572348916861239754",
      "jng1": "345621789476912358529843167698754231213467895134578926752389614861295473987136542",
      "jng2": "745391268426983175659874321398765412987612543134527689213456897572148936861239754",
      "jng4": "345621789452913678569834217698745321214567893123478956736289145871392564987156432",
      "jng5": "487592163716983254569874321698715432345621789234167895123458976852349617971236548",
      "jng6": "754293168216984375639875421498716532987651243345162789123547896562438917871329654",
      "jng7": "751289643862395174123478965234517896987164532498756321619843257576932418345621789",
      "jng8": "546193278712984365369875421498761532987652143125346789234517896653428917871239654",
      "jng9": "145793268436982175659874321798165432987621543324516789213457896562348917871239654"}
for name, g in GR.items():
    G = {(r, c): int(g[r * 9 + c]) for r in range(N) for c in range(N)}; row = []
    for ml, sp in ((6, 2), (5, 2), (5, 3), (4, 3)):
        t0 = time.time(); m, reg = T.region_model(G, maxdeg=0, maxline=ml, span=True, span_min=sp, nobox=False, asym=False)
        s = T.solver(PER); st = s.Solve(m); row.append(f"line<={ml} span>={sp}: {s.StatusName(st)} {time.time()-t0:.0f}s")
        if st == cp_model.INFEASIBLE: break
    print(name, "| " + "; ".join(row), flush=True)
