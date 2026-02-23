// Movie detail — track viewer, external subs, sync trigger
async function MoviePage(container, movieId) {
    if (!movieId) { container.innerHTML = "<p>No movie selected.</p>"; return; }

    container.innerHTML = '<h2>Movie</h2><article aria-busy="true">Loading movie details...</article>';

    let movie;
    try {
        movie = await API.get(`/movies/${movieId}`);
    } catch (err) {
        container.innerHTML = `<h2>Movie</h2><article><p>Error: ${escapeHtml(err.message)}</p></article>`;
        return;
    }

    container.innerHTML = `
        <h2>${escapeHtml(movie.title)} <small>(${movie.year || ""})</small></h2>
        <p class="file-path">${escapeHtml(movie.file_path)}</p>

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
                <label>Output Language Tag
                    <input type="text" id="output-lang" placeholder="e.g. es, pt" value="">
                </label>
            </div>
            <button type="button" id="sync-btn">Sync Subtitles</button>
            <div id="sync-result"></div>
        </article>

        <a href="#/movies">&larr; Back to Movies</a>
    `;

    // Load tracks
    let tracks = [];
    try {
        tracks = await API.get(`/movies/${movieId}/tracks`);
        renderTracks(document.getElementById("tracks-area"), tracks);
    } catch (err) {
        document.getElementById("tracks-area").innerHTML = `<p>Error: ${escapeHtml(err.message)}</p>`;
    }

    // Load external subs
    let externalSubs = [];
    try {
        externalSubs = await API.get(`/movies/${movieId}/external-subs`);
        renderExternalSubs(document.getElementById("folder-subs-area"), externalSubs);
    } catch (err) {
        document.getElementById("folder-subs-area").innerHTML = `<p>Error: ${escapeHtml(err.message)}</p>`;
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
        formData.append("video_path", movie.file_path);
        formData.append("sync_mode", syncMode);
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

function renderTracks(container, tracks) {
    if (tracks.length === 0) {
        container.innerHTML = "<p>No embedded subtitle tracks found.</p>";
        return;
    }

    const hasPgsOnly = tracks.every(t => !t.text_based);

    let html = "";
    if (hasPgsOnly) {
        html += '<div class="pgs-warning">Only image-based (PGS) subtitle tracks found. These cannot be used as text references for sub-to-sub sync. Use sub-to-audio mode instead.</div>';
    }

    html += '<div class="track-list">';
    tracks.forEach(t => {
        const badges = [];
        if (t.default) badges.push("default");
        if (t.forced) badges.push("forced");
        if (!t.text_based) badges.push("image-based");

        html += `
            <div class="track-item">
                <label>
                    <input type="radio" name="ref-track" value="${t.index}" ${t.text_based ? "" : "disabled"}>
                    <span class="track-info">
                        #${t.index} — ${escapeHtml(t.language || "unknown")}
                        (${escapeHtml(t.codec)})
                        ${t.title ? " — " + escapeHtml(t.title) : ""}
                        ${badges.map(b => ` <small>[${b}]</small>`).join("")}
                    </span>
                </label>
            </div>
        `;
    });
    html += "</div>";
    container.innerHTML = html;
}

function renderExternalSubs(container, subs) {
    if (subs.length === 0) {
        container.innerHTML = "<p>No external subtitle files found in folder. Try uploading instead.</p>";
        return;
    }

    let html = '<div class="track-list">';
    subs.forEach((s, i) => {
        html += `
            <div class="track-item">
                <label>
                    <input type="radio" name="ext-sub" value="${escapeHtml(s.path)}">
                    <span class="track-info">
                        ${escapeHtml(s.filename)}
                        ${s.language ? ` <small>[${escapeHtml(s.language)}]</small>` : ""}
                    </span>
                </label>
            </div>
        `;
    });
    html += "</div>";
    container.innerHTML = html;
}
