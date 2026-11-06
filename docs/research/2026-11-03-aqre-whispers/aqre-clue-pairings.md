# What is paired with Aqre shading

Researched 2026-11-05. This is a survey of what I found, not a complete catalogue.

## Synopsis

- Aqre's own rules (Eric Fox, 2020): shade cells so all shaded cells are orthogonally connected; no run of four or more shaded or four or more unshaded cells in a row or column; a number in a region gives its shaded count. The GM Puzzles rules page adds: "it is allowed to shade over the numbered cells."
- In sudoku hybrids, the pairing I found most often is **a sum or count read off the shaded cells** (shaded count, or sum of shaded digits, per region). Three of the sudoku hybrids opened do this (Sudoqre, Heqtare, Cipher JS(Aqre)). Aspartagcus's Aqre arrow sudoku uses the plain count.
- The second most common pairing is **a second pencil-puzzle layer on the same grid**: Japanese Sums, Loop, Country Road, Shikaku, Cave, Cipher, Chaos Deconstruction. Setters who do this often use Japanese Sums or a loop on the unshaded cells, which gives a second route to the colour of a cell.
- I found **no sudoku with Aqre plus German whispers**, and none with Aqre plus thermometers, Kropki or renban. See the coverage section for what that claim rests on.
- Pure pencil-puzzle Aqre variants are mostly "extra rule on the regions" (Borders, Symmetry, All-or-Nothing/Paint, Twilight, Kropki between regions) and "Aqre as a layer on another genre" (Tapa, Kurotto, Cave, Nanro).

## Coverage

Searches run (Exa web search, 8 queries in total, paraphrased):

1. Aqre sudoku variant, shaded cells, no four in a row, SudokuPad, Logic Masters.
2. Aqre pencil puzzle rules and variants.
3. Aqre sudoku hybrid with thermometer, killer, German whispers.
4. "Aqre" sudoku Cracking the Cryptic video.
5. Ashish Kumar Sudoku Aqre sum of shaded cells.
6. Aqre sudoku logic-masters.de with thermo, killer, whispers.
7. Pencil puzzle sudoku hybrid series Aspartagcus Aqre sudoku.
8. Sudoku with Aqre plus thermometer, Kropki, X-sum, sandwich.

Pages fetched in full (opened): the Logic Masters Germany (LMD) entries *Sudoqre* and *Aqre(ish)*; the WPC unofficial wiki *Aqre* page; Eric Fox's blog Aqre label page (list of posts).

Pages read **only as search-result excerpts** (the engine returned the rules text, I did not open the page): LMD *Cipher JS(Aqre) Sudoku*, *Heqtare*, *Pencil puzzle sudoku hybrid series #3 - Aqre arrow sudoku*, *Aqres of Shikaku Country (9x9)*, *Aqropolis*, *2 Corinthians 4:18*, *Kurotto (Aqre)*, *Liar Japanese Sums #9 - Cave (Aqre)*, *LM24-Quali Fingerübung 9: Signpost Nanro (Aqre)*; GM Puzzles *Aqre Rules and Info*, *Aqre by Ashish Kumar* (and a comment on it), *Aqre (Symmetry) by Serkan Yürekli*; Broken Sign Games *Aqre (Twilight)*; Janko.at Aqre page; the Berkeley mini Math Tournament 2026 rules PDF; Madmahogany *Puzzle #17: Aqre*; meander lawn (excerpt of its Aqre rules).

Not opened or not available:
- No SudokuPad puzzle page was opened. Several LMD entries link to SudokuPad or Penpa, which I did not load, so I did not see the grids or the clue layouts.
- I did not open any Cracking the Cryptic video page for a sudoku with Aqre. The one CTC page my search returned was `https://crackingthecryptic.com/sudokuwatch?id=2122`, titled "Video is Kurotto (Aqre) by KNT". It is a pencil puzzle, and I only saw the title in the excerpt. I did not look for a CTC sudoku-Aqre video beyond the one search.
- The YouTube result "Don't Make 4 In A Row: Saturday Puzzle Series No.3" came back with no description text. I did not use it.
- A Scribd result failed to load ("Client Challenge"). Not used.
- I did not open the "Alan Baljeu" Sudoku-Aqre puzzles. A comment on GM Puzzles mentions them but gives no link, so I could not find the puzzle pages.
- I did not search Puzzlers Club, the Discord servers, Penpa-Edit libraries, or f-puzzles listings directly. A "none found" below means: none in the pages named in this file and none in the 8 search result sets.

## Clue types paired with Aqre in sudoku (and sudoku-like) puzzles

"Quoted" means the exact rule words are in the excerpt or page I saw. "Read" means I read the rules but paraphrase. "Inferred" means my reading.

| Clue type | What it does with the shading | Puzzles (title, author, date, URL) | Sureness |
|---|---|---|---|
| Sum of shaded digits in a cage | A cage clue is the sum of its shaded cells, not all its cells. | *Sudoqre (Sudoku Aqre Hybrid)*, PjotrV, 17 Nov 2023, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000FVH . Quoted: "Cages must contain the sum of the shaded cells indicated by the number in its upper left corner. Shaded cells within cages may not repeat." Page opened. | Quoted, page opened |
| Circle = shaded count, square = shaded sum, on a chaos construction | Circle digit "gives the amount of shaded cells in that cell's region"; square digit "gives the sum of the shaded cells in that cell's region". The regions are not drawn: the solver finds them (one to nine cells each), and a corner clue "gives the sum of the digits in that cell's region", with zero, one or more such clues per region. These are not separate killer cages. Aqre run limit is "No more than three shaded cells or unshaded cells may be adjacent in a row or column." No rule ties shading to digits. | *Heqtare*, mathpesto, 2 Sep 2022, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000B2E . Page text opened 2026-11-06; the embedded grid was not loaded. | Quoted from page |
| Arrow | Arrow digits sum to the circle. Shading is separate: the top-left digit of each region is its shaded count. | *Pencil puzzle sudoku hybrid series #3 - Aqre arrow sudoku*, Aspartagcus, 17 Nov 2020, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=0004QF . Quoted: "The regions ... must contain the number of shaded cells equal to the digit in the leftmost cell of the top row of each region." Excerpt only. | Quoted from excerpt |
| Japanese Sums on unshaded cells, ciphered | Outside clues sum the runs of digits in unshaded cells; "shaded cells serve as delimiters between groups". Clues are letter-coded. Box clue: "The digit in the upper-left corner of each box indicates the number of shaded cells in that region." | *Cipher JS(Aqre) Sudoku*, Las4one, 25 Sep 2025, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000PCT . Excerpt only. | Quoted from excerpt |
| Loop through all unshaded cells + Japanese Sums + Chaos Deconstruction | "The loop visits all unshaded cells and no shaded cells." Aqre part has no region counts in the rules text I saw, only the run limit. | *Aqropolis [Aqre Loop Japanese Sums Deconstruction]*, Christounet, 14 May 2024, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000I2O . Excerpt only. | Quoted from excerpt |
| Anti-X-sums + Chaos Deconstruction | Aqre is used only as a run limit on the regions: "A Chaos Deconstruction Region may not have more than 3 cells in a row horizontally or vertically." No shading is drawn. | *2 Corinthians 4:18 (Aqre Anti-X-Sum Chaos Deconstruction)*, MaizeGator, 18 Sep 2024, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000JW4 . Excerpt only. | Quoted from excerpt |
| Sudoku with the Aqre rule applied to odd digits (no shading drawn) | "All odd numbers must form one single orthogonally connected group"; "No more than four consecutive odd numbers in any row or column"; "There can be no 2x2 group of odd numbers." Note the run limit is four here, and a 2x2 ban is added. | *Aqre(ish)*, tuberculosis, 17 May 2026, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000SW1 . Page opened. | Quoted, page opened |
| Cages / killer (sudoku-only, no Aqre) | Not found paired with Aqre except as Heqtare's region-sum corner clues (on its hidden regions) and Sudoqre's cages above. | See rows above. | n/a |
| Shikaku + Country Road, as circled clues | A circled digit may refer to any of the three rules; "An Aqre clue is the amount of shaded cells in that region." Not a sudoku. | *Aqres of Shikaku Country (9x9)*, mathpesto and Nordy, 29 Oct 2022, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000BU3 . Excerpt only. | Quoted from excerpt |

Not found: Aqre with German or any whispers, thermometers, renban, Kropki dots between cells, X/V, sandwich, little killer, or skyscrapers. "None found" rests on the pages and searches listed above only. The Aqre sudoku LMD entries I could surface are the five in the table. Other hybrids may exist on SudokuPad-only or Discord-only releases that I did not search.

## Aqre variants in pencil puzzles

| Variant | What changes | Puzzle or source (title, author, date, URL) | Sureness |
|---|---|---|---|
| Borders | A pair of cells across a bold border has one shaded, one unshaded. Invented by Discord user Shye, per the wiki. | WPC 2022/Round 12 (Tom Coward) and Round 14 (JinHoo Ahn). Page: *Aqre*, WPC unofficial wiki, https://wpcunofficial.miraheze.org/wiki/Aqre . Quoted: "A pair of cells separated by a bold border must contain one shaded cell and one unshaded cell." Page opened. | Quoted, page opened |
| Symmetry | Regions with a circle in the centre: "the shaded cells must have 180° rotational symmetry around the circle." | WPC 2023 Round 11, Jamie Hargrove (same wiki page, opened). Also *Aqre (Symmetry)*, Serkan Yürekli, GM Puzzles, https://www.gmpuzzles.com/blog/category/variation/page/5/ (excerpt only; I did not open the single puzzle page, so its date is not recorded here). | Quoted |
| Symmetric (Janko) | Janko's variant text: shaded cells in each region symmetric about the region's centre. | *Aqre*, janko.at, https://www.janko.at/Raetsel/Aqre/index.htm . Excerpt only. | Read from excerpt |
| All or Nothing / Paint | Each region fully shaded or fully unshaded. | Eric Fox, *#480 - Aqre (All or Nothing)*, 12 Jul 2022, listed on https://ericfox53.blogspot.com/search/label/Aqre (page opened). Also "Paint" in the Berkeley mini Math Tournament 2026 rules, https://berkeley.mt/archives/bmmt-2026/puzzle-rules.pdf (a maths contest, not a puzzle site; excerpt only). | Quoted |
| Twilight | "Shaded clues indicate the number of unshaded cells in their region instead." Clues can sit anywhere in the region. | *Aqre (Twilight)*, Menderbug, 6 Sep 2023, https://brokensign.com/puzzle/2023/09/06/aqre-twilight.html . Excerpt only. | Quoted from excerpt |
| Binario | Each row has equal shaded and unshaded counts. | Berkeley mini Math Tournament 2026 rules PDF (as above). Excerpt only. | Quoted from excerpt |
| Kropki Aqre | Dots between touching regions: black when their shaded counts are 1:2, white when consecutive. No region numbers. | Eric Fox, *#328 - Kropki Aqre*, 17 Sep 2021, label page (opened). | Quoted, page opened |
| Aqre / Tapa hybrid | Tapa-style clues in unshaded cells give the block lengths of shaded cells in the eight neighbours; the Tapa 2x2 ban is switched off. | Eric Fox, *#345*, 8 Oct 2021 and *#195*, 24 Feb 2021, label page (opened). | Quoted, page opened |
| Kurotto (Aqre) | Clue cells are unshaded; the number is the total size of shaded groups touching the clue. **Unshaded** cells must be connected (the reverse of normal Aqre). | *Kurotto (Aqre)*, KNT, 3 Jun 2024, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000ICQ . Excerpt only. The CTC video page for it exists (id 2122) but I did not open it. | Quoted from excerpt |
| Cave (Aqre) with Liar Japanese Sums | Aqre run limit added to a Japanese Sums cave. | *Liar Japanese Sums #9 - Cave (Aqre)*, Niverio, 1 Aug 2024, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000J6B . Excerpt only. | Quoted from excerpt |
| Signpost Nanro (Aqre) | Numbers placed in cells; no more than three in a row numbered or unnumbered. | *LM24-Quali Fingerübung 9*, ibag, 18 Mar 2024, https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000H80 . Excerpt only, German text. | Read from excerpt |
| Cipher (WPC) | Clues letter-coded. | WPC 2022 Round 17, Tom Coward (Cipher), wiki page above. The wiki lists it by name only. | Listed, rules not read |

Aqre's run length is three in every source above except where noted. The Aqre(ish) sudoku uses four-in-a-row as its ban, which is longer than Aqre's.

## What forces shading early

Only the points a page supports are given as sourced. My own readings are marked.

Sourced:
- The Janko solving note on its Aqre page (example no. 6, by Emma, in German) says the solver works out "dass in jeder Zeile und jeder Spalte 2 weiße Felder sein müssen" (each row and column must hold 2 white cells), so there are 16 white cells in total, and the one large region can hold only 60-48 = 12 white cells, so the four small regions must be white. That is a count argument from the line limit combined with region counts. It is for one specific example grid. Excerpt only.
- Borders Aqre: the rule that cells across a bold border differ in colour fixes the colour of one cell from the other. Source: WPC wiki, opened.
- Paint / All or Nothing: a region's cells are all one colour, so one deduction fixes the whole region. Source: Eric Fox blog label page, opened.
- Japanese Sums with shaded cells as delimiters (Cipher JS(Aqre)) and the unshaded-only loop (Aqropolis): outside clues describe runs of unshaded cells, so they carry colour information straight from the edge. Source: excerpts above. That they force colour early is my reading, not stated.
- A solver comment on Aqre(ish) says "I needed the 2x2 constraint but I don't think at any point I required the 4 consecutive constraint to solve" (MikeyJoe, 18 May 2026), and another says "the checkerboard rule was enough to solve" (Blackophelia, 11 Jul 2026). This is evidence that in that puzzle the 2x2 ban did the work. Page opened.
- Sudoqre comments: "Cool application of Aqre logic in this puzzle!" (Mr.Menace, 18 Nov 2023). It tells us the Aqre logic matters in the solve, not how.

My inference (not stated by any page):
- Every four consecutive cells in a row or column must contain both colours. A 3x3 box is only three cells wide, so a box count of 0 or 9 (all white or all shaded) is legal alone but forces the neighbouring boxes in the same lines to supply the other colour within one cell of the border. Extreme box counts (0, 1, 8, 9) are therefore the strongest early-forcing clues in a 3x3-box design. A 0 or 9 count is a direct colour fix for nine cells.
- Correction for this project's rules, checked against `README.md`: with shaded 5-whispers a 3x3 box can only count 1 to 7, so counts of 0, 8 and 9 do not occur, and only the 1 from that list can be used.
- A clue that fixes the sum or count of shaded digits (as in Sudoqre) gives early information only when the cage is small. This is a guess from how those rules read, not from solving them.
- A given digit with a neighbour rule (such as whispers) tells you colour only if the shading rule is tied to the digit (for example "shaded cells obey the whisper"). I found no puzzle that does this with Aqre. Treat this as a design idea, not a precedent.
