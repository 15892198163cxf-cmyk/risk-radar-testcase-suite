# -*- coding: utf-8 -*-
"""
YAML → Excel 一体化脚本（qa-worker 专用）
用法: python yaml_to_excel.py <yaml文件路径> <输出xlsx路径>

只允许输出到 temp/ 目录。
YAML 文件必须是 UTF-8 编码。

示例:
  python yaml_to_excel.py temp/xxx.yaml temp/xxx.xlsx
"""
import sys
import os

# 强制 Python UTF-8 模式
os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openpyxl', '-q'])
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

import yaml


ALLOWED_OUTPUT_DIRS = ["temp", "output"]


def generate_excel(yaml_path, output_path):
    """从 YAML 用例文件生成格式化 Excel"""
    # === 路径安全校验 ===
    resolved = os.path.realpath(output_path)
    allowed = False
    for allowed_dir in ALLOWED_OUTPUT_DIRS:
        allowed_path = os.path.realpath(allowed_dir)
        if resolved.startswith(allowed_path + os.sep) or resolved == allowed_path:
            allowed = True
            break
    if not allowed:
        print(f"[DENIED] 输出路径必须在 {ALLOWED_OUTPUT_DIRS} 下，拒绝写入: {output_path}")
        sys.exit(1)

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    wb = Workbook()
    ws = wb.active
    ws.title = "testcases"

    headers = ['业务场景', '优先级', '用例标题', '前置条件', '测试步骤', '预期结果']

    header_font = Font(name='微软雅黑', bold=True, size=11, color='FFFFFF')
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    cell_font = Font(name='微软雅黑', size=10)
    wrap_alignment = Alignment(wrap_text=True, vertical='top')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    p0_fill = PatternFill(start_color='FCE4EC', end_color='FCE4EC', fill_type='solid')
    security_fill = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    row = 2
    for tc in data.get('testcases', []):
        scene = tc.get('scene', '')
        priority = tc.get('priority', '')
        title = tc.get('title', '')
        precondition = tc.get('precondition', '')
        steps = tc.get('steps', '').strip()
        expected = tc.get('expected', '').strip()
        tc_type = tc.get('type', '')

        ws.cell(row=row, column=1, value=scene)
        ws.cell(row=row, column=2, value=priority)
        ws.cell(row=row, column=3, value=title)
        ws.cell(row=row, column=4, value=precondition)
        ws.cell(row=row, column=5, value=steps)
        ws.cell(row=row, column=6, value=expected)

        for col in range(1, 7):
            cell = ws.cell(row=row, column=col)
            cell.font = cell_font
            cell.alignment = wrap_alignment
            cell.border = thin_border

        if tc_type == '安全':
            for col in range(1, 7):
                ws.cell(row=row, column=col).fill = security_fill
        elif priority == 'P0':
            for col in range(1, 7):
                ws.cell(row=row, column=col).fill = p0_fill

        row += 1

    col_widths = {'A': 18, 'B': 8, 'C': 30, 'D': 30, 'E': 45, 'F': 45}
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    ws.freeze_panes = 'A2'

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    wb.save(output_path)

    case_count = row - 2
    module_name = data.get('module', os.path.basename(yaml_path))
    version = data.get('version', '?')
    print(f"[OK] {module_name} v{version} -> {output_path} ({case_count} cases)")
    return case_count


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python yaml_to_excel.py <yaml路径> <输出xlsx路径>")
        sys.exit(1)

    generate_excel(sys.argv[1], sys.argv[2])
