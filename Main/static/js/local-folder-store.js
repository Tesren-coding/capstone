// Browser-side file persistence. These handles always refer to folders selected
// by the CURRENT browser user, never the Flask server's file system.
const DATABASE = 'capstone-local-folder-handles';
const STORE = 'directories';
const KEY = 'line-builder-scenarios';
let directory = null;

export function folderSupported() {
    return typeof window !== 'undefined' && window.isSecureContext &&
        typeof window.showDirectoryPicker === 'function' && typeof indexedDB !== 'undefined';
}

function openDb() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DATABASE, 1);
        req.onupgradeneeded = () => {
            if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE);
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error || new Error('Folder preference database could not open.'));
    });
}
async function rememberedHandle(action, value) {
    const db = await openDb();
    try {
        return await new Promise((resolve, reject) => {
            const tx = db.transaction(STORE, action === 'read' ? 'readonly' : 'readwrite');
            const request = action === 'read' ? tx.objectStore(STORE).get(KEY)
                : action === 'delete' ? tx.objectStore(STORE).delete(KEY)
                : tx.objectStore(STORE).put(value, KEY);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error || new Error('Could not remember folder.'));
        });
    } finally { db.close(); }
}
export async function restoreFolder() {
    if (!folderSupported()) return null;
    try {
        directory = await rememberedHandle('read') || null;
    } catch (error) {
        console.warn('Could not restore previous folder selection:', error);
        directory = null;
    }
    return directory;
}
export async function chooseFolder() {
    if (!folderSupported()) throw new Error('Folder access requires Chrome/Edge on HTTPS or localhost.');
    // Picker MUST be called from a direct click handler, not after fetching data.
    const picked = await window.showDirectoryPicker({id: 'capstone-line-builder', mode: 'readwrite'});
    const granted = await picked.queryPermission({mode: 'readwrite'});
    if (granted !== 'granted' && await picked.requestPermission({mode: 'readwrite'}) !== 'granted')
        throw new Error('Write permission was not granted for the selected folder.');
    directory = picked;
    try { await rememberedHandle('write', picked); }
    catch (error) { console.warn('Folder selected but could not remember it between sessions:', error); }
    return directory;
}
export function currentFolder() { return directory; }
export function folderLabel() { return directory?.name || null; }
export async function permission(mode = 'read') {
    if (!directory) return 'missing';
    try { return await directory.queryPermission({mode}); }
    catch { return 'prompt'; }
}
function requireDirectory() {
    if (!directory) throw new Error('Choose a local folder first.');
    return directory;
}
export async function listFiles() {
    const dir = requireDirectory();
    if (await permission('read') !== 'granted') throw new Error('Reconnect your folder to allow reading local files.');
    const files=[];
    for await (const [name, item] of dir.entries()) {
        if (item.kind === 'file' && /\.json$/i.test(name)) files.push(name);
    }
    return files.sort((a,b) => a.localeCompare(b, undefined, {numeric:true}));
}
export async function readFile(filename) {
    const dir = requireDirectory();
    const fh = await dir.getFileHandle(filename);
    const file = await fh.getFile();
    const text = await file.text();
    let scenario;
    try {scenario = JSON.parse(text);} catch {throw new Error(`"${filename}" does not contain valid JSON.`);}
    return {scenario, text};
}
export async function exists(filename) {
    return (await listFiles()).some(name => name.toLowerCase() === filename.toLowerCase());
}
export function jsonFilename(name) {
    const base = String(name || '').replace(/\.json$/i, '').trim()
        .replace(/[\\/:*?"<>|\x00-\x1f]/g, '_').replace(/[. ]+$/g, '').slice(0, 120);
    if (!base || base === '.' || base === '..') throw new Error('Enter a valid file name.');
    return base + '.json';
}
export async function numberedName(filename) {
    const names = new Set((await listFiles()).map(x => x.toLowerCase()));
    if (!names.has(filename.toLowerCase())) return filename;
    const stem = filename.replace(/\.json$/i, '').replace(/_v\d+$/i,'');
    for (let n=2; n<10000; n++) {
        const candidate = `${stem}_v${n}.json`;
        if (!names.has(candidate.toLowerCase())) return candidate;
    }
    throw new Error('Too many versions of this file.');
}
export async function writeFile(filename, text, {overwrite = false, expectedText = null} = {}) {
    if (await permission('readwrite') !== 'granted') throw new Error('Reconnect the folder and allow editing files.');
    const dir = requireDirectory();
    const names = await listFiles();
    const existing = names.find(name => name.toLowerCase() === filename.toLowerCase());
    if (existing && !overwrite) throw new Error(`"${filename}" already exists. Choose overwrite or a new version.`);
    if (existing && expectedText !== null) {
        const latest = await readFile(existing);
        if (latest.text !== expectedText) throw new Error('This file changed since you opened it. Reload it or save a new version.');
    }
    const fh = await dir.getFileHandle(existing || filename, {create:true});
    const writable = await fh.createWritable();
    try { await writable.write(text); await writable.close(); }
    catch (error) {try{await writable.abort();}catch{} throw error;}
    return existing || filename;
}
export async function renameFile(oldName, requestedName, {expectedText = null} = {}) {
    if (await permission('readwrite') !== 'granted') throw new Error('Reconnect your folder and allow editing files.');
    const newName=jsonFilename(requestedName);
    if (oldName.toLowerCase() === newName.toLowerCase()) return oldName;
    if (await exists(newName)) throw new Error(`"${newName}" already exists.`);
    const original = await readFile(oldName);
    if (expectedText !== null && original.text !== expectedText)
        throw new Error('The file changed since it was loaded. Reload before renaming.');
    // Copy, verify, THEN delete the original. On failure the old save remains.
    await writeFile(newName, original.text);
    const duplicate = await readFile(newName);
    if (duplicate.text !== original.text) throw new Error('The renamed copy could not be verified. Original file was kept.');
    await requireDirectory().removeEntry(oldName);
    return newName;
}
