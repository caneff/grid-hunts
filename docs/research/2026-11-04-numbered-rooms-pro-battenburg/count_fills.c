/* SCRATCH: exact count of sudoku fillings of the inner 7x7 for each border read from
 * stdin, one per line: 32 digits in row-major order of the edge cells. Solver-free,
 * smallest-domain-first search. Prints "<border> <count>" per line.
 *
 * Build: gcc -O2 -o OUT count_fills.c
 */
#include <stdio.h>
#include <string.h>

#define ALL 0x3FE

static int rows[9], cols[9], boxes[9];
static int er[49], ec[49], eb[49];
static unsigned long long total;

static void search(int n) {
    if (n == 0) {
        total++;
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
    for (int mask = best_mask; mask; mask &= mask - 1) {
        int bit = mask & -mask;
        rows[r] ^= bit;
        cols[c] ^= bit;
        boxes[b] ^= bit;
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

int main(void) {
    char line[128];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        if (strlen(line) != 32)
            return 2;
        for (int i = 0; i < 9; i++)
            rows[i] = cols[i] = boxes[i] = ALL;
        int at = 0, n = 0;
        for (int r = 0; r < 9; r++) {
            for (int c = 0; c < 9; c++) {
                int b = r / 3 * 3 + c / 3;
                if (r == 0 || r == 8 || c == 0 || c == 8) {
                    int bit = 1 << (line[at++] - '0');
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
        search(n);
        printf("%s %llu\n", line, total);
        fflush(stdout);
    }
    return 0;
}
