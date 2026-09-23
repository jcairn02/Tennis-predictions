param(
    [string]$OutputDirectory = 'data/studies/tennis_data_audit/commercial'
)

# Self-contained PowerShell research utility; no Python environment used.
$ErrorActionPreference = 'Stop'
$sourceUrl = 'https://www.goalserve.com/en/sport-data-feeds/tennis-api/sample/34'
$page = Invoke-WebRequest -Uri $sourceUrl -UseBasicParsing
$preBlocks = [regex]::Matches($page.Content, '(?is)<pre[^>]*>(.*?)</pre>')
if ($preBlocks.Count -ne 1) { throw 'Expected exactly one public sample block.' }
$sampleText = [System.Net.WebUtility]::HtmlDecode($preBlocks[0].Groups[1].Value)
$sampleText = [regex]::Replace($sampleText, '(?is)^\s*<code[^>]*>|</code>\s*$', '')
[xml]$sample = $sampleText
$matches = @($sample.scores.tournament.matches.match)
$players = @($matches.player)
$duplicates = @($matches | Group-Object id | Where-Object Count -gt 1 | ForEach-Object {
    [ordered]@{ id = $_.Name; count = $_.Count; rows = @($_.Group | ForEach-Object {
        [ordered]@{ date = $_.date; time = $_.time; status = $_.status; players = @($_.player.name) }
    }) }
})
$finishedWithoutWinner = @($matches | Where-Object {
    $_.status -eq 'Fin.' -and @($_.player | Where-Object winner -eq 'True').Count -ne 1
} | ForEach-Object {
    [ordered]@{ id = $_.id; date = $_.date; players = @($_.player.name); winners = @($_.player.winner) }
})
$missingSinglesIds = @($players | Where-Object { $_.HasAttribute('id') -and [string]::IsNullOrWhiteSpace($_.id) })
$missingDoublesIds = @($players | Where-Object {
    ($_.HasAttribute('id1') -and [string]::IsNullOrWhiteSpace($_.id1)) -or
    ($_.HasAttribute('id2') -and [string]::IsNullOrWhiteSpace($_.id2))
})
$findings = [ordered]@{
    retrieved_at_utc = [DateTime]::UtcNow.ToString('o')
    source_url = $sourceUrl
    evidence_type = 'downloaded_vendor_documentation_sample_not_live_or_authenticated_api'
    sample_dates = @($matches.date | Sort-Object -Unique)
    tournament_blocks = @($sample.scores.tournament).Count
    match_rows = $matches.Count
    unique_match_ids = @($matches.id | Sort-Object -Unique).Count
    player_or_team_rows = $players.Count
    singles_rows_missing_id = $missingSinglesIds.Count
    doubles_rows_missing_component_id = $missingDoublesIds.Count
    duplicate_match_ids = $duplicates
    finished_rows_without_exactly_one_winner = $finishedWithoutWinner
    limitations = @(
        'Public static 2019 example; findings cannot establish current production error rates.',
        'No point-by-point event tape is present in this scores example.',
        'Date/time attributes are present without timezone suffix; website FAQ separately says UTC.',
        'Counts refer to sample rows, not distinct matches in an actual historical archive.'
    )
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$xmlPath = Join-Path $OutputDirectory 'goalserve-public-sample-34.xml'
$sampleText | Set-Content -LiteralPath $xmlPath -Encoding utf8
$findings['sample_sha256'] = (Get-FileHash -LiteralPath $xmlPath -Algorithm SHA256).Hash.ToLowerInvariant()
$findings | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'goalserve-sample-audit.json') -Encoding utf8
$findings | ConvertTo-Json -Depth 10
