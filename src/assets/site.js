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
