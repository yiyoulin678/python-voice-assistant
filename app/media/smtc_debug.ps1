$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType=WindowsRuntime] | Out-Null
$manager = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$rows = @()
foreach ($session in $manager.GetSessions()) {
    try {
        [Windows.Media.MediaProperties.IMediaProperties, Windows.Media, ContentType=WindowsRuntime] | Out-Null
        $props = Await ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.MediaProperties.IMediaProperties])
        $status = $session.GetPlaybackInfo().PlaybackStatus.ToString()
        $rows += [ordered]@{
            app = $session.SourceAppUserModelId
            title = [string]$props.Title
            artist = [string]$props.Artist
            status = $status
        }
    } catch {
        $rows += [ordered]@{ app = $session.SourceAppUserModelId; error = $_.Exception.Message }
    }
}
$rows | ConvertTo-Json -Compress
