// API client — fetch() wrapper for all backend calls
const API = {
    async get(path) {
        const resp = await fetch(`/api${path}`);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || resp.statusText);
        }
        return resp.json();
    },

    async put(path, body) {
        const resp = await fetch(`/api${path}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || resp.statusText);
        }
        return resp.json();
    },

    async post(path, body) {
        const resp = await fetch(`/api${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || resp.statusText);
        }
        return resp.json();
    },

    async postForm(path, formData) {
        const resp = await fetch(`/api${path}`, {
            method: "POST",
            body: formData,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || resp.statusText);
        }
        return resp.json();
    },

    async postFormSSE(path, formData, onEvent) {
        const resp = await fetch(`/api${path}`, {
            method: "POST",
            body: formData,
        });
        if (!resp.ok) {
            const err = await resp.text();
            throw new Error(err || resp.statusText);
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop();
            for (const part of parts) {
                const line = part.trim();
                if (line.startsWith("data: ")) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        onEvent(data);
                    } catch (_) {}
                }
            }
        }
        if (buffer.trim().startsWith("data: ")) {
            try {
                const data = JSON.parse(buffer.trim().slice(6));
                onEvent(data);
            } catch (_) {}
        }
    },
};
