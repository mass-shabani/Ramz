// Load coin SVG inline to preserve CSS animations
document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('coin-container');
  if (!container) return;
  
  fetch('/static/home/coin.svg')
    .then(response => {
      if (!response.ok) throw new Error('Failed to load SVG');
      return response.text();
    })
    .then(svgText => {
      container.innerHTML = svgText;
      const svg = container.querySelector('svg');
      if (svg) {
        svg.classList.add('coin-svg');
      }
    })
    .catch(err => console.error('Failed to load coin SVG:', err));
});