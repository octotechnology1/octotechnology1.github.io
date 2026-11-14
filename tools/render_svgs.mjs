#!/usr/bin/env node
/**
 * Rasterise many SVGs in one process (frames of Mark's greeting for the showreel).
 *
 *   node tools/render_svgs.mjs jobs.json
 *
 * jobs.json = [["in.svg", "out.png", width], ...]. resvg comes from D:/Marks_art_studio/tools/assetgen (its node_modules);
 * nothing is written there.
 */
import { createRequire } from 'node:module'
import fs from 'node:fs'

const require = createRequire('D:/Marks_art_studio/tools/assetgen/package.json')
const { Resvg } = require('@resvg/resvg-js')

const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
for (const [src, out, width] of jobs) {
  const svg = fs.readFileSync(src, 'utf8')
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: width }, background: 'rgba(0,0,0,0)' }).render().asPng()
  fs.writeFileSync(out, png)
}
console.log(`rendered ${jobs.length} svg`)
