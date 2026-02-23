// Hash-based router
const routes = {
    "": DashboardPage,
    "settings": SettingsPage,
    "movies": MoviesPage,
    "movie": MoviePage,
    "shows": ShowsPage,
    "episodes": EpisodesPage,
    "episode": EpisodePage,
};

function getRoute() {
    const hash = location.hash.replace("#/", "") || "";
    const parts = hash.split("/");
    const page = parts[0] || "";
    const id = parts[1] || null;
    return { page, id };
}

function updateNav(page) {
    document.querySelectorAll("nav a[data-nav]").forEach(a => {
        const nav = a.getAttribute("data-nav");
        a.classList.toggle("active", nav === page || (nav === "dashboard" && page === ""));
    });
}

async function navigate() {
    const { page, id } = getRoute();
    const app = document.getElementById("app");
    updateNav(page);

    const handler = routes[page];
    if (handler) {
        app.innerHTML = '<p aria-busy="true">Loading...</p>';
        try {
            await handler(app, id);
        } catch (err) {
            app.innerHTML = `<article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        }
    } else {
        app.innerHTML = "<article><p>Page not found.</p></article>";
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

window.addEventListener("hashchange", navigate);
window.addEventListener("DOMContentLoaded", navigate);
