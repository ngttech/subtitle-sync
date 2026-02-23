// Dashboard page — health status + quick actions
async function DashboardPage(container) {
    container.innerHTML = `
        <h2>Dashboard</h2>
        <article aria-busy="true">Checking system health...</article>
    `;

    try {
        const health = await API.get("/health");
        const tools = health.tools;

        container.innerHTML = `
            <h2>Dashboard</h2>
            <article>
                <header>
                    <strong>System Status:
                        <span class="status-badge ${health.status === 'ok' ? 'ok' : 'error'}">
                            ${health.status === 'ok' ? 'All Good' : 'Degraded'}
                        </span>
                    </strong>
                </header>
                <table>
                    <thead>
                        <tr><th>Tool</th><th>Status</th><th>Details</th></tr>
                    </thead>
                    <tbody>
                        ${toolRow("ffmpeg", tools.ffmpeg)}
                        ${toolRow("ffprobe", tools.ffprobe)}
                        ${toolRow("ffsubsync", tools.ffsubsync)}
                    </tbody>
                </table>
            </article>
            <div class="grid">
                <a href="#/movies" role="button">Browse Movies</a>
                <a href="#/shows" role="button">Browse TV Shows</a>
                <a href="#/settings" role="button" class="outline">Settings</a>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `
            <h2>Dashboard</h2>
            <article>
                <p>Failed to check health: ${escapeHtml(err.message)}</p>
                <p>Make sure the backend is running.</p>
            </article>
        `;
    }
}

function toolRow(name, info) {
    const status = info.available
        ? '<span class="status-badge ok">Available</span>'
        : '<span class="status-badge error">Missing</span>';
    const detail = info.version || info.path || "Not found";
    return `<tr><td>${name}</td><td>${status}</td><td class="file-path">${escapeHtml(detail)}</td></tr>`;
}
