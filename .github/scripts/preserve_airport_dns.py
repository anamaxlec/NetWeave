"""Preserve opt-in airport/subscription node DNS compatibility across upstream syncs.

The provider-specific resolver is restricted to actual proxy node hostnames.
NetWeave's default DoH, domestic routing and FCM DNS behavior stay unchanged.
"""
from pathlib import Path


JS_FILES = (Path('Script/mihomoScript.js'), Path('Script/Script.js'))

HELPER = r"""/**
 * 机场 DNS 兼容：只为订阅节点的域名保留机场原始解析器。
 * proxy-server-nameserver-policy 允许按节点域名指定入口；不覆盖普通网站 DNS。
 * DNS 连接参数（#DIRECT / #RULES / #ecs 等）保留原样。
 */
function buildAirportNodeDnsPolicy(originalDnsConfig, proxyDomains, shouldRewriteByHosts) {
  const policy = {};
  const matchProxyDomain = createDomainMatcher(proxyDomains);
  const originalPolicy = {
    ...originalDnsConfig['nameserver-policy'],
    ...originalDnsConfig['proxy-server-nameserver-policy'],
  };

  for (const [pattern, source] of Object.entries(originalPolicy)) {
    if (!matchProxyDomain(pattern)) continue;
    if (typeof source === 'string' && source.trim()) {
      policy[pattern] = source;
    } else if (Array.isArray(source)) {
      const entries = source.filter((dns) => typeof dns === 'string' && dns.trim());
      if (entries.length) policy[pattern] = entries;
    }
  }

  const dnsList = (source) => {
    const values = Array.isArray(source) ? source : typeof source === 'string' ? [source] : [];
    return values.filter((dns) => typeof dns === 'string' && dns.trim());
  };

  // 如果机场使用指向本地 DNS listen 的占位解析器并已映射 hosts，
  // 不要再次把该占位地址当成实际的节点 DNS。
  const proxyDNS = shouldRewriteByHosts ? [] : dnsList(originalDnsConfig['proxy-server-nameserver']);
  const fallback = proxyDNS.length ? proxyDNS : dnsList(originalDnsConfig.nameserver);
  const patterns = Object.keys(policy);
  if (fallback.length) {
    for (const domain of proxyDomains) {
      const matchesDomain = createDomainMatcher(new Set([domain]));
      if (patterns.some((pattern) => matchesDomain(pattern))) continue;
      policy[domain] = [...fallback];
    }
  }
  return policy;
}

"""

TOGGLE = '  优先机场DNS: false, // 优先使用订阅原始 DNS 解析代理节点\n'
HOSTS_BEFORE = '  const mappedProxies = shouldRewriteByHosts ? applyHostsToProxies(filteredProxies, config.hosts) : filteredProxies;'
HOSTS_AFTER = (
    '  const mappedProxies =\n'
    '    shouldRewriteByHosts || ruleOptionsEnable.优先机场DNS\n'
    '      ? applyHostsToProxies(filteredProxies, config.hosts)\n'
    '      : filteredProxies;'
)
POLICY_BEFORE = """    ...(Object.keys(proxyServerPolicy).length > 0 && {
      'proxy-server-nameserver-policy': proxyServerPolicy,
    }),"""
POLICY_AFTER = """    ...(Object.keys(effectiveProxyServerPolicy).length > 0 && {
      'proxy-server-nameserver-policy': effectiveProxyServerPolicy,
    }),"""
EFFECTIVE = """  const effectiveProxyServerPolicy = ruleOptionsEnable.优先机场DNS
    ? buildAirportNodeDnsPolicy(originalDnsConfig, proxyDomains, shouldRewriteByHosts)
    : proxyServerPolicy;

"""


def once(text, before, after, path):
    if text.count(before) != 1:
        raise RuntimeError(f'{path}: expected one anchor for airport DNS patch: {before[:80]!r}')
    return text.replace(before, after, 1)


def patch_js(text, path):
    if TOGGLE not in text:
        anchor = '  // 以下为非分流策略配置\n'
        text = once(text, anchor, anchor + TOGGLE, path)

    helper_name = 'function buildAirportNodeDnsPolicy('
    if helper_name not in text:
        anchor = '/**\n * 构建 DNS 与 hosts：'
        text = once(text, anchor, HELPER + anchor, path)

    if 'shouldRewriteByHosts || ruleOptionsEnable.优先机场DNS' not in text:
        text = once(text, HOSTS_BEFORE, HOSTS_AFTER, path)

    if 'const effectiveProxyServerPolicy = ruleOptionsEnable.优先机场DNS' not in text:
        anchor = "  const originalFakeIpFilter = originalDnsConfig['fake-ip-filter'] || [];"
        text = once(text, anchor, EFFECTIVE + anchor, path)

    if "'proxy-server-nameserver-policy': effectiveProxyServerPolicy" not in text:
        text = once(text, POLICY_BEFORE, POLICY_AFTER, path)

    for part in (TOGGLE, helper_name, 'shouldRewriteByHosts || ruleOptionsEnable.优先机场DNS', 'const effectiveProxyServerPolicy = ruleOptionsEnable.优先机场DNS', "'proxy-server-nameserver-policy': effectiveProxyServerPolicy"):
        if part not in text:
            raise RuntimeError(f'{path}: airport DNS patch incomplete')
    if text.count('  优先机场DNS: false,') != 1:
        raise RuntimeError(f'{path}: duplicate airport DNS toggle')
    if text.count(helper_name) != 1:
        raise RuntimeError(f'{path}: duplicate airport DNS helper')
    return text


def main():
    for path in JS_FILES:
        source = path.read_text(encoding='utf-8')
        result = patch_js(source, path)
        path.write_text(result, encoding='utf-8')
    print('Optional airport DNS node resolver protection applied to both scripts')


if __name__ == '__main__':
    main()
