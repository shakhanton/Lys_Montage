(function () {
  var cloud = document.querySelector('[data-logo-cloud]');
  if (!cloud) return;

  var chips = Array.prototype.slice.call(cloud.querySelectorAll('.logo-chip'));
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)');

  chips.forEach(function (chip) {
    chip.style.setProperty('--delay', (Math.random() * 5).toFixed(2) + 's');
    chip.style.setProperty('--dur', (6 + Math.random() * 3).toFixed(2) + 's');
    chip.style.setProperty('--r', (Math.random() * 2.4 - 1.2).toFixed(2) + 'deg');
  });

  var RADIUS = 150;
  var PULL = 0.3;
  var frame = null;

  function settle() {
    chips.forEach(function (chip) {
      chip.style.setProperty('--mx', '0px');
      chip.style.setProperty('--my', '0px');
    });
  }

  function track(e) {
    if (frame) return;
    frame = requestAnimationFrame(function () {
      frame = null;
      chips.forEach(function (chip) {
        var b = chip.getBoundingClientRect();
        var dx = e.clientX - (b.left + b.width / 2);
        var dy = e.clientY - (b.top + b.height / 2);
        var dist = Math.hypot(dx, dy);
        if (dist > RADIUS) {
          chip.style.setProperty('--mx', '0px');
          chip.style.setProperty('--my', '0px');
          return;
        }
        var force = (1 - dist / RADIUS) * PULL;
        chip.style.setProperty('--mx', (dx * force).toFixed(1) + 'px');
        chip.style.setProperty('--my', (dy * force).toFixed(1) + 'px');
      });
    });
  }

  if (!calm.matches) {
    cloud.addEventListener('mousemove', track);
    cloud.addEventListener('mouseleave', settle);
  }
  calm.addEventListener('change', function (e) {
    if (e.matches) {
      cloud.removeEventListener('mousemove', track);
      settle();
    } else {
      cloud.addEventListener('mousemove', track);
    }
  });
})();

(function () {
  var track = document.querySelector('[data-carousel]');
  if (!track) return;

  var prev = document.querySelector('[data-carousel-prev]');
  var next = document.querySelector('[data-carousel-next]');

  function step() {
    var card = track.firstElementChild;
    if (!card) return track.clientWidth;
    return card.getBoundingClientRect().width + 24;
  }

  function syncButtons() {
    var max = track.scrollWidth - track.clientWidth - 2;
    prev.disabled = track.scrollLeft <= 2;
    next.disabled = track.scrollLeft >= max;
  }

  prev.addEventListener('click', function () {
    track.scrollBy({ left: -step(), behavior: 'smooth' });
  });
  next.addEventListener('click', function () {
    track.scrollBy({ left: step(), behavior: 'smooth' });
  });

  track.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); next.click(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); prev.click(); }
  });

  track.addEventListener('scroll', syncButtons, { passive: true });
  window.addEventListener('resize', syncButtons);
  syncButtons();
})();
