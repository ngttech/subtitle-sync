// Episode detail — track viewer, external subs, sync trigger (same UI as movie)
async function EpisodePage(container, episodeId) {
    if (!episodeId) { container.innerHTML = "<p>No episode selected.</p>"; return; }

    container.innerHTML = '<h2>Episode</h2><article aria-busy="true">Loading episode details...</article>';

    let episode;
    try {
        episode = await API.get(`/episodes/${episodeId}`);
    } catch (err) {
        container.innerHTML = `<h2>Episode</h2><article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        return;
    }

    const epLabel = `S${String(episode.season_number).padStart(2, "0")}E${String(episode.episode_number).padStart(2, "0")}`;
    const defaultLang = window._appDefaults?.default_language || "";

    container.innerHTML = `
        <h2>${escapeHtml(episode.series_title)} — ${epLabel}: ${escapeHtml(episode.title)}</h2>
        <p class="file-path">${escapeHtml(episode.file_path)}</p>

        <article>
            <header><strong>Embedded Subtitle Tracks</strong></header>
            <div id="tracks-area" aria-busy="true">Loading tracks...</div>
        </article>

        <article>
            <header><strong>External Subtitle (to sync)</strong></header>
            <div class="sub-source-tabs">
                <button type="button" class="active" id="tab-folder">From Folder</button>
                <button type="button" id="tab-upload">Upload File</button>
            </div>
            <div id="folder-subs-area" aria-busy="true">Scanning folder...</div>
            <div id="upload-area" class="hidden">
                <input type="file" id="sub-upload" accept=".srt,.ass,.ssa,.vtt,.sub">
            </div>
        </article>

        <article>
            <header><strong>Sync</strong></header>
            <div class="grid">
                <label>Sync Mode
                    <select id="sync-mode">
                        <option value="sub-to-sub">Sub-to-Sub (recommended)</option>
                        <option value="sub-to-audio">Sub-to-Audio (fallback)</option>
                    </select>
                </label>
                <label>Sync Engine
                    <select id="sync-engine">
                        <option value="ffsubsync">ffsubsync</option>
                        <option value="alass">alass (faster, cross-language)</option>
                    </select>
                </label>
                <label>Output Language Tag
                    <input type="text" id="output-lang" placeholder="e.g. es, pt" value="${escapeHtml(defaultLang)}">
                </label>
            </div>
            <button type="button" id="sync-btn">Sync Subtitles</button>
            <div id="sync-result"></div>
        </article>

        <a href="#/episodes/${episode.series_id}">&larr; Back to Episodes</a>
    `;

    // Load tracks
    const tracksArea = document.getElementById("tracks-area");
    try {
        const tracks = await API.get(`/episodes/${episodeId}/tracks`);
        tracksArea.removeAttribute("aria-busy");
        renderTracks(tracksArea, tracks, episode.file_path, async () => {
            try {
                const subs = await API.get(`/episodes/${episodeId}/external-subs`);
                renderExternalSubs(document.getElementById("folder-subs-area"), subs);
            } catch (_) {}
        });
    } catch (err) {
        tracksArea.removeAttribute("aria-busy");
        tracksArea.innerHTML = `<p>Error: ${escapeHtml(err.message)}</p>`;
    }

    // Load external subs
    const folderSubsArea = document.getElementById("folder-subs-area");
    try {
        const externalSubs = await API.get(`/episodes/${episodeId}/external-subs`);
        folderSubsArea.removeAttribute("aria-busy");
        renderExternalSubs(folderSubsArea, externalSubs);
    } catch (err) {
        folderSubsArea.removeAttribute("aria-busy");
        folderSubsArea.innerHTML = `<p>Error: ${escapeHtml(err.message)}</p>`;
    }

    // Tab switching
    document.getElementById("tab-folder").addEventListener("click", () => {
        document.getElementById("tab-folder").classList.add("active");
        document.getElementById("tab-upload").classList.remove("active");
        document.getElementById("folder-subs-area").classList.remove("hidden");
        document.getElementById("upload-area").classList.add("hidden");
    });
    document.getElementById("tab-upload").addEventListener("click", () => {
        document.getElementById("tab-upload").classList.add("active");
        document.getElementById("tab-folder").classList.remove("active");
        document.getElementById("upload-area").classList.remove("hidden");
        document.getElementById("folder-subs-area").classList.add("hidden");
    });

    // Sync button
    document.getElementById("sync-btn").addEventListener("click", async () => {
        const resultDiv = document.getElementById("sync-result");
        const syncBtn = document.getElementById("sync-btn");

        const selectedTrack = document.querySelector('input[name="ref-track"]:checked');
        const selectedSub = document.querySelector('input[name="ext-sub"]:checked');
        const uploadedFile = document.getElementById("sub-upload").files[0];
        const syncMode = document.getElementById("sync-mode").value;
        const syncEngine = document.getElementById("sync-engine").value;
        const outputLang = document.getElementById("output-lang").value;

        if (syncMode === "sub-to-sub" && !selectedTrack) {
            resultDiv.innerHTML = '<p class="sync-result error">Please select a reference track.</p>';
            return;
        }
        if (!selectedSub && !uploadedFile) {
            resultDiv.innerHTML = '<p class="sync-result error">Please select or upload an external subtitle.</p>';
            return;
        }

        syncBtn.setAttribute("aria-busy", "true");
        syncBtn.disabled = true;
        resultDiv.innerHTML = '<p aria-busy="true">Syncing... this may take a minute.</p>';

        const formData = new FormData();
        formData.append("video_path", episode.file_path);
        formData.append("sync_mode", syncMode);
        formData.append("sync_engine", syncEngine);
        formData.append("output_language", outputLang);

        if (selectedTrack) {
            formData.append("reference_track_index", selectedTrack.value);
        }
        if (uploadedFile) {
            formData.append("uploaded_sub", uploadedFile);
        } else if (selectedSub) {
            formData.append("external_sub_path", selectedSub.value);
        }

        try {
            const result = await API.postForm("/sync", formData);
            if (result.success) {
                resultDiv.innerHTML = `
                    <div class="sync-result success">
                        <p><strong>Sync complete!</strong></p>
                        <p>Offset: ${result.offset_ms.toFixed(0)} ms</p>
                        <p class="file-path">Output: ${escapeHtml(result.output_path)}</p>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `<div class="sync-result error"><p>${escapeHtml(result.message)}</p></div>`;
            }
        } catch (err) {
            resultDiv.innerHTML = `<div class="sync-result error"><p>Error: ${escapeHtml(err.message)}</p></div>`;
        } finally {
            syncBtn.removeAttribute("aria-busy");
            syncBtn.disabled = false;
        }
    });
}
