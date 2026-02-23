// Settings page — configure Radarr/Sonarr, path mappings, AI translation, test connections
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
                <header><strong>AI Translation</strong></header>
                <p><small>Configure an AI provider to enable subtitle translation (embedded track to external file).</small></p>
                <label>AI Provider
                    <select name="ai_provider">
                        <option value="" ${!settings.ai_provider ? 'selected' : ''}>None</option>
                        <option value="openai" ${settings.ai_provider === 'openai' ? 'selected' : ''}>OpenAI</option>
                        <option value="anthropic" ${settings.ai_provider === 'anthropic' ? 'selected' : ''}>Anthropic (Claude)</option>
                    </select>
                </label>
                <label>OpenAI API Key
                    <input type="password" name="openai_api_key" value="" placeholder="${settings.openai_api_key_set ? '(saved — leave blank to keep)' : 'Enter OpenAI API key'}">
                </label>
                <label>Anthropic API Key
                    <input type="password" name="anthropic_api_key" value="" placeholder="${settings.anthropic_api_key_set ? '(saved — leave blank to keep)' : 'Enter Anthropic API key'}">
                </label>
                <div class="grid">
                    <label>OpenAI Model
                        <select name="openai_model">
                            <option value="gpt-4o-mini" ${settings.openai_model === 'gpt-4o-mini' ? 'selected' : ''}>gpt-4o-mini</option>
                            <option value="gpt-4o" ${settings.openai_model === 'gpt-4o' ? 'selected' : ''}>gpt-4o</option>
                            <option value="gpt-5-mini" ${settings.openai_model === 'gpt-5-mini' ? 'selected' : ''}>gpt-5-mini</option>
                            <option value="gpt-5" ${settings.openai_model === 'gpt-5' ? 'selected' : ''}>gpt-5</option>
                        </select>
                    </label>
                    <label>Anthropic Model
                        <select name="anthropic_model">
                            <option value="claude-haiku-4-5-20251001" ${settings.anthropic_model === 'claude-haiku-4-5-20251001' ? 'selected' : ''}>claude-haiku-4-5-20251001</option>
                            <option value="claude-sonnet-4-5-20250929" ${settings.anthropic_model === 'claude-sonnet-4-5-20250929' ? 'selected' : ''}>claude-sonnet-4-5-20250929</option>
                        </select>
                    </label>
                </div>
                <label>Default Language
                    <input type="text" name="default_language" value="${escapeHtml(settings.default_language || '')}" placeholder="e.g. es, pt, fr (pre-fills language fields)">
                </label>
                <label>Translation Prompt
                    <textarea name="translation_prompt" rows="4" placeholder="You are a professional subtitle translator. Translate the following subtitle lines from {source_lang} to {target_lang}. You MUST output every line in {target_lang}. Return EXACTLY the same number of lines, one translation per line. Do NOT add line numbers, timestamps, or any extra text. Keep markup tags like <i>, </i>, <b>, </b> intact. Preserve empty lines as empty lines.">${escapeHtml(settings.translation_prompt || '')}</textarea>
                </label>
                <small>Use <code>{source_lang}</code> and <code>{target_lang}</code> as placeholders. Leave empty to use the default prompt.</small>
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
            const result = await API.put("/settings", {
                radarr_url: form.radarr_url.value,
                radarr_api_key: form.radarr_api_key.value,
                sonarr_url: form.sonarr_url.value,
                sonarr_api_key: form.sonarr_api_key.value,
                path_mappings,
                ai_provider: form.ai_provider.value,
                openai_api_key: form.openai_api_key.value,
                anthropic_api_key: form.anthropic_api_key.value,
                openai_model: form.openai_model.value,
                anthropic_model: form.anthropic_model.value,
                default_language: form.default_language.value,
                translation_prompt: form.translation_prompt.value,
            });
            window._appDefaults.default_language = result.default_language || "";
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
