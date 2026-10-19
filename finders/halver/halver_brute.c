/* The shared halver layer's backtracking search in C (#59), loaded through
   ctypes by halver_brute_c.py, which states its contract. The same search as
   halver_brute.py with `probe_ends`: the same narrowing steps, the same
   probing of line ends and the same branching order. A line's narrowing is a
   table of the end pairs it allows, each with the doubled values its body
   cells may take, so a line type's own code never runs here. It shares no
   code with the CP-SAT model. */
#include <stdint.h>
#include <string.h>
#include <time.h>

#define MAXC 81
#define MAXH 27
#define MAXL 256
#define MAXB 81
#define MAXP (MAXL * 400)

typedef uint32_t m_t;

static int N, SIZE, NH;
static int house[MAXH][9];
static int npeer[MAXC], peer[MAXC][24];
static m_t DIG, HAL;
static int NL, la[MAXL], lb[MAXL], lnb[MAXL], lbody[MAXL][MAXB], lpoff[MAXL], lpn[MAXL];
static uint8_t px[MAXP], py[MAXP];
static m_t pspan[MAXP];
static int NE, ends[MAXC];
static m_t plain_dbl[512];
static int limit, found, timed_out;
static int *out;
static double deadline;
static int has_deadline;
static long nodes;

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

static inline m_t dbl(m_t mask) { return plain_dbl[mask & DIG] | ((mask >> N) << 1); }

static inline m_t cwd(m_t keep) {
    m_t bits = ((keep >> 1) & DIG) << N;
    for (int d = 0; d < N; d++)
        if (keep >> (2 * (d + 1)) & 1) bits |= 1u << d;
    return bits;
}

#define RESTRICT(i, keep)                          \
    do {                                           \
        m_t _b = cells[i], _a = _b & (keep);       \
        if (!_a) return 0;                         \
        if (_a != _b) { cells[i] = _a; changed = 1; } \
    } while (0)

static int propagate(m_t *cells, uint8_t *settled) {
    int changed = 1;
    while (changed) {
        changed = 0;
        for (int i = 0; i < SIZE; i++) {
            m_t mask = cells[i];
            if (settled[i] || (mask & (mask - 1))) continue;
            settled[i] = 1;
            m_t digit = (mask | mask >> N) & DIG;
            m_t clear = ~(digit | digit << N);
            if (mask & HAL) {
                clear &= ~HAL;
                for (int j = 0; j < SIZE; j++)
                    if (j != i) RESTRICT(j, ~mask);
            }
            for (int k = 0; k < npeer[i]; k++) RESTRICT(peer[i][k], clear);
        }
        for (int h = 0; h < NH; h++) {
            m_t once = 0, twice = 0;
            int hp[9], nhp = 0;
            for (int k = 0; k < N; k++) {
                int i = house[h][k];
                m_t d = (cells[i] | cells[i] >> N) & DIG;
                twice |= once & d;
                once |= d;
                if (cells[i] & HAL) hp[nhp++] = i;
            }
            if (once != DIG || !nhp) return 0;
            m_t single = once & ~twice;
            for (int d = 0; d < N; d++) {
                if (!(single >> d & 1)) continue;
                for (int k = 0; k < N; k++) {
                    int i = house[h][k];
                    if ((cells[i] | cells[i] >> N) >> d & 1) {
                        RESTRICT(i, (1u << d) | (1u << (N + d)));
                        break;
                    }
                }
            }
            if (nhp == 1) RESTRICT(hp[0], HAL);
            int only = -1, nonly = 0;
            for (int k = 0; k < nhp; k++)
                if (!(cells[hp[k]] & DIG)) { only = hp[k]; nonly++; }
            if (nonly > 1) return 0;
            if (nonly == 1)
                for (int k = 0; k < nhp; k++)
                    if (hp[k] != only) RESTRICT(hp[k], DIG);
        }
        m_t once = 0, twice = 0;
        for (int i = 0; i < SIZE; i++) {
            m_t h = cells[i] >> N;
            twice |= once & h;
            once |= h;
        }
        if (once != DIG) return 0;
        m_t single = once & ~twice;
        for (int d = 0; d < N; d++) {
            if (!(single >> d & 1)) continue;
            for (int i = 0; i < SIZE; i++)
                if (cells[i] >> (N + d) & 1) { RESTRICT(i, 1u << (N + d)); break; }
        }
        for (int l = 0; l < NL; l++) {
            m_t da = dbl(cells[la[l]]), db = dbl(cells[lb[l]]), dv[MAXB];
            for (int k = 0; k < lnb[l]; k++) dv[k] = dbl(cells[lbody[l][k]]);
            m_t ka = 0, kb = 0, kept = 0;
            for (int p = lpoff[l]; p < lpoff[l] + lpn[l]; p++) {
                if (!(da >> px[p] & 1) || !(db >> py[p] & 1)) continue;
                m_t span = pspan[p];
                int ok = 1;
                for (int k = 0; k < lnb[l] && ok; k++) ok = (dv[k] & span) != 0;
                if (ok) { ka |= 1u << px[p]; kb |= 1u << py[p]; kept |= span; }
            }
            if (!ka) return 0;
            RESTRICT(la[l], cwd(ka));
            RESTRICT(lb[l], cwd(kb));
            m_t body = cwd(kept);
            for (int k = 0; k < lnb[l]; k++) RESTRICT(lbody[l][k], body);
        }
    }
    return 1;
}

static int probe(m_t *cells, uint8_t *settled) {
    for (;;) {
        int pruned = 0;
        for (int e = 0; e < NE; e++) {
            int i = ends[e];
            m_t snap = cells[i];
            if (!(snap & (snap - 1))) continue;
            for (int bit = 0; bit < 2 * N; bit++) {
                if (!(snap >> bit & 1)) continue;
                m_t trial[MAXC];
                uint8_t ts[MAXC];
                memcpy(trial, cells, sizeof(m_t) * SIZE);
                memcpy(ts, settled, SIZE);
                trial[i] = 1u << bit;
                if (!propagate(trial, ts)) {
                    cells[i] &= ~(1u << bit);
                    if (!cells[i]) return 0;
                    pruned = 1;
                }
            }
        }
        if (!pruned) return 1;
        if (!propagate(cells, settled)) return 0;
    }
}

static int search(m_t *cells, uint8_t *settled) {
    if ((nodes++ & 255) == 0 && has_deadline && now() > deadline) timed_out = 1;
    if (timed_out) return 1;
    if (!propagate(cells, settled)) return 0;
    if (!probe(cells, settled)) return 0;
    int best_i = -1, best_n = 99, best_house = -1;
    for (int e = 0; e < NE; e++) {
        int c = __builtin_popcount(cells[ends[e]]);
        if (c > 1 && c < best_n) { best_n = c; best_i = ends[e]; }
    }
    if (best_i < 0) {
        for (int i = 0; i < SIZE; i++) {
            int c = __builtin_popcount(cells[i]);
            if (c > 1 && c < best_n) { best_n = c; best_i = i; }
        }
        if (best_i < 0) {
            int *o = out + found * SIZE;
            for (int i = 0; i < SIZE; i++) {
                m_t d = (cells[i] | cells[i] >> N) & DIG;
                o[i] = (32 - __builtin_clz(d)) + ((cells[i] & HAL) ? 16 : 0);
            }
            found++;
            return found >= limit;
        }
        for (int h = 0; h < NH; h++) {
            int c = 0;
            for (int k = 0; k < N; k++) c += (cells[house[h][k]] & HAL) != 0;
            if (c > 1 && c < best_n) { best_n = c; best_house = h; }
        }
    }
    m_t child[MAXC];
    uint8_t cs[MAXC];
    if (best_house >= 0) {
        for (int k = 0; k < N; k++) {
            int i = house[best_house][k];
            if (!(cells[i] & HAL)) continue;
            memcpy(child, cells, sizeof(m_t) * SIZE);
            memcpy(cs, settled, SIZE);
            child[i] &= HAL;
            if (search(child, cs)) return 1;
        }
        return 0;
    }
    m_t mask = cells[best_i];
    for (int bit = 0; bit < 2 * N; bit++) {
        if (!(mask >> bit & 1)) continue;
        memcpy(child, cells, sizeof(m_t) * SIZE);
        memcpy(cs, settled, SIZE);
        child[best_i] = 1u << bit;
        if (search(child, cs)) return 1;
    }
    return 0;
}

/* houses: nh * n cell indices. lines: per line a, b, nbody, body...;
   pairs: per line npairs then (x, y, span) triples. ends: the cells probed
   at every node and branched on first. Writes each solution as n * n
   ints, digit + 16 on a halver. Returns the count found, or -1 once `budget`
   seconds have passed (budget < 0: no deadline). */
int hb_solutions(int n, int nh, const int *houses, int nl, const int *lines,
                 const int *pairs, int ne, const int *ends_in,
                 int lim, double budget, int *out_buf) {
    N = n; SIZE = n * n; NH = nh;
    DIG = (1u << n) - 1; HAL = DIG << n;
    for (int m = 0; m < (1 << n); m++) {
        plain_dbl[m] = 0;
        for (int d = 0; d < n; d++)
            if (m >> d & 1) plain_dbl[m] |= 1u << (2 * (d + 1));
    }
    for (int h = 0; h < nh; h++)
        for (int k = 0; k < n; k++) house[h][k] = houses[h * n + k];
    for (int i = 0; i < SIZE; i++) {
        uint8_t is[MAXC] = {0};
        npeer[i] = 0;
        for (int h = 0; h < nh; h++) {
            int in = 0;
            for (int k = 0; k < n; k++) in |= house[h][k] == i;
            if (!in) continue;
            for (int k = 0; k < n; k++) {
                int j = house[h][k];
                if (j != i && !is[j]) { is[j] = 1; peer[i][npeer[i]++] = j; }
            }
        }
    }
    NL = nl;
    const int *p = lines, *q = pairs;
    int off = 0;
    for (int l = 0; l < nl; l++) {
        la[l] = *p++; lb[l] = *p++; lnb[l] = *p++;
        for (int k = 0; k < lnb[l]; k++) lbody[l][k] = *p++;
        lpn[l] = *q++; lpoff[l] = off;
        for (int k = 0; k < lpn[l]; k++) {
            px[off] = *q++; py[off] = *q++; pspan[off] = (m_t)*q++; off++;
        }
    }
    NE = ne;
    for (int e = 0; e < ne; e++) ends[e] = ends_in[e];
    limit = lim; found = 0; timed_out = 0; nodes = 0;
    out = out_buf;
    has_deadline = budget >= 0;
    deadline = now() + budget;
    m_t cells[MAXC];
    uint8_t settled[MAXC];
    for (int i = 0; i < SIZE; i++) { cells[i] = (1u << (2 * n)) - 1; settled[i] = 0; }
    search(cells, settled);
    return timed_out ? -1 : found;
}
