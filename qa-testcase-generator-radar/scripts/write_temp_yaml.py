# -*- coding: utf-8 -*-
"""
临时 YAML 写入脚本（qa-worker 专用）
用法: python write_temp_yaml.py <输出路径> < stdin
只允许写入 temp/ 目录。从 stdin 读取 YAML 内容。

示例:
  echo "yaml content" | python write_temp_yaml.py temp/设备购买_v2.yaml
"""
import sys
import os

ALLOWED_OUTPUT_DIR = "temp"

def main():
    if len(sys.argv) < 2:
        print("用法: python write_temp_yaml.py <输出路径>")
        print("内容从 stdin 读取")
        sys.exit(1)

    output_path = sys.argv[1]

    # === 路径安全校验 ===
    resolved = os.path.realpath(output_path)
    allowed = os.path.realpath(ALLOWED_OUTPUT_DIR)
    if not (resolved.startswith(allowed + os.sep) or resolved == allowed):
        print(f"[DENIED] 输出路径必须在 {ALLOWED_OUTPUT_DIR}/ 下，拒绝写入: {output_path}")
        sys.exit(1)

    # 读取 stdin 内容（强制 UTF-8 编码）
    # Windows PowerShell 管道默认用 GBK，需要重新设置 stdin 编码
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    content = sys.stdin.read()
    if not content.strip():
        print("[ERROR] stdin 为空，没有内容可写入")
        sys.exit(1)

    # 创建目录并写入
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] 已写入: {output_path} ({len(content)} bytes)")

if __name__ == '__main__':
    main()
