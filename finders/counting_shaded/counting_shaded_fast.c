// Hot loop of the counting shaded all-visible shape climb, in C (loaded via ctypes).
//
//   gcc -O2 -shared -fPIC -o counting_shaded_fast.so counting_shaded_fast.c -lm
//
// Same rules as shapes.py: a shaded cell's given is its shaded-neighbour count
// (1-8), givens are distinct within every row, column and box, and the shaded cells
// form one orthogonally connected region. gf_require_eight(1) also demands a
// given of 8; gf_set_pins forces cells on or off. gf_count counts sudoku solutions of a shape's givens up to a cap;
// gf_enumerate lists every connected shape of one size; gf_climb anneals on log solutions (temperature t_hi -> t_lo over the run; a
// move toggles a short king-walk of 1..max_toggles cells) and returns the best
// shape found.
#include <math.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

static int NB[81][8], NBN[81], ORTH[81][4], ORTHN[81], ROW[81], COL[81], BOX[81];
static int ready;
static int need_eight;  // gf_require_eight; off by default
static int latin;       // gf_set_latin; off by default

// Latin-square mode (1): rows and columns only, no boxes. Implemented by giving
// every cell its own "box" (BOX[i] = i, masks sized 81), so the box constraint
// is vacuous and nothing else changes.
void gf_set_latin(int on) { latin = on; ready = 0; }
static uint8_t force_on[81], force_off[81];  // gf_set_pins

// Pin cells on and off: two 81-byte masks, 1 = pinned.
void gf_set_pins(const uint8_t *on, const uint8_t *off) {
    for (int i = 0; i < 81; i++) {
        force_on[i] = on ? on[i] : 0;
        force_off[i] = off ? off[i] : 0;
    }
}

// Require (1) or drop (0) the "some shaded cell shows 8" condition.
void gf_require_eight(int on) { need_eight = on; }

static void init(void) {
    if (ready) return;
    for (int i = 0; i < 81; i++) {
        int r = i / 9, c = i % 9;
        ROW[i] = r; COL[i] = c; BOX[i] = latin ? i : (r / 3) * 3 + c / 3;
        NBN[i] = ORTHN[i] = 0;
        for (int a = -1; a <= 1; a++)
            for (int b = -1; b <= 1; b++) {
                if (!a && !b) continue;
                int rr = r + a, cc = c + b;
                if (rr >= 0 && rr < 9 && cc >= 0 && cc < 9) {
                    NB[i][NBN[i]++] = rr * 9 + cc;
                    if (!a || !b) ORTH[i][ORTHN[i]++] = rr * 9 + cc;
                }
            }
    }
    ready = 1;
}

// One orthogonally connected shaded cell region?
static int connected(const uint8_t *sh) {
    int stack[81], top = 0, total = 0, start = -1;
    uint8_t seen[81] = {0};
    for (int i = 0; i < 81; i++) {
        if (!sh[i]) continue;
        total++;
        if (start < 0) start = i;
    }
    if (start < 0) return 0;
    stack[top++] = start;
    seen[start] = 1;
    int reached = 0;
    while (top) {
        int i = stack[--top];
        reached++;
        for (int k = 0; k < ORTHN[i]; k++) {
            int j = ORTH[i][k];
            if (sh[j] && !seen[j]) { seen[j] = 1; stack[top++] = j; }
        }
    }
    return reached == total;
}

// Fill giv (0 = no given). Returns 1 if admissible and connected (and, under
// gf_require_eight(1), showing an 8).
static int givens(const uint8_t *sh, uint8_t *giv) {
    uint16_t rm[9] = {0}, cm[9] = {0}, bm[81] = {0};
    int eight = 0;
    for (int i = 0; i < 81; i++)
        if ((force_on[i] && !sh[i]) || (force_off[i] && sh[i])) return 0;
    if (!connected(sh)) return 0;
    for (int i = 0; i < 81; i++) {
        giv[i] = 0;
        if (!sh[i]) continue;
        int n = 0;
        for (int k = 0; k < NBN[i]; k++) n += sh[NB[i][k]];
        if (!n) return 0;
        uint16_t bit = 1 << n;
        if ((rm[ROW[i]] | cm[COL[i]] | bm[BOX[i]]) & bit) return 0;
        rm[ROW[i]] |= bit; cm[COL[i]] |= bit; bm[BOX[i]] |= bit;
        giv[i] = n;
        eight |= n == 8;
    }
    return !need_eight || eight;
}

typedef struct {
    uint16_t rm[9], cm[9], bm[81];
    uint8_t grid[81];
    int found, cap;
} Search;

static int popc(unsigned x) { return __builtin_popcount(x); }

static int dfs(Search *s) {
    int best = -1, bn = 10;
    uint16_t bo = 0;
    for (int i = 0; i < 81; i++) {
        if (s->grid[i]) continue;
        uint16_t o = 0x3FE & ~(s->rm[ROW[i]] | s->cm[COL[i]] | s->bm[BOX[i]]);
        int n = popc(o);
        if (n < bn) { bn = n; best = i; bo = o; if (n <= 1) break; }
    }
    if (best < 0) return ++s->found >= s->cap;
    if (!bn) return 0;
    int r = ROW[best], c = COL[best], b = BOX[best];
    while (bo) {
        uint16_t bit = bo & -bo;
        bo ^= bit;
        s->rm[r] |= bit; s->cm[c] |= bit; s->bm[b] |= bit;
        s->grid[best] = (uint8_t)__builtin_ctz(bit);
        int stop = dfs(s);
        s->rm[r] ^= bit; s->cm[c] ^= bit; s->bm[b] ^= bit;
        s->grid[best] = 0;
        if (stop) return 1;
    }
    return 0;
}

static int count_givens(const uint8_t *giv, int cap) {
    Search s;
    memset(&s, 0, sizeof s);
    s.cap = cap;
    for (int i = 0; i < 81; i++) {
        if (!giv[i]) continue;
        uint16_t bit = 1 << giv[i];
        if ((s.rm[ROW[i]] | s.cm[COL[i]] | s.bm[BOX[i]]) & bit) return 0;
        s.rm[ROW[i]] |= bit; s.cm[COL[i]] |= bit; s.bm[BOX[i]] |= bit;
        s.grid[i] = giv[i];
    }
    dfs(&s);
    return s.found;
}

// Solutions of a shape's givens up to cap; -1 if inadmissible.
int gf_count(const uint8_t *shape, int cap) {
    init();
    uint8_t giv[81];
    if (!givens(shape, giv)) return -1;
    return count_givens(giv, cap);
}

static uint64_t rs;
static uint64_t rnd(void) { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static double unif(void) { return (rnd() >> 11) * (1.0 / 9007199254740992.0); }
static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

// Climb from shape (in/out: best shape). Returns best solution count
// (1 = unique), or -1 if the start is inadmissible/unsolvable.
// steps_out receives the number of moves tried.
int gf_climb(uint8_t *shape, uint64_t seed, double seconds, int cap, int64_t *steps_out,
             double t_hi, double t_lo, int max_toggles) {
    init();
    rs = seed ? seed : 88172645463325252ULL;
    uint8_t cur[81], trial[81], best[81], giv[81];
    memcpy(cur, shape, 81);
    if (!givens(cur, giv)) return -1;
    int score = count_givens(giv, cap);
    if (score <= 0) return -1;
    memcpy(best, cur, 81);
    int best_score = score;
    double start = now(), end = start + seconds, temp = t_hi;
    int64_t steps = 0;
    while (score != 1) {
        if ((steps & 255) == 0) {
            double t = now();
            if (t > end) break;
            temp = t_hi * pow(t_lo / t_hi, (t - start) / seconds);
        }
        steps++;
        memcpy(trial, cur, 81);
        int i = rnd() % 81;
        trial[i] ^= 1;
        int extra = rnd() % max_toggles;
        for (int e = 0; e < extra; e++) {
            int j = NB[i][rnd() % NBN[i]];
            trial[j] ^= 1;
            i = j;
        }
        if (!givens(trial, giv)) continue;
        int ts = count_givens(giv, cap);
        if (ts <= 0) continue;
        double worse = log((double)ts) - log((double)score);
        if (worse <= 0 || unif() < exp(-worse / temp)) {
            memcpy(cur, trial, 81);
            score = ts;
            if (score < best_score) { best_score = score; memcpy(best, cur, 81); }
        }
    }
    memcpy(shape, best, 81);
    if (steps_out) *steps_out = steps;
    return best_score;
}

// ---- gf_enumerate: every connected shape of one size, depth first -----------
//
// Redelmeier's walk: grow one orthogonally connected shape cell by cell from a
// root, so each shape is built exactly once. Unpinned, the root is the shape's
// lowest-index cell and lower cells are out. With a pinned-on cell the root is
// that cell and nothing is cut off. A cell the walk pops and does not take is
// out for the rest of that branch, so every cell is IN, OUT or still open.
//
// A shaded cell's given is its shaded king-neighbour count. A cell the shape can
// no longer reach (more than the cells left to place away from it, over open
// cells) is out for good, so a shaded cell with no reachable open king neighbour
// has its count settled. The walk prunes on: a settled count of 0, two settled
// counts equal inside a row, column or box, too few reachable cells to finish,
// and (all_digits) a digit of 1-8 that no cell can still show. Each complete
// shape then goes to gf_count, which stays the one judge of a shape.
#define OPEN 0
#define IN 1
#define OUT 2

typedef struct {
    int size, n, all_digits, symmetry, cap;
    uint8_t st[81];       // per cell: OPEN, IN the shape, or OUT of it
    uint8_t visited[81];  // ever offered to the untried set on this branch
    uint8_t shape[81];    // the shape so far, 0/1
    uint8_t reg[81];      // count settled and entered in the house masks
    int inn[81];          // shaded king neighbours so far
    int key[81];          // pick order: distance from the root row, then column
    uint16_t hr[9], hc[9], hb[81];  // settled counts used per row, column, box
    int regstack[81], regtop;
    int64_t shapes, solvable, unique, nodes, out_cap, stored;
    double deadline;
    int timed_out;
    uint8_t *out;
    int *out_k;
} Enum;

static int SYM[8][81];  // the 8 dihedral images as position permutations
static int sym_ready;

static void init_sym(void) {
    if (sym_ready) return;
    for (int t = 0; t < 8; t++)
        for (int i = 0; i < 81; i++) {
            int r = i / 9, c = i % 9, a = t & 1 ? 8 - r : r, b = t & 2 ? 8 - c : c;
            SYM[t][i] = t & 4 ? b * 9 + a : a * 9 + b;
        }
    sym_ready = 1;
}

// Keeps the largest of a shape's 8 images, read as a 0/1 string: one per orbit.
static int canonical(const uint8_t *sh) {
    for (int t = 1; t < 8; t++)
        for (int j = 0; j < 81; j++) {
            int a = sh[SYM[t][j]];
            if (a != sh[j]) {
                if (a > sh[j]) return 0;
                break;
            }
        }
    return 1;
}

static void unsettle_to(Enum *e, int mark) {
    while (e->regtop > mark) {
        int x = e->regstack[--e->regtop];
        uint16_t bit = 1 << e->inn[x];
        e->hr[ROW[x]] &= ~bit; e->hc[COL[x]] &= ~bit; e->hb[BOX[x]] &= ~bit;
        e->reg[x] = 0;
    }
}

// Re-read the position after a decision: 0 when no completion can satisfy the rules.
static int refresh(Enum *e) {
    int rem = e->size - e->n, dist[81], queue[81], qh = 0, qt = 0;
    for (int x = 0; x < 81; x++) {
        dist[x] = e->st[x] == IN ? 0 : 99;
        if (e->st[x] == IN) queue[qt++] = x;
    }
    int reachable = 0;
    while (qh < qt) {
        int x = queue[qh++];
        if (dist[x] >= rem) continue;
        for (int k = 0; k < ORTHN[x]; k++) {
            int y = ORTH[x][k];
            if (e->st[y] != OPEN || dist[y] <= dist[x] + 1) continue;
            dist[y] = dist[x] + 1;
            queue[qt++] = y;
            reachable++;
        }
    }
    if (reachable < rem) return 0;
    for (int x = 0; x < 81; x++)
        if (force_on[x] && e->st[x] == OPEN && dist[x] > rem) return 0;
    int seen = 0;
    for (int x = 0; x < 81; x++) {
        if (dist[x] > rem) continue;
        int open = 0;
        for (int k = 0; k < NBN[x]; k++) open += e->st[NB[x][k]] == OPEN && dist[NB[x][k]] <= rem;
        // Cells still to place that can raise x's count: an open x takes one of the rem
        // slots itself, so only rem - 1 can be its neighbours; an IN cell can use all rem.
        int lo = e->inn[x], hi = lo + open, room = e->st[x] == IN ? rem : rem - 1;
        if (e->st[x] == IN) {
            if (!open && !e->reg[x]) {
                if (lo < 1) return 0;
                uint16_t bit = 1 << lo;
                if ((e->hr[ROW[x]] | e->hc[COL[x]] | e->hb[BOX[x]]) & bit) return 0;
                e->hr[ROW[x]] |= bit; e->hc[COL[x]] |= bit; e->hb[BOX[x]] |= bit;
                e->reg[x] = 1;
                e->regstack[e->regtop++] = x;
            }
        }
        if (hi > lo + room) hi = lo + room;
        if (lo < 1) lo = 1;
        for (int d = lo; d <= hi && d <= 8; d++) seen |= 1 << d;
    }
    return !e->all_digits || seen == 0x1FE;
}

// Decide cell c IN or OUT and re-read the position; returns 0 when it breaks a rule.
// Always leaves the decision applied, so the caller undoes it either way.
static int decide(Enum *e, int c, int state) {
    e->st[c] = (uint8_t)state;
    if (state == IN) {
        e->n++;
        for (int k = 0; k < NBN[c]; k++) e->inn[NB[c][k]]++;
    }
    return refresh(e);
}

static void undecide(Enum *e, int c, int state) {
    if (state == IN) {
        e->n--;
        for (int k = 0; k < NBN[c]; k++) e->inn[NB[c][k]]--;
    }
    e->st[c] = OPEN;
}

static void leaf(Enum *e) {
    if (e->symmetry && !canonical(e->shape)) return;
    if (e->all_digits) {
        int seen = 0;
        for (int i = 0; i < 81; i++) {
            if (!e->shape[i]) continue;
            int n = 0;
            for (int k = 0; k < NBN[i]; k++) n += e->shape[NB[i][k]];
            seen |= 1 << n;
        }
        if ((seen & 0x1FE) != 0x1FE) return;
    }
    int k = gf_count(e->shape, e->cap);
    if (k < 0) return;
    e->shapes++;
    if (k >= 1) {
        if (e->stored < e->out_cap) {
            memcpy(e->out + 81 * e->stored, e->shape, 81);
            e->out_k[e->stored] = k;
            e->stored++;
        }
        e->solvable++;
    }
    if (k == 1) e->unique++;
}

static void grow(Enum *e, const int *untried_in, int cnt) {
    int entry = e->regtop, popped[81], np = 0, untried[81];
    memcpy(untried, untried_in, cnt * sizeof(int));
    while (cnt > 0 && !e->timed_out) {
        if ((++e->nodes & 4095) == 0 && e->deadline > 0 && now() > e->deadline) {
            e->timed_out = 1;
            break;
        }
        // any pick order is valid; the cell nearest the root row first settles counts row by row
        int best = 0;
        for (int i = 1; i < cnt; i++)
            if (e->key[untried[i]] < e->key[untried[best]]) best = i;
        int c = untried[best];
        untried[best] = untried[--cnt];
        popped[np++] = c;
        int mark = e->regtop;
        if (decide(e, c, IN)) {
            e->shape[c] = 1;
            if (e->n == e->size) {
                leaf(e);
            } else {
                int next[81], nn = cnt, added[4], na = 0;
                memcpy(next, untried, cnt * sizeof(int));
                for (int k = 0; k < ORTHN[c]; k++) {
                    int j = ORTH[c][k];
                    if (e->visited[j]) continue;
                    e->visited[j] = 1;
                    added[na++] = j;
                    next[nn++] = j;
                }
                grow(e, next, nn);
                for (int k = 0; k < na; k++) e->visited[added[k]] = 0;
            }
            e->shape[c] = 0;
        }
        unsettle_to(e, mark);
        undecide(e, c, IN);
        // c is out for the rest of this branch; a pinned-on cell cannot be
        if (force_on[c]) {
            np--;
            break;
        }
        if (!decide(e, c, OUT)) break;
    }
    unsettle_to(e, entry);
    for (int i = 0; i < np; i++) undecide(e, popped[i], OUT);
}

// Enumerate every orthogonally connected shape of `size` cells that satisfies the
// local rules (and, with all_digits, shows each of 1-8), honouring gf_set_pins and
// gf_require_eight, and count its sudoku solutions up to cap with gf_count.
// symmetry keeps one shape per orbit of the 8 dihedral images (refused with pins).
// seconds > 0 stops the search after that long. Solvable shapes (81 bytes each,
// with their count in out_k) are stored up to out_cap. stats receives shapes,
// solvable, unique, stored and 1 if the search ran to completion (0 if cut off).
// Returns 0, or -1 on bad arguments (cap below 2 would call every solvable shape unique).
int gf_enumerate(int size, int all_digits, int symmetry, int cap, double seconds,
                 uint8_t *out, int *out_k, int64_t out_cap, int64_t *stats) {
    init();
    init_sym();
    int pinned = 0, first_on = -1;
    for (int i = 0; i < 81; i++) {
        pinned |= force_on[i] | force_off[i];
        if (force_on[i] && first_on < 0) first_on = i;
    }
    if (size < 1 || size > 81 || cap < 2 || (symmetry && pinned)) return -1;
    static Enum e;
    memset(&e, 0, sizeof e);
    e.size = size; e.all_digits = all_digits; e.symmetry = symmetry; e.cap = cap;
    e.out = out; e.out_k = out_k; e.out_cap = out_cap;
    e.deadline = seconds > 0 ? now() + seconds : 0;
    int lo = first_on >= 0 ? first_on : 0, hi = first_on >= 0 ? first_on : 80;
    for (int root = lo; root <= hi && !e.timed_out; root++) {
        if (force_off[root]) continue;
        memset(e.st, OPEN, 81); memset(e.visited, 0, 81); memset(e.shape, 0, 81);
        memset(e.reg, 0, 81); memset(e.inn, 0, sizeof e.inn);
        memset(e.hr, 0, sizeof e.hr); memset(e.hc, 0, sizeof e.hc); memset(e.hb, 0, sizeof e.hb);
        e.regtop = 0; e.n = 0;
        for (int i = 0; i < 81; i++)
            if (force_off[i] || (first_on < 0 && i < root)) {
                e.visited[i] = 1;
                e.st[i] = OUT;
            }
        for (int i = 0; i < 81; i++) e.key[i] = abs(ROW[i] - ROW[root]) * 9 + COL[i];
        e.visited[root] = 1;
        if (decide(&e, root, IN)) {
            e.shape[root] = 1;
            if (e.n == e.size) {
                leaf(&e);
            } else {
                int next[81], nn = 0;
                for (int k = 0; k < ORTHN[root]; k++) {
                    int j = ORTH[root][k];
                    if (e.visited[j]) continue;
                    e.visited[j] = 1;
                    next[nn++] = j;
                }
                grow(&e, next, nn);
            }
        }
    }
    if (stats) {
        stats[0] = e.shapes; stats[1] = e.solvable; stats[2] = e.unique;
        stats[3] = e.stored; stats[4] = !e.timed_out;
    }
    return 0;
}
