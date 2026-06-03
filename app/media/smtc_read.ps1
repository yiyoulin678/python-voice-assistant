$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

Function Await-Operation($Operation) {
    $resultType = $Operation.GetType().GetGenericArguments()[0]
    if ($null -eq $resultType) { throw '无法解析异步操作结果类型。' }
    $asTask = $asTaskGeneric.MakeGenericMethod($resultType)
    $netTask = $asTask.Invoke($null, @($Operation))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType=WindowsRuntime] | Out-Null
$managerType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]
$manager = Await-Operation ($managerType::RequestAsync())
$sessions = $manager.GetSessions()
if ($null -eq $sessions -or $sessions.Count -eq 0) { exit 2 }

$best = $null
$bestScore = -1
foreach ($session in $sessions) {
    try {
        $props = Await-Operation ($session.TryGetMediaPropertiesAsync())
        $status = $session.GetPlaybackInfo().PlaybackStatus.ToString()
        $title = [string]$props.Title
        $artist = [string]$props.Artist
        if ([string]::IsNullOrWhiteSpace($title) -and [string]::IsNullOrWhiteSpace($artist)) { continue }
        $score = 0
        if ($status -eq 'Playing') { $score += 100 }
        if (-not [string]::IsNullOrWhiteSpace($title)) { $score += 10 }
        if ($score -gt $bestScore) {
            $bestScore = $score
            $best = [ordered]@{
                title = $title
                artist = $artist
                is_playing = ($status -eq 'Playing')
                app = $session.SourceAppUserModelId
            }
        }
    } catch {
        continue
    }
}
if ($null -eq $best) { exit 3 }
$best | ConvertTo-Json -Compress
