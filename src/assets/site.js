const $ = (sel, root = document) => root.querySelector(sel);

// Header: subtle style change after scroll
(function headerScroll() {
  const header = $('[data-header]');
  if (!header) return;

  const onScroll = () => {
    header.classList.toggle('is-scrolled', window.scrollY > 8);
  };

  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
})();

// Mobile nav
(function mobileNav() {
  const toggle = $('[data-nav-toggle]');
  const nav = $('[data-site-nav]');
  if (!toggle || !nav) return;

  const setOpen = (open) => {
    document.documentElement.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  toggle.addEventListener('click', () => {
    const isOpen = document.documentElement.classList.contains('nav-open');
    setOpen(!isOpen);
  });

  // Close on nav click (mobile)
  nav.addEventListener('click', (e) => {
    const a = e.target.closest('a');
    if (!a) return;
    setOpen(false);
  });

  // Close on Escape
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setOpen(false);
  });
})();

// Click pulse (meaningful interaction feedback)
(function clickPulse() {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
  if (reduced) return;

  const sel = 'a.btn, button.btn, .site-nav a, a.chip, [data-pulse]';
  const els = Array.from(document.querySelectorAll(sel));
  if (!els.length) return;

  for (const el of els) {
    el.addEventListener('click', () => {
      el.classList.remove('is-pulsing');
      // Force reflow so the animation can restart on rapid clicks.
      void el.offsetWidth;
      el.classList.add('is-pulsing');
      window.setTimeout(() => el.classList.remove('is-pulsing'), 520);
    });
  }
})();

// Reveal-on-scroll (respect reduced motion)
(function revealOnScroll() {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
  const els = Array.from(document.querySelectorAll('.reveal'));
  if (!els.length) return;

  if (reduced || !('IntersectionObserver' in window)) {
    els.forEach((el) => el.classList.add('is-in'));
    return;
  }

  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      }
    },
    { rootMargin: '0px 0px -10% 0px', threshold: 0.1 }
  );

  els.forEach((el) => io.observe(el));
})();
