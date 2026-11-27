# Seller Guide — build the native OneNote notebook and export the .onepkg

**This guide is for you (the seller), not for buyers.** You do this once. The result is the `.onepkg` file buyers download.

## What you need

- A Microsoft account with OneNote (personal or work)
- **OneNote for Windows** (the desktop app in Microsoft 365) to export the `.onepkg`
- Python 3.9 or newer, plus `pip install msal`

## No Microsoft account? Build it offline instead

If you have the OneNote desktop app on Windows (the one with **File › Export**), you can build the notebook on your computer with no account and no internet. Use the **OneNote_Local** folder:

1. Close OneNote. Open PowerShell in the OneNote_Local folder.
2. Test with 8 pages first: `powershell -ExecutionPolicy Bypass -File .\build_onenote_local.ps1 -Test`
3. Check the "Planner Test" notebook and its index links, then close it in OneNote.
4. Build the full planner: `powershell -ExecutionPolicy Bypass -File .\build_onenote_local.ps1`
5. Continue from step 3 below (export the .onepkg and test it).

The notebook is saved in `C:\Brass Ledger`, so the links inside it don't contain your Windows user name.

## 1. Build the notebook in your account

```bash
cd OneNote_Import
python3 onenote_import.py --dry-run     # optional: shows what will be created, no sign-in
python3 onenote_import.py               # signs you in and builds the notebook
```

1. The script prints a code and a web address. Open the address, enter the code and sign in to the Microsoft account where you want the notebook.
2. It creates **"Ultimate Planner 2027"**: 25 sections, 225 pages and about 700 links. It takes roughly 5–10 minutes, because Microsoft limits how fast pages can be created and the script waits whenever it's asked to.

> **Sign-in note.** By default the script signs in through Microsoft's own "Graph Command Line Tools" app. If your organisation blocks that app:
> 1. Register a free app at portal.azure.com › App registrations.
> 2. Turn on "Allow public client flows" and add the delegated permission **Notes.ReadWrite**.
> 3. Run `python3 onenote_import.py --client-id <your app id>`.

## 2. Check it

Open OneNote and find **Ultimate Planner 2027**, then check:

- [ ] The General Index is the first page in **Start**, and its links open the right pages.
- [ ] **⌂ Index** at the top of a weekly page jumps back to the index.
- [ ] Each template section starts with its contents page, and its links work.
- [ ] Checkboxes tick, and tables accept typing.

## 3. Export the file buyers download

In **OneNote for Windows**:
1. Open the notebook, then **File › Export**.
2. Choose **Notebook › OneNote Package (*.onepkg)** and save it as `Ultimate_Planner_2027.onepkg`.
3. Test it: double-click the `.onepkg` and save the copy under a different name. **Open the copy and click several index links.** This is the one thing I couldn't test from here, because links in an exported package must survive the round trip. If any don't, re-create them in the copy with Ctrl+K and export that copy.

## 4. Upload to Etsy

Put `Ultimate_Planner_2027.onepkg` in the listing's `etsy_upload/` folder next to the PDF planner and START_HERE.pdf, then upload all three files.

## Re-building for another year

1. Set `YEAR = 2028` in `build/planner_content.py`.
2. Run `python3 onenote_html.py`, then `python3 planner_pdf.py`.
3. Run the importer again.
