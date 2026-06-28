(function () {
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script")
      s.src = src
      s.onload = resolve
      s.onerror = reject
      document.head.appendChild(s)
    })
  }

  function runEntrance(onDone) {
    var el = document.getElementById("ap2-cinematic")
    if (!el || reduced) {
      if (onDone) onDone()
      return
    }

    var label = el.querySelector(".ap2-cinematic-label")
    var line = el.querySelector(".ap2-cinematic-line")
    if (!label || !line) {
      el.remove()
      if (onDone) onDone()
      return
    }

    loadScript("https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js")
      .then(function () {
        var tl = gsap.timeline({
          onComplete: function () {
            el.classList.add("is-done")
            setTimeout(function () {
              el.remove()
              if (onDone) onDone()
            }, 520)
          },
        })
        tl.to(label, { opacity: 1, duration: 0.8, ease: "power2.out" })
          .to(line, { scaleX: 1, duration: 1, ease: "power2.inOut" }, 0.3)
          .to(el, { opacity: 0, duration: 0.5, ease: "power2.in", delay: 0.3 })
      })
      .catch(function () {
        el.remove()
        if (onDone) onDone()
      })
  }

  function initMotion() {
    if (reduced) return

    Promise.all([
      loadScript("https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"),
      loadScript("https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"),
    ])
      .then(function () {
        gsap.registerPlugin(ScrollTrigger)

        var heroImg = document.querySelector(".ap2-hero-visual img")
        var heroSection = document.querySelector(".ap2-hero")
        if (heroImg && heroSection) {
          gsap.to(heroImg, {
            y: -40,
            ease: "none",
            scrollTrigger: {
              trigger: heroSection,
              start: "top top",
              end: "bottom top",
              scrub: 0.8,
            },
          })
        }

        gsap.utils.toArray(".ap2-step-card").forEach(function (card, i) {
          gsap.to(card, {
            opacity: 1,
            y: 0,
            duration: 0.7,
            ease: "power2.out",
            delay: i * 0.08,
            scrollTrigger: { trigger: card, start: "top 85%" },
          })
        })

        var parallaxImg = document.querySelector(".ap2-parallax-break img")
        var parallaxSection = document.querySelector(".ap2-parallax-break")
        if (parallaxImg && parallaxSection) {
          gsap.fromTo(
            parallaxImg,
            { scale: 1.15 },
            {
              scale: 1,
              ease: "none",
              scrollTrigger: {
                trigger: parallaxSection,
                start: "top bottom",
                end: "bottom top",
                scrub: 0.8,
              },
            },
          )
        }

        gsap.utils.toArray(".ap2-sec-item").forEach(function (item, i) {
          gsap.to(item, {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: "power2.out",
            delay: i * 0.06,
            scrollTrigger: { trigger: item, start: "top 88%" },
          })
        })

        gsap.utils.toArray(".ap2-reveal-block").forEach(function (block) {
          gsap.fromTo(
            block,
            { opacity: 0, y: 28 },
            {
              opacity: 1,
              y: 0,
              duration: 0.8,
              ease: "power2.out",
              scrollTrigger: { trigger: block, start: "top 82%" },
            },
          )
        })
      })
      .catch(function () {
        /* static fallbacks in CSS reduced-motion / no-js */
      })
  }

  function initHeroWords() {
    var words = document.querySelectorAll(".ap2-hero-word")
    var subs = document.querySelectorAll(".ap2-hero-sub")
    var img = document.querySelector(".ap2-hero-visual img")

    if (reduced) {
      words.forEach(function (w) {
        w.style.opacity = "1"
        w.style.transform = "none"
      })
      subs.forEach(function (s) {
        s.style.opacity = "1"
      })
      if (img) {
        img.style.opacity = "1"
        img.style.transform = "none"
      }
      return
    }

    runEntrance(function () {
      if (typeof gsap === "undefined") {
        words.forEach(function (w) {
          w.style.opacity = "1"
          w.style.transform = "none"
        })
        return
      }

      var tl = gsap.timeline()
      tl.to(words, {
        opacity: 1,
        y: 0,
        duration: 0.7,
        ease: "power2.out",
        stagger: 0.08,
      })
      if (img) {
        tl.to(img, { opacity: 1, scale: 1, duration: 1.2, ease: "power2.out" }, "-=0.5")
      }
      tl.to(subs, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out", stagger: 0.1 }, "-=0.8")
    })
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initHeroWords()
      initMotion()
    })
  } else {
    initHeroWords()
    initMotion()
  }
})()
