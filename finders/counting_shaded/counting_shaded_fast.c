// Hot loop of the counting shaded all-visible shape climb, in C (loaded via ctypes).
//
//   gcc -O2 -shared -fPIC -o counting_shaded_fast.so counting_shaded_fast.c -lm
//
// Same rules as shapes.py: a shaded cell's given is its shaded-neighbour count
// (1-8), givens are distinct within every row, column and box, and the shaded cells
// form one orthogonally connected region. gf_require_eight(1) also demands a
// given of 8; gf_set_pins forces cells on or off. gf_count counts sudoku solutions of a shape's givens up to a cap;
// gf_climb anneals on log solutions (temperature t_hi -> t_lo over the run; a
// move toggles a short king-walk of 1..max_toggles cells) and returns the best
// shape found.
#include <math.h>
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
