// Episodes list page — grouped by season
async function EpisodesPage(container, seriesId) {
    if (!seriesId) { container.innerHTML = "<p>No series selected.</p>"; return; }

    container.innerHTML = '<h2>Episodes</h2><article aria-busy="true">Loading episodes...</article>';

    let series, episodes;
    try {
        [series, episodes] = await Promise.all([
            API.get(`/shows/${seriesId}`),
            API.get(`/shows/${seriesId}/episodes`),
        ]);
    } catch (err) {
        container.innerHTML = `<h2>Episodes</h2><article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        return;
    }

    // Group by season
    const seasons = {};
    episodes.forEach(ep => {
        const sn = ep.season_number;
        if (!seasons[sn]) seasons[sn] = [];
        seasons[sn].push(ep);
    });

    const seasonKeys = Object.keys(seasons).sort((a, b) => Number(a) - Number(b));

    let html = `
        <h2>${escapeHtml(series.title)}</h2>
        <a href="#/shows">&larr; Back to Shows</a>
    `;

    if (seasonKeys.length === 0) {
        html += "<article><p>No episodes with files found.</p></article>";
    } else {
        seasonKeys.forEach(sn => {
            html += `<div class="season-group"><h3>Season ${sn}</h3>`;
            html += `<table role="grid"><thead><tr><th>Ep</th><th>Title</th><th>File</th></tr></thead><tbody>`;
            seasons[sn]
                .sort((a, b) => a.episode_number - b.episode_number)
                .forEach(ep => {
                    html += `
                        <tr onclick="location.hash='#/episode/${ep.id}'">
                            <td>${ep.episode_number}</td>
                            <td>${escapeHtml(ep.title)}</td>
                            <td class="file-path">${escapeHtml(ep.file_path || "No file")}</td>
                        </tr>
                    `;
                });
            html += "</tbody></table></div>";
        });
    }

    container.innerHTML = html;
}
