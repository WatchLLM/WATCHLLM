import './style.css'

// ─── INSTALL COPY BOXES ───────────────────────────────────
function setupInstallBox(id: string) {
  const box = document.getElementById(id)
  if (!box) return
  const feedback = box.querySelector('.copy-feedback')
  box.addEventListener('click', () => {
    navigator.clipboard.writeText('pip install watchllm-cli')
    if (feedback) {
      feedback.classList.add('show')
      setTimeout(() => feedback.classList.remove('show'), 1800)
    }
  })
}
setupInstallBox('install-box')
setupInstallBox('install-box-2')

// ─── ASCII GLITCH ─────────────────────────────────────────
const asciiArt = document.getElementById('ascii-art') as HTMLPreElement | null
if (asciiArt && asciiArt.textContent) {
  const originalText = asciiArt.textContent
  const glitchChars = '░▒▓█▀▄▌▐■□▪▫●○◘◙◦☰☱☲☳☴☵☶☷⚡⌁⌂⎔⎓⏣⬡⬢⬟⬠⬡'

  setInterval(() => {
    if (Math.random() > 0.08) return

    const glitched = originalText.split('')
    const numGlitches = Math.floor(Math.random() * 25) + 5
    for (let i = 0; i < numGlitches; i++) {
      const pos = Math.floor(Math.random() * glitched.length)
      if (glitched[pos] !== '\n' && glitched[pos] !== ' ') {
        glitched[pos] = glitchChars[Math.floor(Math.random() * glitchChars.length)]
      }
    }
    asciiArt.textContent = glitched.join('')
    asciiArt.classList.add('glitching')

    setTimeout(() => {
      asciiArt.textContent = originalText
      asciiArt.classList.remove('glitching')
    }, 40 + Math.random() * 120)
  }, 180)
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
        vx: (Math.random() - 0.5) * 0.3,
        vy: -Math.random() * 0.5 - 0.2,
        life: 0,
        maxLife: 80 + Math.random() * 160,
        char: chars[Math.floor(Math.random() * chars.length)],
      }
    }

    for (let i = 0; i < 40; i++) {
      particles.push(spawnParticle())
    }

    function animate() {
      if (!ctx || !canvas) return
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.font = '10px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'

      particles = particles.filter(p => p.life < p.maxLife)
      while (particles.length < 40) {
        particles.push(spawnParticle())
      }

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        p.life++

        const alpha = 1 - p.life / p.maxLife
        ctx.fillStyle = `rgba(204, 255, 0, ${alpha * 0.4})`
        ctx.fillText(p.char, p.x, p.y)

        if (p.y < -10) {
          p.y = canvas.height + 10
          p.life = 0
          p.maxLife = 80 + Math.random() * 160
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
    const formatted = val.toLocaleString()
    statBlocked!.textContent = formatted
    requestAnimationFrame(() => {
      setTimeout(updateCounter, 2000 + Math.random() * 4000)
    })
  }
  updateCounter()
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
  const currentScroll = window.scrollY
  if (navbar) {
    if (currentScroll > 100) {
      navbar.style.borderBottomColor = 'var(--accent)'
    } else {
      navbar.style.borderBottomColor = 'var(--border)'
    }
  }
})

// ─── RANDOM GLITCH ON HERO TITLE ──────────────────────────
const heroTitle = document.querySelector('.hero-title') as HTMLElement | null
if (heroTitle) {
  setInterval(() => {
    if (Math.random() > 0.15) return
    heroTitle.style.transform = `skewX(${(Math.random() - 0.5) * 2}deg) translateX(${(Math.random() - 0.5) * 4}px)`
    setTimeout(() => {
      heroTitle.style.transform = ''
    }, 60 + Math.random() * 100)
  }, 4000 + Math.random() * 3000)
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
  '%c>%c pip install watchllm-cli',
  'color: #ccff00;',
  'color: #fff;'
)
