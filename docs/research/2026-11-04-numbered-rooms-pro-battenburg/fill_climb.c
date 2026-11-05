/* SCRATCH: climb towards a sudoku grid whose 32 border cells fix its inner 7x7.
 *
 * Marks and Numbered Rooms play no part: this asks only about the border. State is a
 * full grid. A move swaps two rows of a band or two columns of a stack on a closed cell
 * set, or swaps two digits on a connected set, so a move always gives a valid grid,
 * which is checked. Score is the exact number of fillings of the border, with
 * an early abort above the acceptance limit. Annealed on log(fillings), restarting when
 * stuck. Logs each new fewest-fillings grid and each new most-forced-inner-cells grid.
 * A forced inner cell holds one digit across every filling. One thread.
 *
 * Build: gcc -O2 -o OUT fill_climb.c -lm
 * Usage: OUT SECONDS SEED OUT_FILE
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define ALL 0x3FE
#define START_LIMIT 30000000ULL
#define STUCK 4000

static int rows[9], cols[9], boxes[9];
static int er[49], ec[49], eb[49];
static int digit[9][9], seen[9][9];
static unsigned long long total, limit;
static int aborted;

static unsigned long long state;
static unsigned long long rnd(void) {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}

static void search(int n) {
    if (aborted)
        return;
    if (n == 0) {
        total++;
        if (total > limit) {
            aborted = 1;
            return;
        }
        for (int r = 1; r < 8; r++)
            for (int c = 1; c < 8; c++)
                seen[r][c] |= digit[r][c];
        return;
    }
    int best = -1, best_n = 10, best_mask = 0;
    for (int i = 0; i < n; i++) {
        int mask = rows[er[i]] & cols[ec[i]] & boxes[eb[i]];
        int count = __builtin_popcount(mask);
        if (count < best_n) {
            best = i;
            best_n = count;
            best_mask = mask;
            if (count <= 1)
                break;
        }
    }
    if (best_n == 0)
        return;
    int r = er[best], c = ec[best], b = eb[best];
    er[best] = er[n - 1];
    ec[best] = ec[n - 1];
    eb[best] = eb[n - 1];
    for (int mask = best_mask; mask && !aborted; mask &= mask - 1) {
        int bit = mask & -mask;
        rows[r] ^= bit;
        cols[c] ^= bit;
        boxes[b] ^= bit;
        digit[r][c] = bit;
        search(n - 1);
        rows[r] ^= bit;
        cols[c] ^= bit;
        boxes[b] ^= bit;
    }
    er[n - 1] = er[best];
    ec[n - 1] = ec[best];
    eb[n - 1] = eb[best];
    er[best] = r;
    ec[best] = c;
    eb[best] = b;
}

/* Fillings of g's border, or 0 if above lim. Sets seen[][] when complete. */
static unsigned long long fills(int g[9][9], unsigned long long lim) {
    for (int i = 0; i < 9; i++)
        rows[i] = cols[i] = boxes[i] = ALL;
    int n = 0;
    for (int r = 0; r < 9; r++) {
        for (int c = 0; c < 9; c++) {
            int b = r / 3 * 3 + c / 3;
            if (r == 0 || r == 8 || c == 0 || c == 8) {
                int bit = 1 << g[r][c];
                rows[r] &= ~bit;
                cols[c] &= ~bit;
                boxes[b] &= ~bit;
            } else {
                er[n] = r;
                ec[n] = c;
                eb[n] = b;
                n++;
            }
        }
    }
    total = 0;
    limit = lim;
    aborted = 0;
    memset(seen, 0, sizeof seen);
    search(n);
    return aborted ? 0 : total;
}

/* Random refill of the zero cells of g. Returns 1 on success. */
static long budget;
static int refill(int g[9][9]) {
    if (--budget < 0)
        return 0;
    int br = -1, bc = -1, bn = 10, bmask = 0;
    int ru[9] = {0}, cu[9] = {0}, xu[9] = {0};
    for (int r = 0; r < 9; r++)
        for (int c = 0; c < 9; c++)
            if (g[r][c]) {
                int bit = 1 << g[r][c];
                ru[r] |= bit;
                cu[c] |= bit;
                xu[r / 3 * 3 + c / 3] |= bit;
            }
    for (int r = 0; r < 9; r++)
        for (int c = 0; c < 9; c++)
            if (!g[r][c]) {
                int mask = ALL & ~(ru[r] | cu[c] | xu[r / 3 * 3 + c / 3]);
                int count = __builtin_popcount(mask);
                if (count < bn) {
                    bn = count;
                    br = r;
                    bc = c;
                    bmask = mask;
                }
            }
    if (br < 0)
        return 1;
    if (bn == 0)
        return 0;
    int options[9], k = 0;
    for (int d = 1; d <= 9; d++)
        if (bmask >> d & 1)
            options[k++] = d;
    for (int i = k - 1; i > 0; i--) {
        int j = rnd() % (i + 1), t = options[i];
        options[i] = options[j];
        options[j] = t;
    }
    for (int i = 0; i < k; i++) {
        g[br][bc] = options[i];
        if (refill(g))
            return 1;
        g[br][bc] = 0;
        if (budget < 0)
            return 0;
    }
    return 0;
}

static int same_border(int a[9][9], int b[9][9]) {
    for (int r = 0; r < 9; r++)
        for (int c = 0; c < 9; c++)
            if ((r == 0 || r == 8 || c == 0 || c == 8) && a[r][c] != b[r][c])
                return 0;
    return 1;
}

static void new_grid(int g[9][9]) {
    do {
        memset(g, 0, sizeof(int) * 81);
        budget = 200000;
    } while (!refill(g));
}

/* Swap two rows of a band on the smallest column set closed under their digits. */
static void swap_rows(int a[9][9]) {
    int band = rnd() % 3, i = band * 3 + rnd() % 3, j;
    do
        j = band * 3 + rnd() % 3;
    while (j == i);
    int c = rnd() % 9, first = a[i][c];
    while (1) {
        int t = a[i][c];
        a[i][c] = a[j][c];
        a[j][c] = t;
        int want = a[i][c];
        if (want == first)
            return;
        int next = -1;
        for (int k = 0; k < 9; k++)
            if (k != c && a[i][k] == want)
                next = k;
        c = next;
    }
}

static void transpose(int a[9][9]) {
    for (int r = 0; r < 9; r++)
        for (int c = r + 1; c < 9; c++) {
            int t = a[r][c];
            a[r][c] = a[c][r];
            a[c][r] = t;
        }
}

/* Swap digits x and y on one connected set of their cells. */
static void swap_digits(int a[9][9]) {
    int x = 1 + rnd() % 9, y;
    do
        y = 1 + rnd() % 9;
    while (y == x);
    int mark[9][9] = {{0}}, stack[81][2], top = 0;
    for (int r = 0, done = 0; r < 9 && !done; r++)
        for (int c = 0; c < 9; c++)
            if (a[r][c] == x) {
                stack[top][0] = r;
                stack[top++][1] = c;
                mark[r][c] = 1;
                done = 1;
                break;
            }
    /* Random start: rotate through x cells. */
    int skip = rnd() % 9;
    if (skip) {
        memset(mark, 0, sizeof mark);
        top = 0;
        int seen_x = 0;
        for (int r = 0; r < 9 && !top; r++)
            for (int c = 0; c < 9; c++)
                if (a[r][c] == x && seen_x++ == skip) {
                    stack[top][0] = r;
                    stack[top++][1] = c;
                    mark[r][c] = 1;
                    break;
                }
    }
    while (top) {
        top--;
        int r = stack[top][0], c = stack[top][1];
        for (int p = 0; p < 9; p++)
            for (int q = 0; q < 9; q++)
                if (!mark[p][q] && (a[p][q] == x || a[p][q] == y) &&
                    (p == r || q == c || (p / 3 == r / 3 && q / 3 == c / 3))) {
                    mark[p][q] = 1;
                    stack[top][0] = p;
                    stack[top++][1] = q;
                }
    }
    for (int r = 0; r < 9; r++)
        for (int c = 0; c < 9; c++)
            if (mark[r][c])
                a[r][c] = a[r][c] == x ? y : x;
}

static int is_valid(int a[9][9]) {
    for (int i = 0; i < 9; i++) {
        int rm = 0, cm = 0, bm = 0;
        for (int j = 0; j < 9; j++) {
            rm |= 1 << a[i][j];
            cm |= 1 << a[j][i];
            bm |= 1 << a[i / 3 * 3 + j / 3][i % 3 * 3 + j % 3];
        }
        if (rm != ALL || cm != ALL || bm != ALL)
            return 0;
    }
    return 1;
}

static int mutate(int g[9][9], int out[9][9]) {
    for (int attempt = 0; attempt < 200; attempt++) {
        memcpy(out, g, sizeof(int) * 81);
        int steps = 1 + rnd() % 2;
        for (int i = 0; i < steps; i++) {
            switch (rnd() % 3) {
            case 0:
                swap_rows(out);
                break;
            case 1:
                transpose(out);
                swap_rows(out);
                transpose(out);
                break;
            default:
                swap_digits(out);
            }
        }
        if (!is_valid(out))
            abort();
        if (!same_border(out, g))
            return 1;
    }
    return 0;
}

static int forced_count(void) {
    int n = 0;
    for (int r = 1; r < 8; r++)
        for (int c = 1; c < 8; c++)
            n += __builtin_popcount(seen[r][c]) == 1;
    return n;
}

static void log_grid(FILE *f, const char *why, unsigned long long count, int forced, int g[9][9], long evals, double t) {
    fprintf(f, "%s fills=%llu forced=%d evals=%ld t=%.0f ", why, count, forced, evals, t);
    for (int r = 0; r < 9; r++) {
        for (int c = 0; c < 9; c++)
            fprintf(f, "%d", g[r][c]);
        if (r < 8)
            fprintf(f, " ");
    }
    fprintf(f, "\n");
    fflush(f);
}

int main(int argc, char **argv) {
    if (argc != 4)
        return 2;
    double seconds = atof(argv[1]);
    state = strtoull(argv[2], 0, 10) * 2654435761ULL + 88172645463325252ULL;
    FILE *f = fopen(argv[3], "a");
    if (!f)
        return 3;
    time_t start = time(0);
    unsigned long long best_count = ~0ULL;
    int best_forced = -1;
    long evals = 0, restarts = 0;
    int cur[9][9], cand[9][9];
    while (difftime(time(0), start) < seconds) {
        unsigned long long cur_count = 0;
        do {
            new_grid(cur);
            cur_count = fills(cur, START_LIMIT);
        } while (!cur_count);
        restarts++;
        long stuck = 0;
        unsigned long long local = cur_count;
        while (stuck < STUCK && difftime(time(0), start) < seconds) {
            if (!mutate(cur, cand))
                break;
            double u = (rnd() % 1000000 + 1) / 1000001.0;
            double room = -0.05 * log(u);
            unsigned long long lim = (unsigned long long)(cur_count * exp(room)) + 1;
            unsigned long long count = fills(cand, lim);
            evals++;
            stuck++;
            if (!count)
                continue;
            memcpy(cur, cand, sizeof cur);
            cur_count = count;
            int forced = forced_count();
            double t = difftime(time(0), start);
            if (count < local) {
                local = count;
                stuck = 0;
            }
            if (count < best_count) {
                best_count = count;
                log_grid(f, "best_fills", count, forced, cand, evals, t);
            }
            if (forced > best_forced) {
                best_forced = forced;
                log_grid(f, "best_forced", count, forced, cand, evals, t);
            }
            if (count == 1) {
                log_grid(f, "FIXED", count, forced, cand, evals, t);
            }
        }
    }
    fprintf(f, "done evals=%ld restarts=%ld best_fills=%llu best_forced=%d\n", evals, restarts, best_count, best_forced);
    fclose(f);
    return 0;
}
