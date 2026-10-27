# 纸间 · zhijian

把一本书，读成自己的理解。一份以 Markdown、图解和静态网站保存的个人读书档案。

书架包含《耶路撒冷三千年》和《明朝那些事儿》的阶段性笔记。实际已读范围以各书的 `book.json` 和笔记来源说明为准。

## 本地运行

安装 Node.js 22 或以上版本，以及 Python 3（用于下方预览命令），在项目根目录运行：

```sh
npm ci
npm run build
python3 -m http.server 4173 --bind 127.0.0.1 --directory website/dist
```

打开 [本地书架](http://127.0.0.1:4173/)。修改内容后重新运行 `npm run build`，再刷新浏览器。

默认使用系统中文衬线字体，保持暖纸色与墨蓝配色。如需使用自备字体，可在构建前通过 `KAMI_FONT_PATH` 指定字体文件的本地路径；请自行确认该字体允许的使用及发布范围。仓库没有打包第三方字体。

## 内容怎么维护

```text
books/<book-id>/book.json     书籍、笔记清单、阅读范围和进度
books/<book-id>/notes/*.md    原始笔记，按稳定 block ID 分块
books/<book-id>/assets/       SVG 图解源与 PNG 图片
books/<book-id>/exports/      可选的笔记导出文件
website/                     页面和构建脚本
website/dist/                自动生成，不直接修改、不提交
```

每本书独立保存；新增书籍不覆盖旧书。修改已有笔记时保留 book、note 和 block ID，以保持阅读链接稳定。

原书 PDF 保留在维护者自己的电脑上，不放进仓库。`source_pdf` 是本地阅读来源记录，不是网站下载地址；换电脑继续阅读时需要更新为自己的文件路径。网站构建不需要读取原书。

分段共读和追问在 AI 聊天工具中进行：提供 PDF，明确这次的页码或章节，整理文字与图解，再保存到 `books/`。网站仅展示已整理的内容，没有在线上传、生成或聊天后端。项目约定见 [AGENTS.md](AGENTS.md)；`distill-books` 共读技能当前由维护者另行安装，没有打包在此仓库中。

收藏、字号和阅读位置仅保存于各自浏览器，不进行跨设备同步。

## GitHub Pages

仓库提供 `.github/workflows/pages.yml`。在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。

每次向 `main` 推送后，工作流会安装依赖、构建并发布 `website/dist/`。也可以在 Actions 页面手动运行 **Publish reading archive**。此仓库对应的网站地址为 [在线书架](https://14126071.github.io/zhijian/)，首次部署成功后生效。

网页使用相对资源路径，支持 `/zhijian/` 这样的项目子目录；书籍与笔记的 hash 路由保持稳定。

日常更新：

```sh
npm run check
npm run build
git add books website
git commit -m "docs: update reading notes"
git push origin main
```

别人只想看最新笔记时，分享在线书架链接。希望维护独立档案时，可以复制本项目，使用自己的书籍、内容与发布设置；独立副本不会自动同步本仓库的新笔记。

## 许可与内容来源

网站代码采用 [MIT License](LICENSE)。读书笔记和自行制作的图解另行保留权利，不纳入代码的 MIT 授权；原书文字的引用及第三方素材依其各自权利和许可处理。`exports/` 中的 PDF 是读书笔记导出，不是原书。
