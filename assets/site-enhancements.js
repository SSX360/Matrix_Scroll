/** Scroll-driven reveal + optional reduced-motion respect */
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll(".reveal-up").forEach((el) => el.classList.add("is-visible"))
    return
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible")
          observer.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.08, rootMargin: "0px 0px -48px 0px" },
  )

  document.querySelectorAll(".reveal-up").forEach((el) => observer.observe(el))
})()
