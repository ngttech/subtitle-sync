// TV Shows list page — searchable table
async function ShowsPage(container) {
    container.innerHTML = `
        <h2>TV Shows</h2>
        <div class="search-bar">
            <input type="search" id="show-search" placeholder="Search shows...">
            <button type="button" id="show-search-btn">Search</button>
        </div>
        <article aria-busy="true">Loading shows...</article>
    `;

    const doSearch = async (query) => {
        const tableContainer = container.querySelector("article") || container;
        const param = query ? `?q=${encodeURIComponent(query)}` : "";
        try {
            const shows = await API.get(`/shows${param}`);
            if (shows.length === 0) {
                tableContainer.outerHTML = "<article><p>No shows found.</p></article>";
                return;
            }
            tableContainer.outerHTML = `
                <table role="grid">
                    <thead>
                        <tr><th>Title</th><th>Year</th><th>Seasons</th><th>Episodes</th></tr>
                    </thead>
                    <tbody>
                        ${shows.map(s => `
                            <tr onclick="location.hash='#/episodes/${s.id}'">
                                <td>${escapeHtml(s.title)}</td>
                                <td>${s.year || ""}</td>
                                <td>${s.season_count}</td>
                                <td>${s.episode_count}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        } catch (err) {
            tableContainer.outerHTML = `<article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        }
    };

    document.getElementById("show-search-btn").addEventListener("click", () => {
        doSearch(document.getElementById("show-search").value);
    });
    document.getElementById("show-search").addEventListener("keydown", (e) => {
        if (e.key === "Enter") doSearch(e.target.value);
    });

    await doSearch("");
}
