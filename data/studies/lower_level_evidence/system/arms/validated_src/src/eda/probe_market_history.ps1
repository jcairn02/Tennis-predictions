param(
    [string]$OutputDirectory = 'data/studies/tennis_data_audit/market_history',
    [switch]$IncludeJuly
)

# Read-only research probe. No account, trading, or production integration.
# Requests and untouched response bodies are preserved; existing files are not replaced.
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$cases = @(
    @{ name='early'; slug='wta-tauson-vs-joint-2025-09-18'; token='93069857165028755556289221755420823733341395565687770769704721178804097032290'; start='2025-09-16T00:00:00Z'; end='2025-09-22T00:00:00Z' },
    @{ name='recent'; slug='atp-medvede-rinderk-2026-09-04'; start='2026-09-01T00:00:00Z'; end='2026-09-07T00:00:00Z' }
)
if ($IncludeJuly) {
    $cases += @{ name='july-repeat'; slug='wta-parry-kalinsk-2026-07-01'; token='24413792233357357834959873724161319223652060414241534823171780600847907843427'; start='2026-06-29T00:00:00Z'; end='2026-07-03T00:00:00Z' }
}
foreach ($case in $cases) {
    $gammaUrl = 'https://gamma-api.polymarket.com/events?slug=' + $case.slug
    $gammaResponse = Invoke-WebRequest -Uri $gammaUrl -UseBasicParsing -TimeoutSec 30
    $gammaFile = Join-Path $OutputDirectory ($case.name + '-gamma.json')
    if (Test-Path -LiteralPath $gammaFile) { throw "Refusing to replace $gammaFile" }
    [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($gammaFile), $gammaResponse.Content)
    $events = @($gammaResponse.Content | ConvertFrom-Json)
    if (-not $case.token) {
        $market = @($events[0].markets | Where-Object { $_.question -eq $events[0].title })[0]
        if (-not $market) { throw "No unambiguous match-winner market: $($case.slug)" }
        $case.token = @($market.clobTokenIds | ConvertFrom-Json)[0]
    }
    $start = ([DateTimeOffset]$case.start).ToUnixTimeSeconds()
    $end = ([DateTimeOffset]$case.end).ToUnixTimeSeconds()
    $base = "https://data-api.polymarket.com/v2/prices-history?token_id=$($case.token)&start=$start&end=$end"
    $queries = @(
        @{ name='v2-auto'; url=$base },
        @{ name='v2-60'; url=($base + '&bucket_seconds=60') },
        @{ name='v2-10800'; url=($base + '&bucket_seconds=10800') },
        @{ name='clob-1'; url="https://clob.polymarket.com/prices-history?market=$($case.token)&startTs=$start&endTs=$end&fidelity=1" }
    )
    foreach ($query in $queries) {
        $name = $case.name + '-' + $query.name
        $path = Join-Path $OutputDirectory ($name + '.json')
        if (Test-Path -LiteralPath $path) { throw "Refusing to replace $path" }
        $retrieved = [DateTimeOffset]::UtcNow.ToString('o')
        try {
            $response = Invoke-WebRequest -Uri $query.url -UseBasicParsing -TimeoutSec 30
            [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($path), $response.Content)
            $payload = $response.Content | ConvertFrom-Json
            $rows = if ($query.name -like 'clob*') { @($payload.history) } else { @($payload.data) }
            $times = @($rows | ForEach-Object { if ($query.name -like 'clob*') { [long]$_.t } else { [long]$_.timestamp } })
            $deltas = @(for ($i=1; $i -lt $times.Count; $i++) { $times[$i]-$times[$i-1] })
            $meta = [ordered]@{ name=$name; slug=$case.slug; token=$case.token; url=$query.url; retrieved_at=$retrieved; status=$response.StatusCode; file=($name+'.json'); rows=$rows.Count; first=($times | Select-Object -First 1); last=($times | Select-Object -Last 1); delta_statistics=($deltas | Measure-Object -Minimum -Maximum -Average); returned_resolution_seconds=@($rows.resolution_seconds | Where-Object { $null -ne $_ } | Select-Object -Unique); sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
        } catch {
            $meta = [ordered]@{ name=$name; slug=$case.slug; token=$case.token; url=$query.url; retrieved_at=$retrieved; error=$_.Exception.Message }
        }
        $meta | ConvertTo-Json -Depth 6 -Compress | Add-Content -LiteralPath (Join-Path $OutputDirectory 'probes.jsonl')
        $meta | ConvertTo-Json -Depth 6 -Compress
    }
}
