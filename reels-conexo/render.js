// Gera o vídeo do Reels (1080x1920, 30 fps) a partir do index.html.
// Uso: node render.js   → saída em reels-conexo-premio-qualidade-2026.mp4
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const FPS = 30;
const OUT = path.join(__dirname, 'reels-conexo-premio-qualidade-2026.mp4');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?capture');
  await page.evaluate(() => document.fonts.ready);
  const duration = await page.evaluate(() => window.DURATION);
  const frames = Math.round(duration * FPS);

  // trilha original gerada por trilha.py (rode "python3 trilha.py" antes)
  const ffmpeg = spawn('ffmpeg', [
    '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-i', path.join(__dirname, 'trilha.wav'),
    '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-crf', '18', '-preset', 'medium',
    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '44100', '-c:a', 'aac', '-b:a', '192k',
    '-movflags', '+faststart', OUT,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  for (let i = 0; i < frames; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'png' });
    if (!ffmpeg.stdin.write(buf)) await new Promise(r => ffmpeg.stdin.once('drain', r));
  }
  ffmpeg.stdin.end();
  await new Promise(r => ffmpeg.on('close', r));
  await browser.close();
  console.log('Vídeo gerado:', OUT);
})();
