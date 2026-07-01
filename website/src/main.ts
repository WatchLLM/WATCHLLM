import './style.css'

// ─── INSTALL COPY BOXES ───────────────────────────────────
function setupInstallBox(id: string) {
  const box = document.getElementById(id)
  if (!box) return
  const feedback = box.querySelector('.copy-feedback')
  box.addEventListener('click', () => {
    navigator.clipboard.writeText('pip install watchllm')
    if (feedback) {
      feedback.classList.add('show')
      setTimeout(() => feedback.classList.remove('show'), 1800)
    }
  })
}
setupInstallBox('install-box')
setupInstallBox('install-box-2')

// ─── WORDMARK GLITCH ──────────────────────────────────────
const heroWordmark = document.getElementById('hero-wordmark')
if (heroWordmark) {
  setInterval(() => {
    if (Math.random() > 0.12) return
    heroWordmark.classList.add('glitching')
    setTimeout(() => heroWordmark.classList.remove('glitching'), 150)
  }, 2200 + Math.random() * 2000)
}

// ─── HERO LIVE TERMINAL ───────────────────────────────────
const terminalLog = document.getElementById('hero-terminal-log')
if (terminalLog) {
  const events = [
    { type: 'block', text: 'BLOCK  src/utils/helpers.ts  secret_literal  sk_live_51H8****' },
    { type: 'block', text: 'BLOCK  src/auth/login.ts     boundaries      ../../db/internal' },
    { type: 'allow', text: 'ALLOW  src/components/Button.tsx  all rules pass  4.1ms' },
    { type: 'block', text: 'BLOCK  src/api/debug.ts      forbidden_import  child_process' },
    { type: 'block', text: 'BLOCK  .env.local            secret_literal  AKIAIOSFOD****' },
    { type: 'allow', text: 'ALLOW  src/hooks/useAuth.ts  all rules pass  2.8ms' },
    { type: 'block', text: 'BLOCK  src/routes/admin.ts   auth_flow       no middleware' },
    { type: 'block', text: 'BLOCK  config/db.ts          secret_literal  postgres://root:***' },
    { type: 'dim', text: '--- agent save intercepted. evaluating AST... ---' },
    { type: 'block', text: 'BLOCK  src/lib/eval.ts       forbidden_import  vm' },
  ]

  let idx = 0
  const maxLines = 14

  function pushLine(event: (typeof events)[0]) {
    if (!terminalLog) return
    const line = document.createElement('div')
    line.className = `hero-terminal-line hero-terminal-line--${event.type}`
    const ms = (Math.random() * 9 + 1).toFixed(1)
    line.textContent = event.type === 'dim'
      ? event.text
      : `${event.text}  ${ms}ms`
    terminalLog.appendChild(line)
    while (terminalLog.children.length > maxLines) {
      terminalLog.removeChild(terminalLog.firstChild!)
    }
  }

  pushLine({ type: 'dim', text: 'watchllm kernel online. enforcing ruleset v0.1.0' })
  pushLine({ type: 'dim', text: 'listening on onWillSaveTextDocument...' })

  setInterval(() => {
    pushLine(events[idx % events.length])
    idx++
  }, 900 + Math.random() * 700)
}

// ─── HERO PARTICLE FIELD ──────────────────────────────────
const particleCanvas = document.getElementById('hero-particles')
if (particleCanvas) {
  const canvas = document.createElement('canvas')
  particleCanvas.appendChild(canvas)
  const ctx = canvas.getContext('2d')
  if (ctx) {
    let particles: { x: number; y: number; vx: number; vy: number; life: number; maxLife: number; char: string }[] = []
    const chars = '01'

    function resize() {
      canvas.width = particleCanvas!.clientWidth
      canvas.height = particleCanvas!.clientHeight
    }
    resize()
    window.addEventListener('resize', resize)

    function spawnParticle() {
      return {
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: 0, // No horizontal drift for matrix
        vy: Math.random() * 0.4 + 0.3, // Falling DOWN, slow reading speed
        life: 0,
        maxLife: 300 + Math.random() * 200, // Longer life since they move slower
        char: chars[Math.floor(Math.random() * chars.length)],
      }
    }

    for (let i = 0; i < 50; i++) {
      particles.push(spawnParticle())
    }

    function animate() {
      if (!ctx || !canvas) return
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.font = '12px "JetBrains Mono", monospace' // Slightly larger
      ctx.textAlign = 'center'

      particles = particles.filter(p => p.life < p.maxLife)
      while (particles.length < 50) {
        particles.push(spawnParticle())
      }

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        p.life++

        // Occasionally switch characters like real matrix
        if (Math.random() < 0.05) {
            p.char = chars[Math.floor(Math.random() * chars.length)];
        }

        const alpha = 1 - p.life / p.maxLife
        ctx.fillStyle = `rgba(204, 255, 0, ${alpha * 0.6})` // Brighter
        ctx.fillText(p.char, p.x, p.y)

        // Reset if it falls off the BOTTOM
        if (p.y > canvas.height + 10) {
          p.y = -10
          p.life = 0
          p.maxLife = 300 + Math.random() * 200
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
  const baseVal = 8472
  function updateCounter() {
    const val = baseVal + Math.floor((Date.now() / 1000) * 0.07)
    statBlocked!.textContent = val.toLocaleString()
    setTimeout(updateCounter, 2000 + Math.random() * 4000)
  }
  updateCounter()
}

// ─── SCROLL REVEAL ────────────────────────────────────────
const revealEls = document.querySelectorAll('.reveal')
if (revealEls.length) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
          observer.unobserve(entry.target)
        }
      }
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  )
  revealEls.forEach(el => observer.observe(el))
}

// ─── SMOOTH SCROLLING (INSTANT FOR BRUTALIST FEEL) ────────
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', (e) => {
    e.preventDefault()
    const target = e.currentTarget as HTMLAnchorElement
    const targetId = target.getAttribute('href')
    if (targetId) {
      const el = document.querySelector(targetId)
      if (el) {
        el.scrollIntoView({ behavior: 'auto' })
      }
    }
  })
})

// ─── NAV SCROLL EFFECT ────────────────────────────────────
const navbar = document.getElementById('navbar')
window.addEventListener('scroll', () => {
  if (navbar) {
    navbar.style.borderBottomColor = window.scrollY > 100 ? 'var(--accent)' : 'var(--border)'
  }
})

// ─── RANDOM GLITCH ON HERO TITLE ──────────────────────────
import React from 'react'
import { createRoot } from 'react-dom/client'
import GlitchText from './GlitchText'

const reactHeroRoot = document.getElementById('react-hero-root')
if (reactHeroRoot) {
  const root = createRoot(reactHeroRoot)
  root.render(
    React.createElement(
      'h1',
      {
        className: 'hero-title brutal-text',
        style: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }
      },
      React.createElement('span', { className: 'hero-line hero-line--top' }, 'YOUR AI AGENT'),
      React.createElement('span', { className: 'hero-title-strike hero-line hero-line--strike' }, 'IS YOUR CO-PILOT'),
      React.createElement(GlitchText, {
        text: 'IS A FUCKING LIAR.',
        speed: 0.5,
        enableShadows: true,
        enableOnHover: false,
        className: 'hero-title-real hero-line hero-line--real'
      })
    )
  )
}

// ─── CONSOLE EASTER EGG ───────────────────────────────────
console.log(
  '%cWATCHLLM%c — %cYOU FOUND THE CONSOLE. YOUR AGENT PROBABLY DID TOO.%c',
  'color: #ccff00; font-size: 20px; font-weight: bold;',
  '',
  'color: #ff3333; font-weight: bold;',
  ''
)
console.log(
  '%c>%c pip install watchllm',
  'color: #ccff00;',
  'color: #fff;'
)
