$file = "F:\muni48\frontend\src\pages\Dashboard.jsx"
Copy-Item $file "F:\muni48\backup_Dashboard_before_emoji.jsx" -Force

$utf8   = New-Object System.Text.UTF8Encoding($false)
$strict = New-Object System.Text.UTF8Encoding($false, $true)
$cp     = [System.Text.Encoding]::GetEncoding(1252)
$marker = [regex]'[\u00C3\u00C2\u00E2\u00F0\u00E0]'
$undef  = @(0x81,0x8D,0x8F,0x90,0x9D)

function Repair-Line([string]$s) {
    $bytes = New-Object System.Collections.Generic.List[byte]
    foreach ($ch in $s.ToCharArray()) {
        $code = [int]$ch
        if ($code -lt 128 -or $undef -contains $code) { $bytes.Add([byte]$code); continue }
        $b = $cp.GetBytes([string]$ch)
        if ($b.Length -ne 1 -or ($b[0] -eq 63 -and $ch -ne '?')) { return $null }
        $bytes.Add($b[0])
    }
    try { return $strict.GetString($bytes.ToArray()) } catch { return $null }
}

$lines = [System.IO.File]::ReadAllLines($file, $utf8)
$fixed = 0
for ($i = 0; $i -lt $lines.Length; $i++) {
    $line = $lines[$i]
    for ($pass = 0; $pass -lt 2 -and $marker.IsMatch($line); $pass++) {
        $r = Repair-Line $line
        if ($null -eq $r -or $r.Contains([string][char]0xFFFD)) { break }
        $line = $r
    }
    if ($line -ne $lines[$i]) { $lines[$i] = $line; $fixed++ }
}
[System.IO.File]::WriteAllLines($file, $lines, $utf8)
Write-Host "Fixed lines: $fixed"