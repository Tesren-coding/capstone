// Shared HTTP handling; scenario rules remain authoritative on the server.
export async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The server did not return valid JSON.'); }
    if (!response.ok) {
        throw new Error(data.errors?.join('\n') || data.error || `Request failed (${response.status}).`);
    }
    return data;
}

export function postJson(url, data) {
    return requestJson(url, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    });
}
