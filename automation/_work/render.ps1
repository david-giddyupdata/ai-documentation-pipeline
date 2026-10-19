# Render the draft to _work/render.pdf. New-Object starts a separate Word process, so Quit() here
# never touches David's open documents (they live in his own Word process). Always Quit: a skipped
# Quit leaves a hidden WINWORD that locks the draft (happened 2026-10-03).
$here = Split-Path -Parent $PSScriptRoot
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open((Resolve-Path "$here\..\QuickSight Journey 1 - draft.docx").Path, $false, $true, $false)
    $doc.ExportAsFixedFormat("$here\_work\render.pdf", 17)
    try { $doc.Close($false) } catch {}
} finally {
    try { $word.Quit() } catch {}
}
