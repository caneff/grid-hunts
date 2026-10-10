// Open a U-Bahn Penpa+ link in a real browser and check what the encoder
// (penpa.py, #774) cannot: that the page loads it in the Line tool, and that
// the embedded answer check agrees with a drawn network. Run it in the local
// session: it needs Chromium and the live Penpa+ page.
//
//   node finders/ubahn/penpa-browser-check.mjs LINKFILE [--shots DIR]
//
// On the opened page it also reads the page's own state: the number strips'
// icons run cross, branch, straight, turn from the outside in (a hollow square
// first when the blank number is shown), and the header's centre point is the
// one Penpa+'s own search_center computes. The number of strips is read off
// the page. Then three drawings on fresh pages, each by mouse drags between the centres of
// adjacent cells: the answer's own edges (the success dialog must come), the
// answer with one edge missing, and the answer with one edge moved to a cell
// pair that is not in it (neither may come). The solution comes from the
// link's own `a` parameter. With --shots, a picture of the opened board and of
// the solved one are written to DIR. Prints a result line per check, never the
// link: AGENTS.md § Puzzle links.

/* global pu */
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'
import { chromium } from 'playwright'

const args = process.argv.slice(2)
function refuse (why) {
  console.error(`penpa-browser-check: ${why}`)
  console.error('usage: penpa-browser-check.mjs LINKFILE [--shots DIR]')
  process.exit(2)
}
const linkFile = args[0]
if (!linkFile || linkFile.startsWith('--')) refuse('no link file given')
const shotsAt = args.indexOf('--shots')
if (shotsAt !== -1 && (!args[shotsAt + 1] || args[shotsAt + 1].startsWith('--'))) refuse('--shots needs a directory')
const shots = shotsAt === -1 ? null : args[shotsAt + 1]
const link = fs.readFileSync(linkFile, 'utf8').trim()

const redact = text => String(text).split(link).join('<link>').slice(0, 300)

// The answer's segments as pairs of cell-centre indices.
const answerMatch = /[?#&]a=([^&]*)/.exec(link)
if (!answerMatch) refuse('the link has no a= answer parameter to draw from')
const answerParam = answerMatch[1]
const answer = JSON.parse(zlib.inflateRawSync(Buffer.from(answerParam, 'base64')).toString('utf8'))
const edges = answer[1].map(entry => entry.split(',').slice(0, 2).map(Number))

let failed = false
function report (name, ok, detail = '') {
  if (!ok) failed = true
  console.log(`${ok ? 'ok' : 'FAIL'}: ${name}${detail ? ` (${detail})` : ''}`)
}

const browser = await chromium.launch()

async function open () {
  const page = await browser.newPage({ viewport: { width: 1300, height: 1000 } })
  const problems = []
  page.on('pageerror', e => problems.push(redact(e)))
  try {
    await page.goto(link, { waitUntil: 'networkidle', timeout: 60000 })
  } catch (e) {
    throw new Error(`the page did not load: ${redact(e.message)}`)
  }
  await page.waitForFunction(() => typeof pu !== 'undefined' && pu.point && pu.point.length > 0)
  await page.waitForTimeout(500)
  return { page, problems }
}

async function draw (page, pairs) {
  const box = await page.locator('#canvas').boundingBox()
  const centres = await page.evaluate(
    ids => ids.map(([a, b]) => [pu.point[a], pu.point[b]].map(p => [p.x, p.y])), pairs)
  for (const [[ax, ay], [bx, by]] of centres) {
    await page.mouse.move(box.x + ax, box.y + ay)
    await page.mouse.down()
    await page.mouse.move(box.x + bx, box.y + by, { steps: 4 })
    await page.mouse.up()
  }
  await page.waitForTimeout(300)
}

async function verdict (page) {
  return page.evaluate(() => ({
    flag: pu.sol_flag,
    dialog: !!document.querySelector('.swal2-popup, .swal2-container'),
    text: (document.querySelector('.swal2-popup') || { innerText: '' }).innerText.slice(0, 80)
  }))
}

// A neighbouring pair of grid cells that the answer does not use, as indices;
// the grid is what lies past the number strips on the page's table.
async function strayEdge (page) {
  const { nx, ny, strips } = await page.evaluate(() => ({ nx: pu.nx, ny: pu.ny, strips: pu.centerlist[0] % (pu.nx + 4) - 1 }))
  const nx0 = nx + 4
  const first = 2 + strips
  const used = new Set(edges.map(e => e.join(',')))
  for (let y = first; y < ny + 2; y++) {
    for (let x = first; x < nx + 2; x++) {
      const a = x + y * nx0
      for (const b of [a + 1, a + nx0]) {
        const onBoard = b === a + 1 ? x + 1 < nx + 2 : y + 1 < ny + 2
        if (onBoard && !used.has(`${a},${b}`)) return [a, b]
      }
    }
  }
  return null
}

try {
  const opened = await open()
  const state = await opened.page.evaluate(() => ({
    answerTool: pu.mode.pu_a.edit_mode,
    solving: pu.mode.qa,
    flag: pu.sol_flag,
    hasSolution: typeof pu.solution === 'string' && pu.solution.length > 0
  }))
  report('the link opens in the Line tool, solving, with an embedded answer',
    state.answerTool === 'line' && state.solving === 'pu_a' && state.hasSolution, JSON.stringify(state))
  report('the page raised no error while loading', opened.problems.length === 0, opened.problems.join('; '))
  if (shots) {
    fs.mkdirSync(shots, { recursive: true })
    const box = await opened.page.locator('#canvas').boundingBox()
    await opened.page.screenshot({ path: path.join(shots, 'opened.png'), clip: box })
  }
  // The strips' icons: for each strip from the outside in, what the cell at
  // the inner end of its row (and of its column) shows. Read from the page's
  // own question layer, not from the link text.
  const strips = await opened.page.evaluate(() => {
    const t = pu.centerlist[0] % (pu.nx + 4) - 1
    const nx0 = pu.nx + 4
    const kindAt = (x, y) => {
      const at = x + y * nx0
      const sym = pu.pu_q.symbol[at]
      if (!sym) return pu.pu_q.number[at] ? 'text:' + pu.pu_q.number[at][0] : 'none'
      const f = sym[0]
      const arms = f[0] + f[1] + f[2] + f[3]
      if (arms === 4) return 'cross'
      if (arms === 3) return 'branch'
      return f[0] === f[2] ? 'straight' : 'turn'
    }
    const rows = []
    const cols = []
    for (let j = 0; j < t; j++) {
      rows.push(kindAt(t + 1, 2 + j))
      cols.push(kindAt(2 + j, t + 1))
    }
    return { t, rows, cols }
  })
  const ruled = ['cross', 'branch', 'straight', 'turn']
  const wanted = strips.t === 5 ? ['text:\u25a1', ...ruled] : ruled
  report('the icons run in the ruled order from the outside in, rows and columns',
    JSON.stringify(strips.rows) === JSON.stringify(wanted) && JSON.stringify(strips.cols) === JSON.stringify(wanted),
    `${strips.t} strips: rows ${strips.rows.join(',')}; columns ${strips.cols.join(',')}`)
  const centre = await opened.page.evaluate(() => {
    const header = pu.center_n
    pu.center_n = 0
    pu.search_center()
    const computed = pu.center_n
    pu.center_n = header
    return { header, computed }
  })
  report("the header's centre point is the one Penpa+ computes",
    centre.header === centre.computed, JSON.stringify(centre))
  report('nothing is solved before drawing', (await verdict(opened.page)).flag === 0)
  await opened.page.close()

  const right = await open()
  await draw(right.page, edges)
  const got = await verdict(right.page)
  report('drawing the solution marks it solved and shows the dialog',
    got.flag === 1 && got.dialog, JSON.stringify(got))
  if (shots) {
    const box = await right.page.locator('#canvas').boundingBox()
    await right.page.screenshot({ path: path.join(shots, 'solved.png') })
    await right.page.screenshot({ path: path.join(shots, 'solved-board.png'), clip: box })
  }
  await right.page.close()

  const missing = await open()
  await draw(missing.page, edges.slice(1))
  const noDialog = await verdict(missing.page)
  report('the solution with one edge missing is not solved',
    noDialog.flag === 0 && !noDialog.dialog, JSON.stringify(noDialog))
  await missing.page.close()

  const wrong = await open()
  const stray = await strayEdge(wrong.page)
  if (stray) {
    await draw(wrong.page, [...edges.slice(1), stray])
    const none = await verdict(wrong.page)
    report('a wrong network of the same size is not solved',
      none.flag === 0 && !none.dialog, JSON.stringify(none))
  } else {
    report('a wrong network could be built', false, 'every neighbour pair is in the answer')
  }
  await wrong.page.close()
} catch (e) {
  report('the check ran', false, redact(e.message))
} finally {
  await browser.close()
}
process.exit(failed ? 1 : 0)
