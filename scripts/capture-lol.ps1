# 云顶参谋只读抓帧脚本
# 作用：找到 League of Legends 窗口，优先用 PrintWindow 取窗口原始画面（不受遮挡），
#       若返回黑屏则回退 CopyFromScreen 抓屏幕合成画面；缩放后存 JPEG。
# 边界：只读屏幕/窗口画面，不点击、不注入、不读游戏进程内存。
# 用法：& capture-lol.ps1 [-Width 1600] [-Out <path>]

param(
    [int]$Width = 1600,
    [string]$Out = ""
)

Add-Type -AssemblyName System.Drawing

$sig = @"
using System;
using System.Runtime.InteropServices;
public class CaptWin2 {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
Add-Type $sig

$list = New-Object System.Collections.ArrayList
$cb = [CaptWin2+EnumWindowsProc]{ param($h,$l)
  if ([CaptWin2]::IsWindowVisible($h)) {
    $sb = New-Object System.Text.StringBuilder 256
    [CaptWin2]::GetWindowText($h,$sb,256) | Out-Null
    $r = New-Object CaptWin2+RECT
    [CaptWin2]::GetWindowRect($h,[ref]$r) | Out-Null
    [void]$list.Add([PSCustomObject]@{ H=$h; Title=$sb.ToString(); L=$r.Left; T=$r.Top; R=$r.Right; B=$r.Bottom })
  }
  return $true
}
[CaptWin2]::EnumWindows($cb,[IntPtr]::Zero) | Out-Null

$win = $list | Where-Object { $_.Title -eq 'League of Legends' } | Select-Object -First 1
if (-not $win) {
    Write-Error "未找到 League of Legends 窗口，请确认游戏已启动并在窗口模式。"
    exit 1
}

if ([string]::IsNullOrEmpty($Out)) {
    $Out = Join-Path $env:TEMP "lol_frame.jpg"
}

$w = $win.R - $win.L
$h = $win.B - $win.T
$tw = $Width
$th = [int]($h * ($tw / $w))

function Test-BlackBitmap($bmp) {
    # 抽样网格判断是否接近全黑（PrintWindow 对部分 DX 窗口会返回黑屏）
    $stepX = [Math]::Max(1, [int]($bmp.Width / 16))
    $stepY = [Math]::Max(1, [int]($bmp.Height / 16))
    $sum = 0; $n = 0
    for ($x = 0; $x -lt $bmp.Width; $x += $stepX) {
        for ($y = 0; $y -lt $bmp.Height; $y += $stepY) {
            $p = $bmp.GetPixel($x, $y)
            $sum += ($p.R + $p.G + $p.B) / 3
            $n++
        }
    }
    $avg = $sum / $n
    return ($avg -lt 12)
}

$sw = [Diagnostics.Stopwatch]::StartNew()
$src = New-Object Drawing.Bitmap $w, $h
$g = [Drawing.Graphics]::FromImage($src)

# 路线 1：PrintWindow（不受遮挡）
$hdc = $g.GetHdc()
$pwOk = [CaptWin2]::PrintWindow($win.H, $hdc, 2)  # PW_RENDERFULLCONTENT
$g.ReleaseHdc($hdc)
$mode = "printwindow"
if (-not $pwOk -or (Test-BlackBitmap $src)) {
    # 路线 2：回退屏幕合成画面
    $g.Clear([Drawing.Color]::Black)
    $g.CopyFromScreen($win.L, $win.T, 0, 0, $src.Size)
    $mode = "copyfromscreen"
}

$dst = New-Object Drawing.Bitmap $tw, $th
$g2 = [Drawing.Graphics]::FromImage($dst)
$g2.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g2.DrawImage($src, 0, 0, $tw, $th)

$enc = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object Drawing.Imaging.EncoderParameters 1
$ep.Param[0] = New-Object Drawing.Imaging.EncoderParameter([Drawing.Imaging.Encoder]::Quality, [long]80)
$dst.Save($Out, $enc, $ep)

$sw.Stop()
$g.Dispose(); $g2.Dispose(); $src.Dispose(); $dst.Dispose()

$f = Get-Item $Out
Write-Host ("mode={0} | {1}x{2} -> jpg {3}x{4} | {5} ms | {6} KB" -f `
    $mode, $w, $h, $tw, $th, $sw.ElapsedMilliseconds, [int]($f.Length/1KB))
Write-Host $Out
