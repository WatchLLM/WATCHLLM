import './style.css'

// Brutal install copy
const installBox = document.getElementById('install-box');
if (installBox) {
  const feedback = installBox.querySelector('.copy-feedback');
  installBox.addEventListener('click', () => {
    navigator.clipboard.writeText('pip install watchllm-cli');
    if (feedback) {
      feedback.classList.add('show');
      setTimeout(() => {
        feedback.classList.remove('show');
      }, 1500);
    }
  });
}

// Intense glitch effect on the ASCII text
// We swap out characters randomly in the ASCII block to simulate data corruption
const asciiArt = document.querySelector('.ascii-art');
if (asciiArt && asciiArt.textContent) {
  const originalText = asciiArt.textContent;
  const chars = '░▒▓█><{}[]!@#$%^&*()_+-=';
  
  setInterval(() => {
    // Only glitch 10% of the time to keep the logo readable
    if (Math.random() > 0.1) return;
    
    let glitchedText = originalText.split('');
    // Glitch a random chunk of characters
    const numGlitches = Math.floor(Math.random() * 20);
    for (let i = 0; i < numGlitches; i++) {
      const pos = Math.floor(Math.random() * glitchedText.length);
      // Don't glitch newlines
      if (glitchedText[pos] !== '\n' && glitchedText[pos] !== ' ') {
        glitchedText[pos] = chars[Math.floor(Math.random() * chars.length)];
      }
    }
    
    asciiArt.textContent = glitchedText.join('');
    
    // Snap back to normal quickly
    setTimeout(() => {
      asciiArt.textContent = originalText;
    }, 50 + Math.random() * 150);
    
  }, 200);
}

// Smooth scrolling (instant for brutalist feel)
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', (e) => {
    e.preventDefault();
    const target = e.currentTarget as HTMLAnchorElement;
    const targetId = target.getAttribute('href');
    if (targetId) {
      const el = document.querySelector(targetId);
      if (el) {
        el.scrollIntoView({ behavior: 'auto' }); // 'auto' is instant, brutalist
      }
    }
  });
});
