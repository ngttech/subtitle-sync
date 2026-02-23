// Movies list page — searchable table
async function MoviesPage(container) {
    container.innerHTML = `
        <h2>Movies</h2>
        <div class="search-bar">
            <input type="search" id="movie-search" placeholder="Search movies...">
            <button type="button" id="movie-search-btn">Search</button>
        </div>
        <article aria-busy="true">Loading movies...</article>
    `;

    const doSearch = async (query) => {
        const tableContainer = container.querySelector("article") || container;
        const param = query ? `?q=${encodeURIComponent(query)}` : "";
        try {
            const movies = await API.get(`/movies${param}`);
            if (movies.length === 0) {
                tableContainer.outerHTML = "<article><p>No movies found.</p></article>";
                return;
            }
            tableContainer.outerHTML = `
                <table role="grid">
                    <thead>
                        <tr><th>Title</th><th>Year</th><th>File</th></tr>
                    </thead>
                    <tbody>
                        ${movies.map(m => `
                            <tr onclick="location.hash='#/movie/${m.id}'">
                                <td>${escapeHtml(m.title)}</td>
                                <td>${m.year || ""}</td>
                                <td class="file-path">${escapeHtml(m.file_path || "No file")}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        } catch (err) {
            tableContainer.outerHTML = `<article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        }
    };

    document.getElementById("movie-search-btn").addEventListener("click", () => {
        doSearch(document.getElementById("movie-search").value);
    });
    document.getElementById("movie-search").addEventListener("keydown", (e) => {
        if (e.key === "Enter") doSearch(e.target.value);
    });

    await doSearch("");
}
