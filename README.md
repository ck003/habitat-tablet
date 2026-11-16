# Habitat Tablet

![Habitat Tablet](custom_components/habitat_tablet/brand/icon.png)

把 Habitat 安卓平板接入 Home Assistant，**每台平板只创建一个屏幕开关**，用于自动化中的真实亮屏、熄屏。第一版没有摄像头、麦克风、人体检测或其他传感器实体。

适用于 Home Assistant **2026.11.0 及以上**的内置 Marketplace。集成和安卓 App 分别发布、分别更新。

## 安装

1. HA **设置 → Marketplace → 从链接添加（Add from link）**。
2. 填入仓库地址：**https://github.com/ck003/habitat-tablet**。
3. 安装 **Habitat Tablet**。从链接安装需要在 Marketplace 连接 GitHub。
4. 在 **设置 → 设备与服务 → 添加集成** 搜索 **Habitat Tablet**。

首次安装配置流可直接加载；HA 如提示重启则按提示操作。集成更新后按 Marketplace 提示重启。

## 平板设置

安装包含「HA 屏幕控制」的 Habitat App 更新。在 App 设置中：

1. 开启 **允许 HA 控制亮灭屏**。
2. 点 **授权熄屏**，在安卓系统界面授权设备管理员。该管理员仅声明 `force-lock`，不申请擦除数据、密码策略等权限。
3. 点 **复制地址**、**复制配对密钥**，填入 HA 集成的两个输入框。

平板与 HA 必须能通过局域网互相访问，端口为 TCP **8765**。推荐给平板设置 DHCP 地址保留。地址变化后，在 HA 集成菜单选择 **重新配置**；覆盖更新 APK 保留设备身份和密钥，卸载/清数据后需要重新配对。

配对密钥随机生成并在平板用 Android Keystore 加密保存，只放在鉴权请求头中，不放进 URL。接口为本地 HTTP，请只在可信家庭网络中使用，不做端口转发到公网。关闭平板上的开关即停止服务和远程访问。

## 使用

设备页面里会出现一个 **屏幕** 开关。实体 ID 由 HA 命名，可自行改为 `switch.living_tablet_screen`，然后在自动化中使用：

```yaml
action: switch.turn_on
target:
  entity_id: switch.living_tablet_screen
```

熄屏使用 `switch.turn_off`。命令等待平板实际切换后才更新状态；缺少熄屏授权、无法连接或操作失败会报告错误，离线显示不可用。每 30 秒读取一次当前屏幕状态，命令执行后立即更新。

## 锁屏与后台

- 针对目标平板 Lenovo TB-J606F / Android 12 实现；亮屏不会解除系统 PIN、图案或密码。设备有安全锁时，可能需要手动解锁才能操作中控。
- 设备管理员的 `lockNow()` 会真正熄屏并锁定设备，有安全凭据时可能要求强认证。这是安卓系统行为。
- 后台使用带通知的前台服务，不持续使用摄像头、录音或永久 CPU 唤醒锁。亮屏命令只短暂持有有超时的唤醒锁。
- 服务开启后会尝试在重启后恢复。系统强制停止 App、Wi-Fi 断开、拔电后的深度休眠或厂商后台限制可能影响可达性，需要重新打开 App 或调整该 App 的后台电池设置。
- 此开关控制的是屏幕电源状态；不自动改动系统安全锁、亮度、自然休眠时间或充电常亮设置。
- 在没有安装更新 APK、开启服务和授权前，HA 集成无法凭空控制系统屏幕。

## 后续更新

正式版本通过 GitHub Release 发布，版本号与 `manifest.json` 一致，附带 `habitat_tablet.zip`。**设置 → 更新**中即可升级集成，无需重复复制文件或重新添加仓库，设备与实体 ID 保留。自定义仓库的更新发现由 Marketplace 定期检查 GitHub，可能不会立即出现；需要保留 GitHub 连接。

这只更新 HA 集成，**不负责静默更新安卓 APK**。安卓 App 仍由原项目的 GitHub Actions 构建签名 APK，再覆盖安装。

## 开发与验证

- `.github/workflows/validate.yml`：HA 2026.11.1 下验证配置流、单个实体、权限错误、掉线、状态确认与 API 鉴权，另运行 hassfest 和 Marketplace/HACS 校验。
- `.github/workflows/release.yml`：校验版本并生成只含集成文件的 ZIP，发布正式 Release。`workflow_dispatch` 输入版本号即可发布，`manifest.json` 须先更新到同一版本。
- 安卓源码在独立的私有 App 仓库中维护；安卓单元测试和 APK 构建只运行于 GitHub Actions。

参考：[Marketplace 安装与格式](https://contributors.home-assistant.io/marketplace/guides/integrations/)、[发布与更新](https://contributors.home-assistant.io/marketplace/guides/releases/)。
