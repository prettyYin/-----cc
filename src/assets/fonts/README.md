# 像素字体放这里

为了让 UI 的中文渲染成像素风（与桌宠图素材匹配），需要一份**中文像素字体 TTF**。

## 推荐字体（任选其一）

**缝合像素字体 Fusion Pixel Font 12px（首选）**
- 仓库：https://github.com/TakWolf/fusion-pixel-font
- Release：在 https://github.com/TakWolf/fusion-pixel-font/releases/latest 页面找 **`fusion-pixel-12px-monospaced-zh_hans.ttf`** 这类文件，下载即可
- 协议：SIL OFL，可随软件分发

**方舟像素字体 Ark Pixel 12px**
- 仓库：https://github.com/TakWolf/ark-pixel-font
- Release 找 `ark-pixel-12px-monospaced-zh_hans.ttf`
- 协议：SIL OFL

## 放置规则

下载好的 TTF **直接放在本目录**（`src/assets/fonts/`）。文件名保持原状，代码会自动按以下优先级查找并注册：

1. `fusion-pixel-12px-monospaced-zh_hans.ttf`
2. `fusion-pixel-12px-monospaced.ttf`
3. `fusion-pixel-12px-proportional-zh_hans.ttf`
4. `ark-pixel-12px-monospaced-zh_hans.ttf`
5. `pixel.ttf`（任意像素字体重命名成这个也行）

## 验证

放好后重启桌宠（双击 `启动小喜.bat`），打开聊天面板或设置，中文应该呈现明显的像素方块感。

如果都找不到，代码会回落到系统中文字体（微软雅黑）并关闭抗锯齿——还不是真正的像素风但能正常显示。
