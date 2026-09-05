$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

# Sprawdzenie, czy jesteśmy w repo Git
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Ten katalog nie jest repozytorium Git."
}

# Odczyt wersji integracji
$manifestPath = ".\custom_components\dsiw74\manifest.json"

if (-not (Test-Path $manifestPath)) {
    throw "Nie znaleziono $manifestPath"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$version = $manifest.version
$tag = "v$version"

Write-Host ""
Write-Host "=== Publikowanie DSIW74 $tag ==="
Write-Host ""

# Dodanie zmian
git add -A
if ($LASTEXITCODE -ne 0) {
    throw "git add nie powiodl sie."
}

# Commit tylko jeśli są zmiany
git diff --cached --quiet

if ($LASTEXITCODE -eq 1) {
    git commit -m "Release $tag"

    if ($LASTEXITCODE -ne 0) {
        throw "git commit nie powiodl sie."
    }
}
elseif ($LASTEXITCODE -eq 0) {
    Write-Host "Brak nowych zmian do commit."
}
else {
    throw "Blad podczas sprawdzania zmian Git."
}

# Push brancha main
Write-Host "Wysylanie main..."
git push origin main

if ($LASTEXITCODE -ne 0) {
    throw "git push main nie powiodl sie."
}

# Sprawdzenie, czy tag istnieje lokalnie
$existingTag = git tag --list $tag

if (-not $existingTag) {
    Write-Host "Tworzenie taga $tag..."

    git tag $tag

    if ($LASTEXITCODE -ne 0) {
        throw "Nie udalo sie utworzyc taga $tag."
    }
}
else {
    Write-Host "Tag $tag juz istnieje lokalnie."
}

# Push taga
Write-Host "Wysylanie taga $tag..."

git push origin $tag

if ($LASTEXITCODE -ne 0) {
    throw "Nie udalo sie wyslac taga $tag."
}

# Sprawdzenie, czy GitHub Release już istnieje
Write-Host "Sprawdzanie GitHub Release..."

$existingRelease = gh release list `
    --repo unky23/ha-dsiw74 `
    --json tagName `
    --jq ".[] | select(.tagName == `"$tag`") | .tagName"

if ($LASTEXITCODE -ne 0) {
    throw "Nie udalo sie pobrac listy GitHub Releases."
}

if (-not $existingRelease) {
    Write-Host "Tworzenie GitHub Release $tag..."

    gh release create $tag `
        --repo unky23/ha-dsiw74 `
        --title "DSIW74 $tag" `
        --generate-notes

    if ($LASTEXITCODE -ne 0) {
        throw "Nie udalo sie utworzyc GitHub Release."
    }
}
else {
    Write-Host "GitHub Release $tag juz istnieje."
}

Write-Host ""
Write-Host "=== GOTOWE: $tag ==="
Write-Host ""