(function () {
  const root = document.documentElement;
  const btn = document.getElementById("theme-toggle");
  const stored = localStorage.getItem("theme");

  if (stored === "light") {
    root.setAttribute("data-theme", "light");
    if (btn) btn.textContent = "☀";
  }

  if (btn) {
    btn.addEventListener("click", () => {
      const isLight = root.getAttribute("data-theme") === "light";
      if (isLight) {
        root.removeAttribute("data-theme");
        localStorage.setItem("theme", "dark");
        btn.textContent = "☾";
      } else {
        root.setAttribute("data-theme", "light");
        localStorage.setItem("theme", "light");
        btn.textContent = "☀";
      }
    });
  }

  // Highlight active sidebar link on scroll
  const sections = document.querySelectorAll("section.topic");
  const links = document.querySelectorAll(".sidebar a");

  if (sections.length && links.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            links.forEach((a) => {
              a.classList.toggle("active", a.getAttribute("href") === "#" + id);
            });
          }
        });
      },
      { rootMargin: "-20% 0px -60% 0px" }
    );
    sections.forEach((s) => observer.observe(s));
  }
})();
