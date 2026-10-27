# 纸间 · 网站

静态页面提供书架、图文阅读、搜索、图解放大、收藏、字号与阅读位置。内容源在 `books/`，生成物在 `website/dist/`。

在项目根目录运行 `npm ci`、`npm run build`，再用本地 HTTP 服务预览。完整运行方式、内容约定及 GitHub Pages 配置见 [项目说明](../README.md)。

不要直接修改 `website/dist/`。资源使用相对路径，以兼容本地根目录和 GitHub Pages 项目子目录。默认使用系统字体；可通过构建环境变量 `KAMI_FONT_PATH` 使用自备字体。
