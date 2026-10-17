# G-V1 完整 STEP 私有下载与 FreeCAD 查看

本说明对应任务26。**不再使用此前会404的 `/releases/tag/` 网页链接。** 已确认私有 release `t0-cad-review-20261016-9ec1022` 为 Draft，资产真实存在；保留 Draft，通过授权 GitHub CLI/API 下载，不发布、不公开 STEP、不合并 PR。

## 已有版本与新版本

| 文件 | 内容 | 是否轻量proxy |
|---|---|---|
| 原资产 `t0-g-v1-review-complete.zip` | **原 `e805d38` 完整装配** `assembly_complete_12_4mm.step`、原报告；两颗L形键 | 否，含723官方实体，装配739实体 |
| 新资产 `t0-g-v1-boot-rect-task26-viewer.zip` | BOOT圆角矩形新版完整装配；两版前壳；共用原板、后盖、螺丝、临时配件精确STEP；FreeCAD查看脚本 | 否，原板为全部723物理实体，无包络替换 |
| Git中的 `deliverables/t0-g-v1-boot-rect/assembly_light.step` / `.glb` | 新版轻量装配，适合先看外观 | **是**，部分元件为明确标记的proxy，不作净空证据 |

旧版资产不替换。新版包中的 `baseline_e805d38/FrontShell.step` 来自冻结的旧版交付；其他精确共用件保持同一坐标。旧版**原始完整装配文件**在旧资产中单独取得，不用重构模型冒充它。

完整装配中的原板为精确723物理实体；电池、扬声器、插头和线束仍是原先 `unverified` 的临时包络，不是配件实测模型。

完整装配用于查看，不是单件打印文件。本轮不批准打印/下单；未来审查中的制造件只有前壳和后盖，不是整板装配或临时配件。

## Mac直接下载（需要本仓库权限）

使用 GitHub CLI；未安装时可按 [GitHub CLI官方安装说明](https://github.com/cli/cli#installation) 安装。先在Mac终端登录有本私有仓库权限的账户：

```bash
gh auth login --hostname github.com
gh auth status --hostname github.com
gh repo view Gadil123/esp32-design
mkdir -p ~/Downloads/PocketPi-T26

gh release view t0-cad-review-20261016-9ec1022 -R Gadil123/esp32-design --json isDraft,assets

gh release download t0-cad-review-20261016-9ec1022 -R Gadil123/esp32-design --pattern t0-g-v1-review-complete.zip --dir ~/Downloads/PocketPi-T26

gh release download t0-cad-review-20261016-9ec1022 -R Gadil123/esp32-design --pattern t0-g-v1-boot-rect-task26-viewer.zip --dir ~/Downloads/PocketPi-T26

unzip ~/Downloads/PocketPi-T26/t0-g-v1-review-complete.zip -d ~/Downloads/PocketPi-T26/original_e805d38
unzip ~/Downloads/PocketPi-T26/t0-g-v1-boot-rect-task26-viewer.zip -d ~/Downloads/PocketPi-T26/viewer
```

命令通过授权 release API 找到 Draft 资产，不依赖草稿的标签网页地址。若 `gh repo view` 也404，是当前账户的私有仓库访问问题；先切换到有权限的账户。仓库可见但草稿不可见时需具有草稿访问权限的账户，或使用下方服务器转移方式；不为此公开文件或发布 release。已有同名下载可保留，改用新的本地目录。

[GitHub release资产API](https://docs.github.com/en/rest/releases/assets)支持授权获取附件；`gh release download`是本轮实际验证的下载路径。验证记录见交付目录的 `download_verification.json`，包含下载字节数、ZIP目录与STEP实体/坐标检查；**未做SHA校验**。

## 服务器取文件，再拷到Mac

服务器已经实际下载的文件位于：

```text
/home/gadil/esp32-project/esp32-design-t0/build/t26-download-verification/old/t0-g-v1-review-complete.zip
/home/gadil/esp32-project/esp32-design-t0/build/t26-download-verification/new/t0-g-v1-boot-rect-task26-viewer.zip
```

Mac终端使用你平时连接本服务器的SSH地址。例如服务器仍为 `192.168.50.250` 时：

```bash
mkdir -p ~/Downloads/PocketPi-T26
POCKET_PI_SSH=gadil@192.168.50.250
scp "$POCKET_PI_SSH:/home/gadil/esp32-project/esp32-design-t0/build/t26-download-verification/old/t0-g-v1-review-complete.zip" ~/Downloads/PocketPi-T26/
scp "$POCKET_PI_SSH:/home/gadil/esp32-project/esp32-design-t0/build/t26-download-verification/new/t0-g-v1-boot-rect-task26-viewer.zip" ~/Downloads/PocketPi-T26/
```

SSH地址/端口请沿用你的现有连接配置；上面的SCP网络连接没有在本轮代替Mac实测。无需改路由或代理。随后按上一节解压。

## FreeCAD完整装配与分解查看

最直接：打开 `original_e805d38/assembly_complete_12_4mm.step` 查看原版，或 `viewer/boot_rect_task26/assembly_complete_12_4mm.step` 查看新版。新版STEP具名顶层包括 `OfficialBoard_ALL_723_REAL_SOLIDS`、`FrontShell_BOOT_RECT_BAT_PWR_L`、`RearShell_UNCHANGED`、四螺丝、临时配件。具体导入树取决于FreeCAD STEP导入设置。

为避免导入时合并成难以操作的单一树节点，提供**五个同坐标精确STEP**和短查看脚本。它使用标准 `Part.read` / `Part::Feature`，无需Assembly插件、FreeCAD MCP或任何联网操作；每组只有一个树节点，原板屏总成（含屏幕和原装元件）仍保留723真实实体。

1. 打开FreeCAD，选择 **View → Panels → Python console**。
2. 在FreeCAD的Python控制台粘贴以下四行（如解压位置不同，修改 `p`）：

```python
from pathlib import Path
p=Path.home()/"Downloads/PocketPi-T26/viewer/view_g_v1_freecad.py"
ns={"__file__":str(p)}
exec(compile(p.read_text(),str(p),"exec"),ns)
```

3. 在同一控制台按需执行：

```python
ns["exploded"]()                  # 仅视觉分离，不是实际拆装路径证明
ns["assembled"]()                # 恢复各组原装配Placement，保留原有旋转
```

看旧版时先关闭当前文档，再加载旧版前壳，避免8GB Mac同时加载两套原板：

```python
import FreeCAD as App
App.closeDocument(App.ActiveDocument.Name)
ns["open_version"]("baseline_e805d38")
```

脚本默认打开新版，树中可单独选择 `FrontShell`、`RearShell`、`OfficialBoard_723`、`Hardware`、`Accessories_UNVERIFIED`，按空格显示/隐藏。物理拆装顺序仍为**软支承正面朝下 → 卸四螺丝 → 单片顺序释放后盖 → 原板直线取出**；视觉分解的位移不代表带线束或带玻璃模块可这样移动。

脚本保存每组导入时的Placement，复位不会假设原STEP没有位置/旋转。也可直接多次 File → Import 五个单体STEP到同一文档，保留其坐标，通过属性 Data → Placement 手工移动；记下原Placement再恢复。可保存为自己的 `.FCStd`。

8GB Mac建议先看轻量GLB，完整模型一次只打开一个版本；原板精确STEP较大。几何检查采用完整实体，轻量模型不用于判断碰撞。

本轮在Linux上验证STEP回读和脚本语法，**未安装/运行FreeCAD GUI，也未声称Mac显示、渲染速度或脚本GUI运行已经实测**。相关API依据 [FreeCAD官方Part.read使用示例](https://github.com/FreeCAD/FreeCAD-library/blob/master/PartsLibrary.FCMacro) 和 [Placement说明](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Placement.md)。
