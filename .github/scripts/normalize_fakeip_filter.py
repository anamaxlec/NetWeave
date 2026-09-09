from pathlib import Path
import re

JS_FILES = [
    Path('Script/Script.js'),
    Path('Script/mihomoScript.js'),
]

# 上游全量脚本会根据 FCM 开关动态展开 googlefcm：
#   ...(ruleOptionsEnable['FCM'] ? ['rule-set:googlefcm'] : []),
# NetWeave 需要 googlefcm 始终存在于 fake-ip-filter，因此在 downstream patch
# 处理前先把这条条件 spread 规范化成普通数组项。这样也避免旧 patch 的
# 非嵌套数组正则在遇到条件表达式内部的 [] 时提前截断。
CONDITIONAL_GOOGLEFCM = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\.\.\.\(\s*ruleOptionsEnable\[['\"]FCM['\"]\]\s*"
    r"\?\s*\[\s*['\"]rule-set:googlefcm['\"]\s*\]\s*:\s*\[\s*\]\s*\),\s*$"
)

for path in JS_FILES:
    text = path.read_text(encoding='utf-8')

    def replace(match):
        return f"{match.group('indent')}'rule-set:googlefcm',"

    text, count = CONDITIONAL_GOOGLEFCM.subn(replace, text)

    # 只要上游仍使用当前已知的条件 spread，就必须已经被规范化。
    if re.search(
        r"\.\.\.\(\s*ruleOptionsEnable\[['\"]FCM['\"]\]\s*\?\s*\[\s*['\"]rule-set:googlefcm['\"]",
        text,
    ):
        raise RuntimeError(f'{path}: conditional googlefcm spread was not normalized')

    path.write_text(text, encoding='utf-8')
    if count:
        print(f'{path}: normalized {count} conditional googlefcm spread(s)')

print('fake-ip-filter pre-normalization complete')
