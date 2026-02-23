// Settings page — configure Radarr/Sonarr, path mappings, test connections
async function SettingsPage(container) {
    container.innerHTML = '<h2>Settings</h2><article aria-busy="true">Loading settings...</article>';

    let settings;
    try {
        settings = await API.get("/settings");
    } catch (err) {
        container.innerHTML = `<h2>Settings</h2><article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        return;
    }

    const mappings = settings.path_mappings || [];

    container.innerHTML = `
        <h2>Settings</h2>
        <form id="settings-form">
            <article>
                <header><strong>Radarr</strong></header>
                <label>URL
                    <input type="url" name="radarr_url" value="${escapeHtml(settings.radarr_url)}" placeholder="http://localhost:7878">
                </label>
                <label>API Key
                    <input type="password" name="radarr_api_key" value="" placeholder="${settings.radarr_api_key_set ? '(saved — leave blank to keep)' : 'Enter API key'}">
                </label>
                <button type="button" id="test-radarr" class="outline">Test Connection</button>
                <small id="radarr-result"></small>
            </article>

            <article>
                <header><strong>Sonarr</strong></header>
                <label>URL
                    <input type="url" name="sonarr_url" value="${escapeHtml(settings.sonarr_url)}" placeholder="http://localhost:8989">
                </label>
                <label>API Key
                    <input type="password" name="sonarr_api_key" value="" placeholder="${settings.sonarr_api_key_set ? '(saved — leave blank to keep)' : 'Enter API key'}">
                </label>
                <button type="button" id="test-sonarr" class="outline">Test Connection</button>
                <small id="sonarr-result"></small>
            </article>

            <article>
                <header><strong>Path Mappings</strong></header>
                <p><small>Map container/remote paths to local paths. Leave empty if your mounts match.</small></p>
                <div id="path-mappings">
                    ${mappings.map((m, i) => pathMappingRow(i, m.from_path, m.to_path)).join("")}
                </div>
                <button type="button" id="add-mapping" class="outline secondary">+ Add Mapping</button>
            </article>

            <article>
                <header><strong>Cache</strong></header>
                <button type="button" id="refresh-cache" class="outline">Refresh Library Cache</button>
                <small id="cache-result"></small>
            </article>

            <button type="submit">Save Settings</button>
            <small id="save-result"></small>
        </form>
    `;

    let mappingCount = mappings.length;

    document.getElementById("add-mapping").addEventListener("click", () => {
        const div = document.getElementById("path-mappings");
        div.insertAdjacentHTML("beforeend", pathMappingRow(mappingCount++, "", ""));
    });

    document.getElementById("path-mappings").addEventListener("click", (e) => {
        if (e.target.classList.contains("remove-mapping")) {
            e.target.closest(".path-mapping-row").remove();
        }
    });

    document.getElementById("test-radarr").addEventListener("click", async () => {
        const el = document.getElementById("radarr-result");
        el.textContent = "Testing...";
        const form = document.getElementById("settings-form");
        try {
            const res = await API.post("/settings/test", {
                service: "radarr",
                url: form.radarr_url.value,
                api_key: form.radarr_api_key.value || "(current)",
            });
            el.textContent = res.message;
        } catch (err) {
            el.textContent = err.message;
        }
    });

    document.getElementById("test-sonarr").addEventListener("click", async () => {
        const el = document.getElementById("sonarr-result");
        el.textContent = "Testing...";
        const form = document.getElementById("settings-form");
        try {
            const res = await API.post("/settings/test", {
                service: "sonarr",
                url: form.sonarr_url.value,
                api_key: form.sonarr_api_key.value || "(current)",
            });
            el.textContent = res.message;
        } catch (err) {
            el.textContent = err.message;
        }
    });

    document.getElementById("refresh-cache").addEventListener("click", async () => {
        const el = document.getElementById("cache-result");
        el.textContent = "Refreshing...";
        try {
            await API.post("/cache/refresh", {});
            el.textContent = "Cache cleared. Next page load will fetch fresh data.";
        } catch (err) {
            el.textContent = err.message;
        }
    });

    document.getElementById("settings-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const el = document.getElementById("save-result");
        el.textContent = "Saving...";

        const form = e.target;
        const pathMappingRows = document.querySelectorAll(".path-mapping-row");
        const path_mappings = [];
        pathMappingRows.forEach(row => {
            const from_path = row.querySelector(".mapping-from").value.trim();
            const to_path = row.querySelector(".mapping-to").value.trim();
            if (from_path || to_path) {
                path_mappings.push({ from_path, to_path });
            }
        });

        try {
            await API.put("/settings", {
                radarr_url: form.radarr_url.value,
                radarr_api_key: form.radarr_api_key.value,
                sonarr_url: form.sonarr_url.value,
                sonarr_api_key: form.sonarr_api_key.value,
                path_mappings,
            });
            el.textContent = "Settings saved!";
        } catch (err) {
            el.textContent = "Error: " + err.message;
        }
    });
}

function pathMappingRow(index, from_path, to_path) {
    return `
        <div class="path-mapping-row">
            <input class="mapping-from" type="text" value="${escapeHtml(from_path)}" placeholder="From path (e.g. /movies)">
            <span>&rarr;</span>
            <input class="mapping-to" type="text" value="${escapeHtml(to_path)}" placeholder="To path (e.g. D:\\Movies)">
            <button type="button" class="remove-mapping outline secondary">&times;</button>
        </div>
    `;
}
