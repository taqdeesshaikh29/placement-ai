// Keep the footer year current
document.getElementById("year").textContent = new Date().getFullYear();

// Close the mobile menu after clicking a nav link
document.querySelectorAll(".navbar-nav .nav-link").forEach((link) => {
  link.addEventListener("click", () => {
    const menu = document.getElementById("nav");
    if (menu.classList.contains("show")) bootstrap.Collapse.getOrCreateInstance(menu).hide();
  });
});
