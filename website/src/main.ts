import './style.css'
import './glitch.css'
import React from 'react'
import { createRoot } from 'react-dom/client'
import GlitchText from './GlitchText'

// ─── INSTALL COPY BOXES ───────────────────────────────────
function setupInstallBox(id: string, feedbackId: string) {
  const box = document.getElementById(id)
  if (!box) return
  const feedback = document.getElementById(feedbackId)
  box.addEventListener('click', () => {
    navigator.clipboard.writeText('pip install watchllm')
    if (feedback) {
      feedback.classList.add('show')
      setTimeout(() => feedback.classList.remove('show'), 2000)
    }
  })
}
setupInstallBox('install-box', 'copy-fb-1')
setupInstallBox('install-box-2', 'copy-fb-2')

// ─── HERO PARTICLE FIELD (INDUSTRIAL VOLT MATRIX) ────────
const particleCanvas = document.getElementById('hero-particles')
if (particleCanvas) {
  const canvas = document.createElement('canvas')
  particleCanvas.appendChild(canvas)
  const ctx = canvas.getContext('2d')
  if (ctx) {
    let particles: { x: number; y: number; vy: number; life: number; maxLife: number; char: string }[] = []
    const chars = '01#%&@'

    function resize() {
      if (!particleCanvas) return
      canvas.width = particleCanvas.clientWidth
      canvas.height = particleCanvas.clientHeight
    }
    resize()
    window.addEventListener('resize', resize)

    function spawnParticle() {
      return {
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vy: Math.random() * 0.8 + 0.4,
        life: 0,
        maxLife: 200 + Math.random() * 150,
        char: chars[Math.floor(Math.random() * chars.length)],
      }
    }

    for (let i = 0; i < 60; i++) {
      particles.push(spawnParticle())
    }

    function animate() {
      if (!ctx || !canvas) return
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.font = '14px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'

      particles = particles.filter(p => p.life < p.maxLife)
      while (particles.length < 60) {
        particles.push(spawnParticle())
      }

      for (const p of particles) {
        p.y += p.vy
        p.life++

        if (Math.random() < 0.08) {
          p.char = chars[Math.floor(Math.random() * chars.length)]
        }

        const alpha = 1 - p.life / p.maxLife
        ctx.fillStyle = `rgba(204, 255, 0, ${alpha * 0.7})` // Volt Highlighter Yellow
        ctx.fillText(p.char, p.x, p.y)

        if (p.y > canvas.height + 10) {
          p.y = -10
          p.life = 0
        }
      }

      requestAnimationFrame(animate)
    }
    animate()
  }
}

// ─── FAKE LIVE COUNTER ────────────────────────────────────
const statBlocked = document.getElementById('stat-blocked')
if (statBlocked) {
  const baseVal = 124793571
  function updateCounter() {
    const val = baseVal + Math.floor((Date.now() / 1000) * 0.08)
    statBlocked!.textContent = val.toLocaleString()
    setTimeout(updateCounter, 2500)
  }
  updateCounter()
}

// ─── REACT HERO RENDER WITH BRUTAL TYPOGRAPHY ────────────
const reactHeroRoot = document.getElementById('react-hero-root')
if (reactHeroRoot) {
  const root = createRoot(reactHeroRoot)
  root.render(
    React.createElement(
      'h1',
      {
        className: 'hero-headline-massive',
        style: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }
      },
      React.createElement('span', { className: 'hero-line' }, 'YOUR AI AGENT'),
      React.createElement('span', { className: 'hero-headline-strike hero-line' }, 'IS YOUR CO-PILOT'),
      React.createElement(GlitchText, {
        text: 'IS A FUCKING LIAR.',
        speed: 0.5,
        enableShadows: true,
        enableOnHover: false,
        className: 'hero-headline-liar hero-line'
      })
    )
  )
}

// ─── CONSOLE EASTER EGG ───────────────────────────────────
console.log(
  '%cWATCHLLM%c — %cTYPOGRAPHIC MAXIMALISM // DETERMINISTIC KERNEL%c',
  'color: #ccff00; font-size: 24px; font-weight: bold; background: #000; padding: 4px;',
  '',
  'color: #ff2200; font-weight: bold;',
  ''
)
