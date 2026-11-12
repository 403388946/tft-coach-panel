# scripts/

只读抓帧脚本目录。

## capture-lol.ps1

Windows PowerShell 只读抓帧脚本：找到 `League of Legends` 窗口，优先用 `PrintWindow` 取窗口自绘内容（不受上层窗口遮挡），抽样判为黑屏后回退 `CopyFromScreen`（屏幕合成画面），缩放后存 JPEG。

### 用法

```powershell
& .\capture-lol.ps1                 # 默认 1600 宽，输出 %TEMP%\lol_frame.jpg
& .\capture-lol.ps1 -Width 1920     # 提高分辨率
& .\capture-lol.ps1 -Out D:\frame.jpg
```

### 边界（保持不变）

- 仅按窗口标题 `League of Legends` 定位句柄，只读抓帧；
- `PrintWindow`（flag 2，`PW_RENDERFULLCONTENT`）优先，黑屏回退 `CopyFromScreen`；
- 输出 JPEG（默认 1600 宽，质量 80）；
- 参数：`-Width`（缩放宽度）、`-Out`（输出路径）；
- **不做**：键鼠动作、进程访问、内存读取、提权、客户端配置改写。

### 备注

- 对局内 DirectX 渲染下 `PrintWindow` 是否黑屏尚未进对局实测；黑屏时脚本自动回退 `CopyFromScreen`，需窗口并排、游戏区域可见。
- 脚本含中文注释；在 Windows PowerShell 5.1 下若注释显示乱码，将文件另存为 UTF-8（带 BOM）即可，不影响逻辑。
