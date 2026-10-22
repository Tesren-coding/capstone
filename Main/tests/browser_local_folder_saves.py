"""Exercise the real Line Builder local-folder save workflow with a mock browser
File System Access API. No actual user files, server DB, or filesystem used.
Run: python tests/browser_local_folder_saves.py
"""
from playwright.sync_api import sync_playwright
from browser_builder_smoke import HTML, BUNDLE, FETCH_STUB

FAKE_FOLDER = r'''() => {
 const files = {};
 window.__deviceFiles = files;
 const dir = {
   kind:'directory',name:'Line Planning',
   queryPermission:async () => 'granted', requestPermission:async () => 'granted',
   getFileHandle:async (name,opt={}) => {
     if(!(name in files)) {
       if(!opt.create) throw new DOMException('Missing file','NotFoundError');
       files[name] = '';
     }
     return {
       getFile:async () => ({text:async () => files[name]}),
       createWritable:async () => {
         let pending = files[name];
         return {write:async text => {pending=text},close:async () => {files[name]=pending},abort:async()=>{}};
       }
     };
   },
   removeEntry:async name => {if(!(name in files)) throw new Error('Not found'); delete files[name];},
   async *entries() {for(const name of Object.keys(files)) yield [name,{kind:'file',name}];},
 };
 Object.defineProperty(window,'isSecureContext',{configurable:true,value:true});
 window.showDirectoryPicker = async () => dir;
 }'''

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1450,'height':1000}, accept_downloads=True)
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.set_content(HTML)
        page.evaluate(FETCH_STUB)
        page.evaluate(FAKE_FOLDER)
        page.evaluate('localStorage.setItem("capstone-builder-scenario-save-location","local")')
        page.add_script_tag(content=BUNDLE)
        page.wait_for_selector('body[data-builder-ready="true"]')
        assert page.locator('#save-location-mode').input_value() == 'local'
        assert page.locator('#scenario-storage-note').inner_text().startswith('Local device folder')
        page.locator('#choose-local-folder-btn').click()
        page.wait_for_function('() => document.querySelector("#local-folder-status").textContent.includes("Line Planning")')

        initial_dialog = lambda d: d.accept('Test Local')
        page.on('dialog', initial_dialog)
        page.locator('#save-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        assert page.locator('#scenario-select').input_value() == 'Test Local.json'
        snap = page.evaluate('window.__builderTest.serializeScenario()')
        assert page.evaluate('JSON.parse(window.__deviceFiles["Test Local.json"])') == snap
        assert page.evaluate('Object.keys(window.__savedByTest).length') == 0  # not stored on server

        # Unsaved change and explicit overwrite; JSON on disk should update.
        page.locator('.add-btn[data-type="station"]').click()
        canvas=page.locator('#builder-canvas')
        canvas.scroll_into_view_if_needed()
        bbox=canvas.bounding_box()
        page.mouse.click(bbox['x']+400*bbox['width']/2400,bbox['y']+320*bbox['height']/1042)
        assert page.evaluate('window.__builderTest.serializeScenario()') != snap
        page.locator('#save-scenario-btn').click()
        page.locator('#save-overwrite-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Saved")')
        updated = page.evaluate('window.__builderTest.serializeScenario()')
        assert page.evaluate('JSON.parse(window.__deviceFiles["Test Local.json"])') == updated

        # External edits are detected before overwriting the original local file.
        page.evaluate('window.__deviceFiles["Test Local.json"] += " "')
        page.locator('#save-scenario-btn').click()
        page.locator('#save-overwrite-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("changed since")')
        assert page.evaluate('window.__deviceFiles["Test Local.json"].endsWith(" ")')
        page.evaluate('window.__deviceFiles["Test Local.json"] = JSON.stringify(window.__builderTest.serializeScenario(), null, 2) + "\\n"')

        # Rename modifies the device folder entry, not the backend.
        page.remove_listener('dialog', initial_dialog)
        page.on('dialog',lambda d:d.accept('Renamed Device'))
        page.locator('#rename-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Renamed device file") && document.querySelector("#scenario-select").value === "Renamed Device.json"')
        assert page.evaluate('"Test Local.json" in window.__deviceFiles') is False

        # Switching to server never hides or deletes device files; returning to
        # the chosen local folder restores its list.
        page.locator('#save-location-mode').select_option('server')
        page.wait_for_function('() => document.querySelector("#scenario-storage-note").textContent.includes("storage")')
        assert page.locator('#scenario-select option').count() == 1
        page.locator('#save-location-mode').select_option('local')
        page.wait_for_function('() => document.querySelector("#scenario-select").value === "Renamed Device.json"')

        # New Line does not remove device files; Open retrieves saved changes.
        page.locator('#new-line-btn').click()
        page.locator('#scenario-select').select_option('Renamed Device.json')
        page.locator('#load-scenario-btn').click()
        page.wait_for_function('() => document.querySelector("#status-text").textContent.includes("Opened")')
        assert page.evaluate('window.__builderTest.serializeScenario()') == updated

        # Numbered versions keep the previous file, and never use the server.
        page.locator('#save-scenario-btn').click()
        page.locator('#save-duplicate-btn').click()
        page.wait_for_function('() => document.querySelector("#scenario-select").value === "Renamed Device_v2.json"')
        assert page.evaluate('"Renamed Device.json" in window.__deviceFiles')
        assert page.evaluate('"Renamed Device_v2.json" in window.__deviceFiles')

        # Browsers without folder permissions still have a client-only download.
        page.locator('#save-location-mode').select_option('download')
        with page.expect_download() as info:
            page.locator('#save-scenario-btn').click()
        assert info.value.suggested_filename == 'Renamed Device.json'
        assert page.evaluate('Object.keys(window.__savedByTest).length') == 0
        assert not errors, errors
        browser.close()
        print('Chromium: device folder, no server writes, overwrite protection, rename, switch backend, new line and reopen passed.')

if __name__ == '__main__': test()
