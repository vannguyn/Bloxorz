$ErrorActionPreference = 'Stop'

# Prefer a standalone compiler; otherwise reuse Tinymist installed by VS Code.
$typstCompiler = Get-Command typst -ErrorAction SilentlyContinue
if ($typstCompiler) {
    $compilerPath = $typstCompiler.Source
} else {
    $extensionRoot = Join-Path $env:USERPROFILE '.vscode\extensions'
    $tinymistExtension = Get-ChildItem -LiteralPath $extensionRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object Name -Like 'myriad-dreamin.tinymist-*-win32-x64' |
        Sort-Object LastWriteTime -Descending |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'out\tinymist.exe') } |
        Select-Object -First 1
    if (-not $tinymistExtension) {
        throw 'Install Tinymist Typst in VS Code, or install Typst CLI and add it to PATH.'
    }
    $compilerPath = Join-Path $tinymistExtension.FullName 'out\tinymist.exe'
}

& $compilerPath compile (Join-Path $PSScriptRoot 'main.typ') (Join-Path $PSScriptRoot 'main.pdf')
if ($LASTEXITCODE -ne 0) {
    throw "Typst compilation failed (exit $LASTEXITCODE)."
}
Write-Output (Join-Path $PSScriptRoot 'main.pdf')
