# NetWeave

这是基于 [AIsouler/MyClash](https://github.com/AIsouler/MyClash) 的个人优化 Fork，继续跟随上游更新，并针对我自己的 Android / Bettbox 使用场景做了一些网络稳定性调整。

上游原项目基于 [Mihomo](https://github.com/MetaCubeX/mihomo/tree/Alpha)，提供全量版和精简版配置文件与覆写脚本，支持 Bettbox 图形化配置管理、分流策略、地区策略、节点过滤、倍率识别、私有 DNS / hosts 兼容等功能。

## 本 Fork 的主要改动

### 1. FCM 推送稳定性优化

主要用于 Android 设备，尤其是依赖 Google FCM 的应用，例如 Google Play 版微信。

将 `googlefcm.mrs` 提升为始终可用的基础 Rule Provider，并在 `fake-ip-filter` 中加入：

```text
rule-set:googlefcm
```

这样规则集后续新增的 FCM 域名也会自动使用真实 DNS 结果，不需要手工追着补域名。即使关闭全量版里的 `FCM` 分流策略组，或者使用精简版，`googlefcm` provider 仍然存在，不会产生悬空的 rule-set 引用。

同时保留 Google 官方 FCM / Android 推送链路 hostname 作为显式兜底，形成“动态规则集 + 官方域名列表”的双保险，减少 fake-ip 对长连接、注册和重连流程的干扰。

脚本版按上游当前的声明式数组组合风格组织：显式 hostname 统一定义为 `fcmRealIpFallback`，再通过 spread 合并到 `fake-ip-filter`；静态 YAML 则保留等价的显式条目。

当前显式保护的域名包括：

```text
mtalk.google.com
mtalk4.google.com
mtalk-dev.google.com
mtalk-staging.google.com
alt1-mtalk.google.com ~ alt8-mtalk.google.com
android.apis.google.com
device-provisioning.googleapis.com
firebaseinstallations.googleapis.com
```

全量版仍保留上游的独立 `FCM` 策略组，可根据实际网络环境选择直连或固定代理出口。`fake-ip-filter` 只负责让这些域名返回 real IP，不会强制改变其最终的 DIRECT / Proxy 路由策略。

### 2. 国内 QUIC 放行判断优化

保留上游「屏蔽国外 QUIC」的设计，但扩大国内流量识别范围。

上游主要通过：

```text
cn_additional OR cn_ip
```

判断 UDP/443 是否属于国内流量。本 Fork 调整为：

```text
geolocation-cn OR cn_additional OR cn_ip
```

因此在开启 Bettbox 的「禁用 QUIC / 排除国内」后：

```text
国内 QUIC  → 放行
国外 QUIC  → REJECT，回退 TCP
```

这样可以降低 fake-ip 模式下部分国内 App / CDN 域名因为未被额外规则覆盖而误判为国外 QUIC 的概率，重点改善微信、微博以及其他国内应用的媒体资源加载兼容性。

### 3. 默认解析与国内域名使用国内 DoH

为了兼顾国内 CDN 调度与 DNS 隐私，本 Fork 采用以下组合：

```text
default-nameserver
        ↓
国内 DoH（DIRECT）

rule-set:cn
rule-set:geolocation-cn
        ↓
国内 DoH（DIRECT）
        ↓
223.5.5.5 / 1.12.12.12 的 DoH 服务
```

国外普通域名仍使用：

```text
Cloudflare DoH / Google DoH
        ↓
默认代理
```

也就是说，`default-nameserver` 的 bootstrap/default 解析和主要国内业务域名解析都使用国内 DoH；同时保留 `rule-set:geolocation-cn`，避免只靠 `rule-set:cn` 时部分国内 CDN 域名落回国外 DNS。

这样不需要单独维护微信、微博、抖音、小红书、淘宝等 App 的 CDN 域名列表；只要域名进入通用中国规则集，就会自动使用国内 DNS 出口获得更合适的 CDN 调度。

`direct-nameserver` 仍保留 `system` 与国内普通 DNS 作为 DIRECT 场景的兼容回退，因此这里描述的是主要解析路径，并不宣称所有可能的 DNS 查询都绝对不会使用明文解析器。

### 4. 具体服务优先于 geolocation-cn 兜底

全量版新增并独立维护以下策略组：

- `Gemini`
- `OpenAI`
- `Anthropic`
- `GitHub`

对应规则放在 `Google` / 通用 `AI` 等大类规则之前；`geolocation-cn → 直连` 则保留在业务分流之后作为兜底，而不是提前作为总入口。

这样即使某个全球服务域名未来被通用中国 geosite 规则误分类，Gemini / Google / OpenAI 等更具体的服务规则仍有机会先命中，降低类似 `gstatic.com` 被错误直连的风险。

`Crypto` / `cryptocurrency` 分流则从 NetWeave 全量版中移除。

### 5. 自动同步上游并保护本地优化

仓库包含 `Sync upstream` GitHub Action，每天自动拉取：

```text
AIsouler/MyClash main
```

同步流程为：

```text
拉取并 merge 上游
        ↓
无冲突 → 直接继续
有已知冲突：
  README → 保留 NetWeave
  Script / Config → 采用上游最新结构
        ↓
重放 NetWeave 最小语义 patch
        ↓
再次运行 patch，验证幂等性
        ↓
JS 语法 / whitespace 校验
        ↓
运行集成测试
        ↓
提交并 push
```

如果出现不在允许列表内的新冲突，Action 会主动失败，而不是猜测如何处理，避免自动同步误覆盖未知文件。

目前自动保护：

- `googlefcm` 基础 provider 与 `rule-set:googlefcm` real-IP 保护
- Google 官方 FCM hostname 显式兜底
- 国内 QUIC 的 `geolocation-cn` 放行
- `default-nameserver` 使用国内 DoH
- `rule-set:cn` / `rule-set:geolocation-cn` 使用国内 DoH
- `Gemini` / `OpenAI` / `Anthropic` / `GitHub` 独立分流组与规则顺序
- 具体服务规则优先于 `geolocation-cn` 兜底
- 移除上游 `Crypto` / `cryptocurrency` 分流组与规则集
- 四份核心配置 / 脚本的 NetWeave 项目头部与链接

保护逻辑按职责拆分到：

- `.github/scripts/preserve_downstream.py`：FCM、DNS、QUIC、规则顺序、Crypto 移除、头部等网络语义差异
- `.github/scripts/preserve_service_groups.py`：Gemini / OpenAI / Anthropic / GitHub 独立策略组

同步过程中会连续运行两次 patch 并比较 diff，确保这些脚本具备幂等性；脚本版还会经过 `node --check`，避免 downstream patch 生成无效 JavaScript。

格式化 workflow 只做检查，不再自动向 `main` push，避免与上游同步 workflow 同时写分支产生 ref 竞争。

因此上游后续对核心脚本和配置的功能、规则与结构调整仍可继续合入；当结构发生已知冲突时，会先采用上游版本，再重放本 Fork 的小范围语义差异，而不是长期锁死旧文件。

---

## 覆写脚本

### 注意事项

> [!IMPORTANT]
>
> 该脚本仅用于覆写机场提供的配置文件，不建议用于覆写自行编写的完整配置。
>
> 如果机场使用私有 DNS / hosts，请不要再叠加代理客户端自身的 DNS 覆写，以免与脚本生成的 DNS 配置冲突。

### 全量版

[mihomoScript.js](/Script/mihomoScript.js)

```text
https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Script/mihomoScript.js
```

### 精简版

[Script.js](/Script/Script.js)

```text
https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Script/Script.js
```

全量版包含更多独立分流策略组；精简版保留核心分流逻辑，适合不需要大量策略组的场景。

## 配置文件

### 全量版

[mihomoConfig.yaml](/Config/mihomoConfig.yaml)

```text
https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Config/mihomoConfig.yaml
```

### 精简版

[mihomoConfigLite.yaml](/Config/mihomoConfigLite.yaml)

```text
https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Config/mihomoConfigLite.yaml
```

静态配置与覆写脚本的主要网络策略保持一致，但不具备脚本的动态节点处理能力。

## Bettbox

本项目继续兼容 [Bettbox](https://github.com/appshubcc/Bettbox) 的图形化配置参数。

常用选项包括：

- 手动选择 / 自动选择 / 负载均衡
- 各类独立分流策略组
- 生成地区自动选择组
- 隐藏地区手动选择组
- 生成高 / 低倍率节点组
- 过滤高倍率或非地区节点
- 屏蔽国外 QUIC
- IPv4 / IPv6 优先
- 链式代理

针对本 Fork 的使用习惯，开启「屏蔽国外 QUIC」时建议同时保持 Bettbox 中的「排除国内」开启，以实现“国外 QUIC 禁用、国内 QUIC 放行”。

## DNS 结构

当前主要结构为：

```text
国内域名
  └─ rule-set:cn / geolocation-cn
       └─ 国内 DoH #DIRECT

国外域名
  └─ Cloudflare / Google DoH
       └─ 默认代理

FCM / Android 推送相关域名
  ├─ rule-set:googlefcm（动态覆盖）
  └─ Google 官方 hostname（显式兜底）
       └─ fake-ip-filter → 返回真实 IP
```

同时保留：

- `fake-ip` 模式
- ARC DNS cache
- `store-fake-ip`
- TUN DNS hijack
- strict-route
- `tcp-concurrent`

## 上游继承的主要功能

- 多种分流策略与地区策略
- 根据节点匹配动态生成地区组
- 自动排除无效 / 信息类节点
- 自动识别节点倍率
- 高倍率 / 低倍率节点组
- 自定义节点
- 链式代理
- 机场私有 DNS / hosts 节点解析兼容
- Bilibili PCDN 屏蔽规则
- Google Play 下载兼容处理
- `rule-set` / MRS 规则集
- Bettbox 图形化参数

## 内置策略组（全量版）

包括但不限于：

`默认代理`、`手动选择`、`自动选择`、`负载均衡`、`FCM`、`YouTube`、`Gemini`、`OpenAI`、`Anthropic`、`GitHub`、`Google`、`AI`、`Microsoft`、`Apple`、`Telegram`、`Steam`、`TikTok`、`Twitter`、`Instagram`、`Netflix`、`Emby`、`PikPak`、`Spotify`、`EHentai`、`AdBlock`、`直连`、`漏网之鱼`。

地区节点组包括：香港、日本、美国、新加坡、台湾省，以及低倍率、高倍率和其他节点组。

## 说明

本 Fork 的修改主要针对个人使用场景，并不意味着这些设置适合所有网络环境。

特别是 FCM 的出口策略：如果本地网络可以稳定直连 Google，可保持 `FCM → 直连`；如果无法稳定直连，应使用一个长期稳定的固定代理出口，而不是频繁切换节点。

国内 DoH 与国内 QUIC 放行则主要用于改善中国大陆服务的 CDN 调度和 HTTP/3 使用体验，同时尽量避免扩大明文 DNS 查询范围。

## 致谢

感谢 Mihomo、Bettbox、bett-rules、Qure、clash-rules、adblockfilters 等相关开源项目及维护者。

本仓库的绝大部分基础设计、脚本、规则组织方式与持续更新都来自原作者的项目。特别感谢原作者 AIsouler 的工作：

**[AIsouler/MyClash](https://github.com/AIsouler/MyClash)**
