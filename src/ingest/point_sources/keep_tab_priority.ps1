# Keep the SofaScore collector's processes at AboveNormal CPU priority while a long browser-mode run goes on.
#
# Why (observed 13 Oct 2026, work package P7): Chrome runs every renderer of the scraping profile at Idle priority,
# the SofaScore tab's among them, despite the flags against backgrounding (--disable-renderer-backgrounding and the
# others in docs/studies/gap_downloads/README.md). When other work holds the CPU at 100%, an Idle renderer gets almost
# no time and the run stalls for minutes, with no error. Raising the priority restored the pace at once, but Chrome
# lowers its renderers again on its own, so this re-raises them every few seconds. It touches only the Chrome
# processes of the scraping profile (--user-data-dir ...sofascore-cdp) and the adapter's Python processes, and logs
# each change. The collector needs little CPU, so other work loses almost nothing.
#
# Run detached (it stops by itself after -Hours):
#   pwsh -NoProfile -File src/ingest/point_sources/keep_tab_priority.ps1
param(
    [int]$Seconds = 15,
    [int]$Hours = 168,
    [string]$Log = "data/raw/point_sources/sofascore_editions/_logs/keep_tab_priority.log"
)
$end = (Get-Date).AddHours($Hours)
Add-Content $Log "$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) started (pid $PID; every $Seconds s until $($end.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')))"
while ((Get-Date) -lt $end) {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match 'sofascore-cdp' })
    $procs += @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -match 'sofascore_editions' })
    foreach ($c in $procs) {
        $p = Get-Process -Id $c.ProcessId -ErrorAction SilentlyContinue
        if ($p -and $p.PriorityClass -in @('Idle', 'BelowNormal', 'Normal')) {
            $was = $p.PriorityClass
            $kind = if ($c.Name -like 'python*') { 'adapter' } elseif ($c.CommandLine -match '--type=(\S+)') { $Matches[1] } else { 'browser' }
            try {
                $p.PriorityClass = 'AboveNormal'
                Add-Content $Log "$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) raised $($c.ProcessId) ($kind) from $was"
            } catch {
                Add-Content $Log "$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) could not raise $($c.ProcessId) ($kind): $_"
            }
        }
    }
    Start-Sleep -Seconds $Seconds
}
Add-Content $Log "$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) stopped (time limit)"
