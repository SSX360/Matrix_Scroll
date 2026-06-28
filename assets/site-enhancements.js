/** Scroll-driven reveal + staggered children + reduced-motion respect */
(function () {
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches

  if (reduced) {
    document.querySelectorAll(".reveal-up, .reveal-stagger").forEach(function (el) {
      el.classList.add("is-visible")
    })
    return
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return
        var target = entry.target
        if (target.classList.contains("reveal-stagger")) {
          target.classList.add("is-visible")
          target.querySelectorAll(".panel, .flow-step, .status-card, .pricing-card, .cta-panel").forEach(function (child, i) {
            child.style.transitionDelay = i * 80 + "ms"
            child.classList.add("is-visible")
          })
        } else {
          target.classList.add("is-visible")
        }
        observer.unobserve(target)
      })
    },
    { threshold: 0.08, rootMargin: "0px 0px -48px 0px" },
  )

  document.querySelectorAll(".reveal-up, .reveal-stagger").forEach(function (el) {
    observer.observe(el)
  })
})()
