param(
    [string]$Tag = "v3.0.0",
    [string]$Repository = "Artelnics/neuraldesigner-models"
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot ".."))
$apiUrl = "https://api.github.com/repos/$Repository/releases/tags/$Tag"
$release = Invoke-RestMethod -Uri $apiUrl
$assets = @($release.assets | Where-Object { $_.name -like "*.zip" })

if ($assets.Count -eq 0) {
    throw "Release $Tag has no ZIP assets."
}

$taskTemp = Join-Path ([System.IO.Path]::GetTempPath()) (
    "neuraldesigner-models-sync-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $taskTemp | Out-Null

try {
    $index = 0
    foreach ($asset in ($assets | Sort-Object name)) {
        $index++
        $id = [System.IO.Path]::GetFileNameWithoutExtension($asset.name)
        $targetDirectory = Join-Path $repoRoot $id
        $archivePath = Join-Path $taskTemp $asset.name
        $extractDirectory = Join-Path $taskTemp $id

        Write-Host "[$index/$($assets.Count)] $($asset.name)"
        Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url `
            -OutFile $archivePath
        New-Item -ItemType Directory -Path $extractDirectory | Out-Null
        Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDirectory

        $modelFiles = @(Get-ChildItem -Recurse -File -LiteralPath $extractDirectory `
            -Filter "*.nd")
        if ($modelFiles.Count -ne 1) {
            throw "$($asset.name) contains $($modelFiles.Count) .nd files; expected one."
        }

        $expectedName = "$id.nd"
        if ($modelFiles[0].Name -ne $expectedName) {
            throw "$($asset.name) contains '$($modelFiles[0].Name)'; expected '$expectedName'."
        }

        New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null

        # Preserve every release resource (datasets, images, labels, and the
        # model), rather than copying only the .nd file.  Use LiteralPath for
        # each top-level item so asset names are never interpreted as globs.
        foreach ($item in Get-ChildItem -Force -LiteralPath $extractDirectory) {
            Copy-Item -LiteralPath $item.FullName -Destination $targetDirectory `
                -Recurse -Force
        }

        Remove-Item -LiteralPath $archivePath -Force
        Remove-Item -LiteralPath $extractDirectory -Recurse -Force
    }
}
finally {
    $resolvedTemp = [System.IO.Path]::GetFullPath($taskTemp)
    $systemTemp = [System.IO.Path]::GetFullPath(
        [System.IO.Path]::GetTempPath())

    if ($resolvedTemp.StartsWith($systemTemp, [System.StringComparison]::OrdinalIgnoreCase) `
        -and (Test-Path -LiteralPath $resolvedTemp)) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}

Write-Host "Synchronized $($assets.Count) model files from $Tag."
