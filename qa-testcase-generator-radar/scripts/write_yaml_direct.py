# -*- coding: utf-8 -*-
"""
直接写入 YAML（qa-worker 专用）
用法: python write_yaml_direct.py <输出路径> <YAML内容>
只允许写入 temp/ 目录。

示例:
  python write_yaml_direct.py temp/test.yaml "testcases:\n  - scene: test"
"""
import sys
import os

ALLOWED_OUTPUT_DIR = "temp"

def main():
    if len(sys.argv) < 3:
        print("用法: python write_yaml_direct.py <输出路径> <YAML内容>")
        sys.exit(1)

    output_path = sys.argv[1]
    content = sys.argv[2]

    # === 路径安全校验 ===
    resolved = os.path.realpath(output_path)
    allowed = os.path.realpath(ALLOWED_OUTPUT_DIR)
    if not (resolved.startswith(allowed + os.sep) or resolved == allowed):
        print(f"[DENIED] 输出路径必须在 {ALLOWED_OUTPUT_DIR}/ 下，拒绝写入: {output_path}")
        sys.exit(1)

    if not content.strip():
        print("[ERROR] 内容为空")
        sys.exit(1)

    # 创建目录并写入
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] 已写入: {output_path} ({len(content.encode('utf-8'))} bytes)")

if __name__ == '__main__':
    main()
