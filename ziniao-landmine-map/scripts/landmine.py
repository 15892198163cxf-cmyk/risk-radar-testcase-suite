from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(os.environ.get("ZINIAO_LANDMINE_ROOT", Path(__file__).resolve().parents[1])).resolve()
DATA_FILE = ROOT / "data" / "landmines.jsonl"
GENERATED_LANDMINES_FILE = ROOT / "data" / "feishu_cluster_landmines.jsonl"
QUERY_ALIASES_FILE = ROOT / "data" / "query_aliases.yaml"
RECALL_RULES_FILE = ROOT / "data" / "recall_rules.yaml"
RAW_DIR = ROOT / "data" / "feishu_raw"
BUG_DETAILS_FILE = RAW_DIR / "feishu_bug_details.jsonl"
ALL_BUG_DETAILS_FILE = RAW_DIR / "all_bug_details.jsonl"
NORMALIZED_BUGS_FILE = ROOT / "data" / "normalized_bugs.jsonl"
CLUSTERS_FILE = ROOT / "data" / "feishu_clusters.json"
REPORT_FILE = ROOT / "data" / "feishu_clusters.md"
SCENARIO_CANDIDATES_FILE = ROOT / "data" / "scenario_candidates.json"
SCENARIO_CANDIDATES_REPORT_FILE = ROOT / "data" / "scenario_candidates.md"
SCENARIO_INDEX_FILE = ROOT / "data" / "scenario_index.json"
RADAR_BENCHMARKS_FILE = ROOT / "data" / "radar_benchmarks.json"
RADAR_EVAL_PLAN_FILE = ROOT / "data" / "radar_eval_plan.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


FEISHU_URL = "https://project.feishu.cn/mcp_server/v1"
FEISHU_PROJECT_KEY = "3zobdi"
FEISHU_VIEW_URL = "https://project.feishu.cn/3zobdi/workObjectView/zxqx/Khmxw2UDR?scope=workspaces&node=30406156"
FEISHU_VIEW_ID = "Khmxw2UDR"
FEISHU_HISTORICAL_VIEW_URL = "https://project.feishu.cn/3zobdi/workObjectView/zxqx/ZZdtquUvR"
FEISHU_HISTORICAL_VIEW_ID = "ZZdtquUvR"
CURRENT_VIEW_SNAPSHOT = RAW_DIR / f"view_{FEISHU_VIEW_ID}_normalized.json"
HISTORICAL_VIEW_SNAPSHOT = RAW_DIR / f"view_{FEISHU_HISTORICAL_VIEW_ID}_normalized.json"
FEISHU_FIELDS = [
    "name",
    "work_item_status",
    "start_time",
    "field_c65ba1",
    "field_24ef5b",
    "field_8a92da",
    "field_1a4393",
    "field_9ad8d4",
    "field_2849cf",
]

DEFAULT_RECALL_RULES = {
    "evidence_priority": {
        "direct_bug": 300,
        "tester_note": 260,
        "feishu_online_bug": 240,
        "derived_cluster": 170,
        "feishu_cluster": 140,
        "qa_inference": 60,
    },
    "match_weights": {
        "preferred_id": 500,
        "canonical_feature": 120,
        "alias_phrase": 90,
        "exact_token": 18,
        "substring": 6,
        "evidence_exact_token": 8,
        "evidence_substring": 3,
        "weak_term_penalty": -20,
        "confirmed_bonus": 25,
        "seed_bonus": 8,
    },
    "minimum_score": 180,
    "generic_cluster_ids": ["ZN-FEISHU-CLUSTER-OTHER-HIGH-FREQ"],
    "suppress_generic_cluster_when_specific_score": 250,
}


SCENARIO_SEEDS = [
    {
        "scenario": "首页账号动态",
        "domain": "管理系统",
        "module": "首页",
        "aliases": ["首页账号动态", "账号动态", "首页动态", "动态列表"],
        "terms": ["账号动态", "动态", "首页", "头像", "列表", "刷新"],
        "issue_patterns": ["动态数据展示异常", "头像或列表状态异常"],
        "must_check": ["切换公司、刷新首页后账号动态数据是否正确", "动态列表中的头像、状态、数量是否和实际账号一致"],
    },
    {
        "scenario": "首页账户余额",
        "domain": "管理系统",
        "module": "首页",
        "aliases": ["首页账户余额", "账户余额", "余额", "余额明细", "充值", "消费"],
        "anchor_terms": ["首页账户余额", "账户余额", "余额", "余额明细"],
        "terms": ["账户余额", "余额", "余额明细", "充值", "消费", "首页"],
        "issue_patterns": ["余额展示或跳转异常", "充值/消费入口状态异常"],
        "must_check": ["首页余额、余额明细、充值/消费入口展示是否一致", "余额为 0、欠费、充值后刷新等状态是否正确"],
    },
    {
        "scenario": "账号列表",
        "domain": "管理系统",
        "module": "账号管理",
        "aliases": ["账号列表", "账号管理列表", "账号菜单"],
        "anchor_terms": ["账号列表", "账号管理列表", "账号菜单"],
        "terms": ["账号列表", "账号管理", "店铺账号", "平台账号", "列表", "筛选", "搜索", "授权成员", "绑定设备", "打开账号", "分页", "排序"],
        "issue_patterns": ["筛选后数据展示不正确", "列表字段/状态刷新异常", "分页或排序异常"],
        "must_check": ["新增/编辑/删除后列表是否刷新", "筛选、搜索、分页、排序、权限字段组合是否正确"],
    },
    {
        "scenario": "账号授权",
        "domain": "管理系统",
        "module": "账号管理",
        "aliases": ["账号授权", "账号列表授权", "授权成员", "成员授权", "部门授权", "角色授权"],
        "anchor_terms": ["账号授权", "账号列表授权", "授权成员", "成员授权"],
        "terms": ["账号授权", "账号列表", "授权成员", "成员", "部门", "角色", "授权人员", "已授权", "未授权", "权限"],
        "issue_patterns": ["授权关系保存时被误清空", "授权对象展示不完整", "授权筛选或数据权限异常", "授权弹窗搜索或交互异常"],
        "must_check": [
            "只编辑无关字段时已有授权关系不被清空",
            "成员、部门、角色混合授权后的列表、弹窗、详情、日志和通知展示完整",
            "已授权/未授权筛选语义与实际授权关系一致",
            "部门子级、角色名称、禁用对象和数据可见范围正确",
            "账号、云号和访问策略共享选择组件的选择、回显和搜索行为一致",
        ],
    },
    {
        "scenario": "账号中心账号设置",
        "domain": "管理系统",
        "module": "紫鸟账号",
        "aliases": ["账号中心账号设置", "账号中心", "账号设置", "紫鸟账号", "登录账号", "成员账号"],
        "anchor_terms": ["账号中心", "账号设置", "紫鸟账号", "登录账号", "成员账号"],
        "terms": ["账号中心", "账号设置", "紫鸟账号", "登录账号", "成员账号", "手机号", "绑定管理", "安全中心", "权限", "移除授权接口"],
        "issue_patterns": ["登录账号权限态异常", "账号设置按钮与接口权限不一致", "手机号/绑定/安全中心状态异常"],
        "must_check": ["BOSS、管理员、小权限成员切换登录后按钮展示和接口权限一致", "手机号、绑定、安全中心操作的成功/失败提示和页面刷新正确"],
    },
    {
        "scenario": "编辑账号",
        "domain": "管理系统",
        "module": "账号管理",
        "aliases": ["编辑账号", "修改账号", "账号编辑", "账号详情编辑"],
        "terms": ["编辑账号", "修改账号", "账号编辑", "保存", "账号详情"],
        "issue_patterns": ["保存后字段不同步", "编辑页校验或回显异常"],
        "must_check": ["编辑后列表、详情、关联店铺信息是否同步", "必填项、特殊字符、权限限制和取消保存路径是否覆盖"],
    },
    {
        "scenario": "复制账号",
        "domain": "管理系统",
        "module": "账号管理",
        "aliases": ["复制账号", "复制", "账号复制", "复制店铺", "店铺复制接口", "复制设备", "左滑复制"],
        "terms": ["复制账号", "复制", "账号", "复制店铺", "店铺复制接口", "左滑复制", "复制设备", "接口响应时间", "clipboard"],
        "issue_patterns": ["复制账号失败", "复制后的账号信息不完整", "复制接口响应慢"],
        "must_check": ["复制后账号基础信息、授权成员、店铺关联是否符合预期", "重复复制、无权限复制、复制失败提示是否正确", "复制接口响应耗时和移动端剪贴板复制是否正常"],
    },
    {
        "scenario": "共享账号",
        "domain": "管理系统",
        "module": "账号管理",
        "aliases": ["共享账号", "账号共享", "分享账号", "被共享"],
        "terms": ["共享账号", "分享账号", "被共享", "共享", "权限"],
        "issue_patterns": ["共享后权限或列表展示异常", "共享关系取消/变更后状态不同步"],
        "must_check": ["共享、取消共享、被共享方查看和权限边界是否正确", "共享后账号列表、详情、操作按钮状态是否同步"],
    },
    {
        "scenario": "急需续费列表",
        "domain": "管理系统",
        "module": "账号管理",
        "aliases": ["急需续费列表", "急需续费", "即将到期", "即将过期", "去续费", "到期提醒"],
        "terms": ["急需续费", "即将到期", "即将过期", "续费", "到期提醒", "结果页"],
        "issue_patterns": ["续费入口/结果页异常", "到期提醒列表展示异常"],
        "must_check": ["即将到期、已过期、已续费账号在列表中的展示和消失时机", "从急需续费入口进入续费、支付完成、返回结果页后的状态刷新"],
    },
    {
        "scenario": "设备回收站",
        "domain": "管理系统",
        "module": "设备管理",
        "aliases": ["设备回收站", "回收站", "设备删除", "恢复设备"],
        "terms": ["设备回收站", "回收站", "删除", "恢复", "设备"],
        "issue_patterns": ["回收站列表/恢复状态异常", "删除后的设备仍可见或不可恢复"],
        "must_check": ["设备删除、恢复、彻底删除后的列表状态", "不同权限、批量操作、刷新后设备状态是否一致"],
    },
    {
        "scenario": "自定义视图",
        "domain": "管理系统",
        "module": "设备管理",
        "aliases": ["自定义视图", "视图", "保存视图", "筛选视图"],
        "anchor_terms": ["自定义视图", "保存视图", "筛选视图"],
        "terms": ["自定义视图", "视图", "筛选", "保存", "字段", "排序"],
        "issue_patterns": ["自定义视图保存或切换异常", "视图字段/筛选条件丢失"],
        "must_check": ["新增、编辑、删除、切换视图后筛选条件和字段是否保留", "多人/多角色下默认视图和自定义视图是否隔离"],
    },
    {
        "scenario": "云号购买",
        "domain": "管理系统",
        "module": "云号管理",
        "aliases": ["云号购买", "购买云号", "云号的购买", "购买"],
        "anchor_terms": ["云号购买", "购买云号", "云号的购买", "云号", "订单号"],
        "terms": ["云号", "订单号", "购买", "支付", "订单", "套餐", "开通", "续费"],
        "issue_patterns": ["云号购买无同名直接 Bug 时，优先参考云号订单/筛选状态风险", "订单/支付流程异常"],
        "must_check": ["管理系统购买后，管理系统内云号状态、数量、订单结果是否可见", "支付取消、失败、重复点击、刷新后的状态一致性"],
    },
    {
        "scenario": "云号替换记录",
        "domain": "运维后台",
        "module": "云号管理",
        "aliases": ["云号替换记录", "云号替换", "替换记录", "替换记录列表", "替换日志", "替换回调", "变更记录"],
        "anchor_terms": ["云号替换记录", "云号替换", "替换记录", "替换回调", "替换日志"],
        "terms": ["云号", "替换", "替换记录", "替换日志", "替换回调", "记录表", "变更记录", "查询", "列表", "替换前", "替换后"],
        "issue_patterns": ["替换成功但记录未写入", "替换记录列表查询不到真实记录", "替换前后对象查询口径不一致"],
        "must_check": ["替换成功、失败、回调延迟和多入口替换是否都写入记录", "按替换前云号和替换后云号都能查到对应替换链路"],
    },
    {
        "scenario": "黑名单管理",
        "domain": "管理系统",
        "module": "云号管理",
        "aliases": ["黑名单管理", "黑名单", "云号黑名单"],
        "terms": ["黑名单", "黑名单管理", "云号", "拉黑", "解除"],
        "issue_patterns": ["黑名单新增/移除后状态异常", "黑名单权限或列表展示异常"],
        "must_check": ["添加、移除、搜索黑名单后的云号状态", "不同权限、重复添加、已解除后的列表刷新"],
    },
    {
        "scenario": "添加成员",
        "domain": "管理系统",
        "module": "企业管理",
        "aliases": ["添加成员", "创建成员", "新增成员", "成员管理"],
        "terms": ["添加成员", "创建成员", "新增成员", "成员", "部门", "权限", "邀请"],
        "issue_patterns": ["成员新增后权限/列表异常", "邀请或登录状态异常"],
        "must_check": ["添加成员后列表、角色、部门、登录权限是否正确", "重复添加、无权限添加、邀请状态刷新"],
    },
    {
        "scenario": "部门管理",
        "domain": "管理系统",
        "module": "企业管理",
        "aliases": ["部门管理", "新增部门", "编辑部门", "删除部门"],
        "terms": ["部门管理", "部门", "新增部门", "编辑部门", "删除部门", "成员"],
        "issue_patterns": ["部门新增/编辑/删除状态异常", "部门成员关系不同步"],
        "must_check": ["新增、编辑、删除部门后成员归属和列表刷新", "有成员部门、空部门、权限受限场景"],
    },
    {
        "scenario": "添加监管账号",
        "domain": "管理系统",
        "module": "安全监管",
        "aliases": ["添加监管账号", "新增监管账号", "监管账号", "监管对象"],
        "terms": ["添加监管账号", "监管账号", "监管对象", "生效账号", "事中监管", "安全监管"],
        "issue_patterns": ["监管对象或生效账号配置异常", "监管账号新增后状态不同步"],
        "must_check": ["添加监管账号后监管对象、生效账号、列表状态是否正确", "无权限、重复添加、删除后再次添加"],
    },
    {
        "scenario": "访问策略",
        "domain": "管理系统/店铺内",
        "module": "安全监管",
        "aliases": ["访问策略", "会员安全策略", "生效成员", "策略生效", "启用策略", "禁用策略"],
        "anchor_terms": ["访问策略", "会员安全策略", "策略生效", "生效成员"],
        "terms": ["访问策略", "会员安全策略", "生效成员", "策略生效", "页面拦截", "元素拦截", "启用策略", "禁用策略", "特例", "店铺"],
        "reject_terms": ["事中监管", "监管日志", "监管账号", "监管对象", "告警方案"],
        "issue_patterns": ["策略配置和店铺内执行不一致", "成员/部门/角色生效范围异常", "已打开店铺是否立即生效不明确"],
        "must_check": ["配置端启用/禁用/修改后权限范围和状态刷新正确", "新开店铺、刷新店铺、已打开店铺下访问策略执行结果是否符合预期"],
    },
    {
        "scenario": "打开店铺链路",
        "domain": "店铺内",
        "module": "店铺环境",
        "aliases": ["打开店铺链路", "打开店铺", "启动店铺", "店铺启动", "批量启动", "店铺检测页"],
        "anchor_terms": ["打开店铺", "启动店铺", "店铺启动", "店铺检测页"],
        "terms": ["打开店铺", "启动店铺", "店铺启动", "批量启动", "店铺检测页", "IP检测", "代理", "cookie", "内核", "启动卡住"],
        "issue_patterns": ["打开店铺或启动队列异常", "IP检测/代理/cookie链路异常", "启动失败后影响后续店铺"],
        "must_check": ["打开店铺时环境安全检测/IP网络、代理、cookie、托管账密自动填充是否符合预期", "单店铺失败不能卡住后续启动，关闭/重试/重新打开状态正确"],
    },
    {
        "scenario": "本地端口",
        "domain": "客户端",
        "module": "客户端",
        "aliases": ["本地端口", "端口分配", "端口占用", "端口兜底", "本地服务", "客户端和内核通信"],
        "anchor_terms": ["本地端口", "端口分配", "端口占用", "端口兜底", "本地服务"],
        "terms": ["本地端口", "端口分配", "端口占用", "端口兜底", "本地服务", "客户端", "内核通信", "打开店铺", "多开"],
        "issue_patterns": ["端口被占用后兜底失败", "端口释放或进程残留异常", "客户端和内核通信仍请求旧端口"],
        "must_check": ["默认端口被占用、连续端口被占用、端口释放后重新打开店铺", "多开工作台下不同店铺端口和进程互不影响"],
    },
    {
        "scenario": "多开工作台",
        "domain": "客户端",
        "module": "客户端",
        "aliases": ["多开工作台", "开启多开", "多开", "多工作台", "工作台隔离"],
        "anchor_terms": ["多开工作台", "开启多开", "多工作台"],
        "terms": ["多开工作台", "开启多开", "多开", "工作台", "打开店铺", "进程残留", "端口", "隔离"],
        "issue_patterns": ["多开后打开店铺互相影响", "退出客户端后进程残留", "多工作台端口或状态串扰"],
        "must_check": ["开启多开后不同工作台打开的账号互不影响", "退出、重启、URL唤起打开店铺后进程和端口释放正确"],
    },
    {
        "scenario": "缓存路径设置",
        "domain": "客户端",
        "module": "设置",
        "aliases": ["缓存路径设置", "缓存管理", "文件下载设置", "客户端下载设置", "下载设置", "下载弹窗", "路径冲突", "店铺文件下载路径", "内核下载文件", "内核解压文件", "内核缓存"],
        "terms": ["缓存管理", "缓存路径", "文件下载设置", "客户端下载设置", "下载设置", "下载弹窗", "路径冲突", "店铺文件下载路径", "账号临时缓存", "紫鸟客户端缓存", "内核下载", "内核解压", "内核缓存", "安装目录", "appdata", "误删除", "卡住"],
        "issue_patterns": ["路径冲突导致误删风险", "下载/缓存路径设置不同步", "破坏缓存后店铺启动异常"],
        "must_check": ["账号缓存、客户端缓存、店铺下载、内核下载/解压路径展示和打开能力", "路径冲突启动检测、暂不处理/去处理、关闭弹窗和跳转文件下载设置", "路径与安装目录或其他缓存目录相同/父子级时的风险提示"],
    },
    {
        "scenario": "书签相关",
        "domain": "店铺内",
        "module": "店铺",
        "aliases": ["书签", "收藏", "文件夹重命名", "链接修改"],
        "terms": ["书签", "收藏", "文件夹", "重命名", "链接", "新建"],
        "issue_patterns": ["书签文件夹或链接编辑后状态异常"],
        "must_check": ["书签新增、重命名、删除、修改链接后的展示和同步", "多店铺/多窗口下书签状态是否隔离"],
    },
]


GENERIC_SCENARIO_CANDIDATES = {
    "v5",
    "v6",
    "ios",
    "安卓",
    "移动端",
    "客户端",
    "管理系统",
    "线上问题",
    "历史问题",
    "前端改",
    "代码错误",
    "异常",
    "首页",
    "账号",
    "账号管理",
    "设备",
    "设备管理",
    "云号",
    "云号管理",
    "管理",
    "企业管理",
    "安全",
    "安全监管",
    "费用管理",
    "服务",
    "官网",
}


GENERIC_SCENARIO_TERMS = {
    *GENERIC_SCENARIO_CANDIDATES,
    "列表",
    "视图",
    "页面",
    "功能",
    "设置",
    "新增",
    "编辑",
    "修改",
    "删除",
    "复制",
    "购买",
    "保存",
    "状态",
    "筛选",
    "搜索",
    "刷新",
    "权限",
    "成员",
    "部门",
}


def parse_simple_yaml(path: Path) -> dict:
    if not path.exists():
        return {}

    document: dict = {}
    stack: list[tuple[int, object]] = [(-1, document)]
    pending_key: tuple[int, dict, str] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        text = raw_line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if text.startswith("- "):
            value = parse_scalar(text[2:].strip())
            if not isinstance(parent, list):
                if pending_key is None:
                    raise SystemExit(f"List item without list parent in {path}: {raw_line}")
                _, pending_parent, key = pending_key
                new_list: list = []
                pending_parent[key] = new_list
                stack.append((pending_key[0], new_list))
                parent = new_list
            parent.append(value)
            continue

        if ":" not in text:
            continue
        key, value_text = text.split(":", 1)
        key = key.strip()
        value_text = value_text.strip()
        if value_text:
            value = parse_scalar(value_text)
            if isinstance(parent, dict):
                parent[key] = value
            pending_key = None
        else:
            value = {}
            if isinstance(parent, dict):
                parent[key] = value
            stack.append((indent, value))
            pending_key = (indent, parent, key)
    return document


def parse_scalar(value: str):
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value in {"true", "false"}:
        return value == "true"
    return value.strip("\"'")


def load_alias_config() -> dict:
    return parse_simple_yaml(QUERY_ALIASES_FILE)


def load_recall_rules() -> dict:
    rules = DEFAULT_RECALL_RULES.copy()
    loaded = parse_simple_yaml(RECALL_RULES_FILE)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(rules.get(key), dict):
            merged = dict(rules[key])
            merged.update(value)
            rules[key] = merged
        else:
            rules[key] = value
    return rules


def load_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    if not path.exists():
        return items
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    return items


def load_landmines(path: Path | None = None) -> list[dict]:
    if path is not None:
        return load_jsonl(path)

    items: list[dict] = []
    seen: set[str] = set()
    for source in [DATA_FILE, GENERATED_LANDMINES_FILE]:
        for item in load_jsonl(source):
            item_id = item.get("id")
            if item_id and item_id in seen:
                continue
            if item_id:
                seen.add(item_id)
            items.append(item)
    return items


def mcp_request(method: str, params: dict | None = None, session_id: str | None = None, request_id: int = 1) -> tuple[dict | None, str | None]:
    import os

    token = os.environ.get("FEISHU_PROJECT_MCP_TOKEN")
    if not token:
        raise SystemExit("FEISHU_PROJECT_MCP_TOKEN is not set.")

    headers = {
        "X-Mcp-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params

    request = urllib.request.Request(
        FEISHU_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
            new_session_id = response.headers.get("Mcp-Session-Id") or session_id
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"MCP HTTP {exc.code}: {body[:1000]}") from exc

    if not raw.strip():
        return None, new_session_id
    return parse_mcp_response(raw), new_session_id


def parse_mcp_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("data:"):
        chunks = []
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunks.append(line[5:].strip())
        raw = "\n".join(chunks).strip()
    return json.loads(raw)


def mcp_initialize() -> str:
    _, session_id = mcp_request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ziniao-landmine-map", "version": "1.0"},
        },
        request_id=1,
    )
    if not session_id:
        raise SystemExit("MCP initialize did not return a session id.")
    return session_id


def call_mcp_tool(session_id: str, name: str, arguments: dict, request_id: int) -> dict:
    payload, _ = mcp_request("tools/call", {"name": name, "arguments": arguments}, session_id=session_id, request_id=request_id)
    if not payload:
        raise SystemExit(f"Empty MCP response from {name}.")
    if "error" in payload:
        raise SystemExit(json.dumps(payload["error"], ensure_ascii=False))
    result = payload.get("result", {})
    content = result.get("content", [])
    if not content:
        return result
    first = content[0]
    if first.get("type") == "text":
        return json.loads(first.get("text", "{}"))
    return result


def extract_field(fields: list[dict], key: str):
    for field in fields:
        if field.get("key") == key:
            return field.get("value")
    return None


def label_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "string_value" in value:
            return str(value["string_value"])
        if "iso_time" in value:
            return str(value["iso_time"])
        if "label" in value:
            return str(value["label"])
        if "name" in value:
            return str(value["name"])
        if "key_label_value_list" in value:
            return "/".join(item.get("label", "") for item in value["key_label_value_list"])
        if "cascade_key_label_value_list" in value:
            return "/".join(item.get("label", "") for item in value["cascade_key_label_value_list"])
    if isinstance(value, list):
        labels = []
        for item in value:
            if isinstance(item, dict):
                labels.append(str(item.get("label") or item.get("name") or item.get("value") or ""))
            else:
                labels.append(str(item))
        return ";".join(label for label in labels if label)
    return str(value)


def clean_detail_text(value) -> str:
    text = label_value(value)
    if not text:
        return ""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)(?:<!--.*?-->)?", "", text)
    text = re.sub(r"<!--.*?-->", "", text)
    text = re.sub(r"\[[^\]]*(?:https?://|www\.|mailto:)[^\]]*\]\([^)]*\)", "[URL]", text)
    text = re.sub(r"\[([^\]]+)\]\((?:https?|mailto):[^)]*\)", lambda m: "[URL]" if re.match(r"https?://|www\.|[\w.-]+\.[A-Za-z]{2,}", m.group(1)) else m.group(1), text)
    text = re.sub(r"\[([^\]]{0,80})\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[[^\]]*(?:https?://|www\.)[^\]]*\]", "[URL]", text)
    text = re.sub(r"https?://\S+|www\.\S+", "[URL]", text)
    text = re.sub(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]", text)
    text = re.sub(r"\b1[3-9]\d{9}\b", "[PHONE]", text)
    text = re.sub(r"(?<!\d)\d{12,}(?!\d)", "[ID]", text)
    text = re.sub(r"(验证码[：:])\s*\d{4,8}", r"\1 [CODE]", text)
    text = re.sub(r"(?i)\b(companyId|userId|removeStoreId|store_id|taskId|shareId|organizeId)\b\s*[:=]\s*['\"]?[^,\s\"'}]+", r"\1=[REDACTED]", text)
    text = re.sub(r"(?m)^.*(?:密码|账号名|用户名|正式账号|测试账号|线上账号|热更账号|手机号|公司名)[：:]\s*.+$", lambda m: redact_sensitive_line(m.group(0)), text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def redact_sensitive_line(line: str) -> str:
    safe_prefixes = ["账号列表", "账号管理", "账号详情", "账号设置", "账号权限", "手机号验证"]
    if any(prefix in line for prefix in safe_prefixes) and not re.search(r"(密码|用户名|账号名|正式账号|测试账号|线上账号|热更账号|公司名)[：:]", line):
        return line
    return re.sub(r"([：:])\s*.*$", r"\1 [REDACTED]", line)


DETAIL_SECTION_NAMES = {
    "steps": ["重现步骤", "复现步骤", "操作步骤"],
    "actual_result": ["测试结果", "实际结果", "现象", "问题现象"],
    "expected_result": ["期望结果", "预期结果"],
}


def extract_markdown_section(text: str, headings: list[str]) -> str:
    if not text:
        return ""
    heading_pattern = "|".join(re.escape(name) for name in headings)
    all_headings = []
    for names in DETAIL_SECTION_NAMES.values():
        all_headings.extend(names)
    all_heading_pattern = "|".join(re.escape(name) for name in all_headings)
    pattern = re.compile(
        rf"(?:^|\n)\s*(?:\*\*)?\s*({heading_pattern})\s*(?:\*\*)?\s*\n(?P<body>.*?)(?=\n\s*(?:\*\*)?\s*(?:{all_heading_pattern})\s*(?:\*\*)?\s*\n|\Z)",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return trim_numbered_blanks(match.group("body"))


def trim_numbered_blanks(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"\d+[.、]\s*", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def compact_lines(text: str, limit: int = 6) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip(" -\t")
        if not line:
            continue
        if re.fullmatch(r"\d+[.、]\s*", line):
            continue
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def extract_keywords_from_text(*parts: str) -> list[str]:
    text = " ".join(part for part in parts if part)
    keywords: list[str] = []
    for bracketed in re.findall(r"【([^】]{1,30})】", text):
        for token in re.split(r"[-/｜|、，,;\s]+", bracketed):
            token = token.strip()
            if token and token not in keywords:
                keywords.append(token)
    for token in re.findall(r"[A-Za-z0-9_./-]{2,}|[\u4e00-\u9fff]{2,10}", text):
        token = token.strip()
        if token and token not in keywords:
            keywords.append(token)
        if len(keywords) >= 30:
            break
    return keywords[:30]


def fields_by_key(fields: list[dict]) -> dict[str, dict]:
    return {field.get("key"): field for field in fields if field.get("key")}


def normalize_detail_work_item(data: dict, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    attr = data.get("work_item_attribute", {})
    fields = data.get("work_item_fields", [])
    by_key = fields_by_key(fields)
    remark = clean_detail_text(by_key.get("field_318642", {}).get("value"))
    fix_plan = clean_detail_text(by_key.get("field_45f401", {}).get("value"))

    def field_label(key: str) -> str:
        return label_value(by_key.get(key, {}).get("value"))

    return {
        "id": str(attr.get("work_item_id") or fallback.get("id") or ""),
        "title": attr.get("work_item_name") or fallback.get("title") or "",
        "status": (attr.get("work_item_status") or {}).get("name") or fallback.get("status") or "",
        "created_at": field_label("start_time") or attr.get("create_time") or fallback.get("created_at") or "",
        "updated_at": field_label("updated_at") or attr.get("update_time") or "",
        "category": field_label("field_24ef5b") or fallback.get("category") or "",
        "module": field_label("field_8a92da") or fallback.get("module") or "",
        "severity": field_label("field_1a4393") or fallback.get("severity") or "",
        "defect_type": field_label("field_9ad8d4") or fallback.get("defect_type") or "",
        "priority": field_label("field_2849cf") or fallback.get("priority") or "",
        "remark": remark,
        "steps": extract_markdown_section(remark, DETAIL_SECTION_NAMES["steps"]),
        "actual_result": extract_markdown_section(remark, DETAIL_SECTION_NAMES["actual_result"]),
        "expected_result": extract_markdown_section(remark, DETAIL_SECTION_NAMES["expected_result"]),
        "fix_plan": fix_plan,
        "source": "feishu_detail",
    }


def normalize_work_item(item: dict) -> dict:
    attr = item.get("work_item_attribute", {})
    fields = item.get("work_item_fields", [])
    return {
        "id": attr.get("work_item_id"),
        "title": attr.get("work_item_name"),
        "status": (attr.get("work_item_status") or {}).get("name"),
        "created_at": label_value(extract_field(fields, "start_time")) or attr.get("create_time"),
        "created_date": label_value(extract_field(fields, "field_c65ba1")),
        "category": label_value(extract_field(fields, "field_24ef5b")),
        "module": label_value(extract_field(fields, "field_8a92da")),
        "severity": label_value(extract_field(fields, "field_1a4393")),
        "defect_type": label_value(extract_field(fields, "field_9ad8d4")),
        "priority": label_value(extract_field(fields, "field_2849cf")),
    }


def cmd_import_feishu(args: argparse.Namespace) -> None:
    view_id = args.view_id or FEISHU_VIEW_ID
    view_url = args.view_url or (
        FEISHU_VIEW_URL
        if view_id == FEISHU_VIEW_ID
        else f"https://project.feishu.cn/{FEISHU_PROJECT_KEY}/workObjectView/zxqx/{view_id}"
    )
    session_id = mcp_initialize()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    page_num = 1
    request_id = 10
    while True:
        data = call_mcp_tool(
            session_id,
            "get_view_detail",
            {
                "project_key": FEISHU_PROJECT_KEY,
                "view_id": view_id,
                "url": view_url,
                "fields": FEISHU_FIELDS,
                "page_num": page_num,
            },
            request_id,
        )
        if args.save_pages:
            raw_path = RAW_DIR / f"view_{view_id}_page_{page_num:03d}.json"
            raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        normalized = [normalize_work_item(item) for item in data.get("work_item_list", [])]
        all_items.extend(normalized)

        pagination = data.get("pagination", {})
        print(f"Fetched page {page_num}: {len(normalized)} items")
        if not pagination.get("has_more"):
            break
        page_num += 1
        request_id += 1
        if args.max_pages and page_num > args.max_pages:
            break
        time.sleep(args.sleep)

    output = {
        "source": {
            "project_key": FEISHU_PROJECT_KEY,
            "view_id": view_id,
            "view_url": view_url,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        },
        "total": len(all_items),
        "items": all_items,
    }
    out_path = Path(args.output) if args.output else RAW_DIR / f"view_{view_id}_normalized.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_items)} normalized items to {out_path}")


def load_view_document(path: Path | None = None) -> dict:
    source_path = path or (RAW_DIR / f"view_{FEISHU_VIEW_ID}_normalized.json")
    return json.loads(source_path.read_text(encoding="utf-8"))


def load_view_items(path: Path | None = None) -> list[dict]:
    return load_view_document(path).get("items", [])


def view_item_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        str(item.get("id") or "")
        for item in load_view_items(path)
        if item.get("id")
    }


def build_view_membership_index() -> dict[str, dict[str, list[str]]]:
    memberships: dict[str, dict[str, list[str]]] = {}
    sources = [
        ("current_182d", FEISHU_VIEW_ID, CURRENT_VIEW_SNAPSHOT),
        ("historical_view", FEISHU_HISTORICAL_VIEW_ID, HISTORICAL_VIEW_SNAPSHOT),
    ]
    for membership, view_id, path in sources:
        for item_id in view_item_ids(path):
            entry = memberships.setdefault(item_id, {"view_memberships": [], "source_view_ids": []})
            entry["view_memberships"].append(membership)
            entry["source_view_ids"].append(view_id)
    return memberships


def apply_view_membership(row: dict, membership_index: dict[str, dict[str, list[str]]]) -> dict:
    item_id = str(row.get("id") or "")
    membership = membership_index.get(item_id, {"view_memberships": [], "source_view_ids": []})
    result = dict(row)
    result["view_memberships"] = list(membership["view_memberships"])
    result["source_view_ids"] = list(membership["source_view_ids"])
    result["window_status"] = "current" if "current_182d" in result["view_memberships"] else "archived"
    if FEISHU_VIEW_ID in result["source_view_ids"]:
        result["source_view_id"] = FEISHU_VIEW_ID
        result["source_view_url"] = FEISHU_VIEW_URL
    elif FEISHU_HISTORICAL_VIEW_ID in result["source_view_ids"]:
        result["source_view_id"] = FEISHU_HISTORICAL_VIEW_ID
        result["source_view_url"] = FEISHU_HISTORICAL_VIEW_URL
    return result


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_existing_detail_rows(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for row in load_jsonl(path):
        if row.get("id"):
            rows[str(row["id"])] = row
    return rows


def default_detail_source_path() -> Path:
    return ALL_BUG_DETAILS_FILE if ALL_BUG_DETAILS_FILE.exists() else BUG_DETAILS_FILE


def created_at_timestamp(row: dict) -> float:
    value = str(row.get("created_at") or "").strip()
    if not value:
        return 0.0
    normalized = value.replace("Z", "+00:00")
    for parser in (
        lambda text: datetime.fromisoformat(text),
        lambda text: datetime.strptime(text, "%Y/%m/%d %H:%M:%S"),
        lambda text: datetime.strptime(text, "%Y/%m/%d"),
    ):
        try:
            return parser(normalized).timestamp()
        except ValueError:
            continue
    return 0.0


def bug_recency_adjustment(row: dict, reference_time: datetime | None = None) -> tuple[int, str]:
    created_timestamp = created_at_timestamp(row)
    if created_timestamp <= 0:
        return 0, "age_unknown"
    reference = reference_time or datetime.now(timezone.utc)
    age_days = max(0, int((reference.timestamp() - created_timestamp) // 86400))
    if age_days < 182:
        return 20, "recent_182_days"
    if age_days < 365:
        return 5, "age_182_364_days"
    return -5, "age_365_plus_days"


def detail_sort_key(row: dict) -> tuple[float, str]:
    return (created_at_timestamp(row), str(row.get("id") or ""))


def ranked_bug_sort_key(pair: tuple[int, dict, list[str]]) -> tuple[int, float, str]:
    score, row, _ = pair
    return (-score, -created_at_timestamp(row), str(row.get("id") or ""))


def write_detail_stores(all_rows: dict[str, dict], current_ids: list[str]) -> tuple[int, int]:
    membership_index = build_view_membership_index()
    for item_id, row in list(all_rows.items()):
        all_rows[item_id] = apply_view_membership(row, membership_index)
    all_ordered = sorted(all_rows.values(), key=detail_sort_key, reverse=True)
    current_rows = [
        all_rows[item_id]
        for item_id in current_ids
        if item_id in all_rows and "current_182d" in all_rows[item_id].get("view_memberships", [])
    ]
    write_jsonl(ALL_BUG_DETAILS_FILE, all_ordered)
    write_jsonl(BUG_DETAILS_FILE, current_rows)
    return len(all_ordered), len(current_rows)


def fetch_workitem_all_fields(session_id: str, item_id: str, request_id: int) -> dict:
    merged: dict | None = None
    page_token: str | None = None
    while True:
        arguments = {
            "project_key": FEISHU_PROJECT_KEY,
            "work_item_id": item_id,
            "fields": ["_all"],
            "page_size": 200,
        }
        if page_token:
            arguments["page_token"] = page_token
        data = call_mcp_tool(session_id, "get_workitem_brief", arguments, request_id)
        if merged is None:
            merged = data
        else:
            merged.setdefault("work_item_fields", []).extend(data.get("work_item_fields", []))
        pagination = data.get("pagination", {})
        if not pagination.get("has_more"):
            break
        page_token = pagination.get("next_page_token")
        if not page_token:
            break
        request_id += 1
    return merged or {}


def cmd_import_details(args: argparse.Namespace) -> None:
    imported_at = datetime.now(timezone.utc).isoformat()
    source_path = Path(args.source) if args.source else None
    source_document = load_view_document(source_path)
    all_view_items = source_document.get("items", [])
    current_source_path = Path(args.current_source) if args.current_source else source_path
    current_document = load_view_document(current_source_path)
    current_view_items = current_document.get("items", [])
    current_ids = [str(item.get("id") or "") for item in current_view_items if item.get("id")]
    current_id_set = set(current_ids)
    view_items = all_view_items[: args.limit] if args.limit else all_view_items
    source_metadata = source_document.get("source", {})
    current_metadata = current_document.get("source", {})

    existing_path = default_detail_source_path()
    all_rows = read_existing_detail_rows(existing_path) if existing_path.exists() else {}
    legacy_rows = read_existing_detail_rows(BUG_DETAILS_FILE) if BUG_DETAILS_FILE.exists() else {}
    for item_id, row in legacy_rows.items():
        all_rows.setdefault(item_id, row)

    session_id: str | None = None
    request_id = 100
    fetched = 0
    cached = 0
    newly_added = 0

    for index, item in enumerate(view_items, 1):
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        was_known = item_id in all_rows
        if args.resume and was_known:
            detail = dict(all_rows[item_id])
            cached += 1
            print(f"[{index}/{len(view_items)}] cached {item_id}")
        else:
            if session_id is None:
                session_id = mcp_initialize()
            data = fetch_workitem_all_fields(session_id, item_id, request_id)
            detail = normalize_detail_work_item(data, fallback=item)
            request_id += 10
            fetched += 1
            newly_added += 0 if was_known else 1
            print(f"[{index}/{len(view_items)}] fetched {item_id}: {detail.get('title')}")

        is_current = item_id in current_id_set
        metadata = current_metadata if is_current else source_metadata
        detail.update(
            {
                "window_status": "current" if is_current else "archived",
                "source_view_id": metadata.get("view_id") or FEISHU_VIEW_ID,
                "source_view_url": metadata.get("view_url") or FEISHU_VIEW_URL,
                "window_imported_at": imported_at,
                "archived_at": "" if is_current else detail.get("archived_at") or imported_at,
            }
        )
        if is_current:
            detail["last_seen_in_window"] = imported_at
        all_rows[item_id] = detail
        if args.flush_each:
            write_detail_stores(all_rows, current_ids)
        if args.sleep:
            time.sleep(args.sleep)

    archived = 0
    for item_id, detail in all_rows.items():
        if item_id in current_id_set:
            detail["window_status"] = "current"
            detail["archived_at"] = ""
            continue
        if detail.get("source") != "feishu_detail":
            continue
        if detail.get("window_status") != "archived":
            detail["archived_at"] = imported_at
        detail["window_status"] = "archived"
        archived += 1

    all_count, current_count = write_detail_stores(all_rows, current_ids)
    print(f"Wrote {current_count} current-window detail rows to {BUG_DETAILS_FILE}")
    print(f"Wrote {all_count} long-term detail rows to {ALL_BUG_DETAILS_FILE}")
    print(f"Fetched: {fetched}; cached: {cached}; new: {newly_added}; archived outside current view: {archived}")


def normalized_bug_from_detail(
    detail: dict,
    membership_index: dict[str, dict[str, list[str]]] | None = None,
) -> dict:
    detail = apply_view_membership(detail, membership_index or build_view_membership_index())
    steps = detail.get("steps") or ""
    actual = detail.get("actual_result") or ""
    expected = detail.get("expected_result") or ""
    fix_plan = detail.get("fix_plan") or ""
    title = detail.get("title") or ""
    module = detail.get("module") or ""
    category = detail.get("category") or ""
    trigger_lines = compact_lines(steps, limit=4)
    failure_lines = compact_lines(actual, limit=4)
    fix_lines = compact_lines(fix_plan, limit=3)
    return {
        "id": detail.get("id"),
        "title": title,
        "status": detail.get("status", ""),
        "category": category,
        "module": module,
        "severity": detail.get("severity", ""),
        "defect_type": detail.get("defect_type", ""),
        "priority": detail.get("priority", ""),
        "created_at": detail.get("created_at", ""),
        "updated_at": detail.get("updated_at", ""),
        "window_status": detail.get("window_status", "current"),
        "last_seen_in_window": detail.get("last_seen_in_window", ""),
        "archived_at": detail.get("archived_at", ""),
        "source_view_id": detail.get("source_view_id", ""),
        "view_memberships": list(detail.get("view_memberships", [])),
        "source_view_ids": list(detail.get("source_view_ids", [])),
        "trigger_conditions": trigger_lines,
        "failure_symptoms": failure_lines or compact_lines(title, limit=1),
        "expected_result": compact_lines(expected, limit=4),
        "fix_clues": fix_lines,
        "keywords": extract_keywords_from_text(title, module, category, steps, actual, expected, fix_plan),
        "evidence": [f"{detail.get('id')}: {title}"],
        "has_detail": bool(detail.get("remark") or detail.get("fix_plan")),
    }


def cmd_normalize_bugs(args: argparse.Namespace) -> None:
    details_path = Path(args.source) if args.source else default_detail_source_path()
    details = load_jsonl(details_path)
    membership_index = build_view_membership_index()
    rows = [normalized_bug_from_detail(detail, membership_index) for detail in details]
    write_jsonl(NORMALIZED_BUGS_FILE, rows)
    with_detail = sum(1 for row in rows if row.get("has_detail"))
    with_fix = sum(1 for detail in details if detail.get("fix_plan"))
    with_steps = sum(1 for detail in details if detail.get("steps"))
    by_window = Counter(row.get("window_status", "current") for row in rows)
    print(f"Wrote {len(rows)} normalized bugs to {NORMALIZED_BUGS_FILE}")
    print(f"Source detail file: {details_path}")
    print(f"Window status: {dict(by_window)}")
    print(f"With detail text: {with_detail}; with steps: {with_steps}; with fix plan: {with_fix}")


def cmd_refresh_view_memberships(args: argparse.Namespace) -> None:
    details_path = Path(args.source) if args.source else default_detail_source_path()
    all_rows = read_existing_detail_rows(details_path)
    current_ids = list(view_item_ids(CURRENT_VIEW_SNAPSHOT))
    all_count, current_count = write_detail_stores(all_rows, current_ids)
    print(f"Refreshed view memberships for {all_count} archived Bugs")
    print(f"Current-window detail rows: {current_count}")


def cmd_sanitize_details(args: argparse.Namespace) -> None:
    details_path = Path(args.source) if args.source else default_detail_source_path()
    details = load_jsonl(details_path)
    text_fields = ["remark", "steps", "actual_result", "expected_result", "fix_plan"]
    sanitized = []
    for detail in details:
        row = dict(detail)
        for field in text_fields:
            row[field] = clean_detail_text(row.get(field, ""))
        sanitized.append(row)
    write_jsonl(details_path, sanitized)
    print(f"Sanitized {len(sanitized)} detail rows in {details_path}")


def normalized_bug_text(row: dict) -> str:
    fields = [
        row.get("id", ""),
        row.get("title", ""),
        row.get("module", ""),
        row.get("category", ""),
        row.get("severity", ""),
        row.get("defect_type", ""),
        row.get("priority", ""),
        " ".join(row.get("keywords", [])),
        " ".join(row.get("trigger_conditions", [])),
        " ".join(row.get("failure_symptoms", [])),
        " ".join(row.get("expected_result", [])),
        " ".join(row.get("fix_clues", [])),
        " ".join(row.get("evidence", [])),
    ]
    return normalize_text(" ".join(str(value) for value in fields))


def scenario_seed_score(row: dict, seed: dict) -> tuple[int, list[str]]:
    title = normalize_text(row.get("title", ""))
    module = normalize_text(row.get("module", ""))
    category = normalize_text(row.get("category", ""))
    keywords = normalize_text(" ".join(row.get("keywords", [])))
    trigger = normalize_text(" ".join(row.get("trigger_conditions", [])))
    failure = normalize_text(" ".join(row.get("failure_symptoms", [])))
    fix = normalize_text(" ".join(row.get("fix_clues", [])))
    haystack = " ".join([title, module, category, keywords, trigger, failure, fix])

    score = 0
    reasons: list[str] = []
    matched_terms: set[str] = set()
    aliases = [seed["scenario"], *seed.get("aliases", [])]
    terms = list(dict.fromkeys([*aliases, *seed.get("terms", [])]))
    anchors = seed.get("anchor_terms") or [term for term in terms if normalize_text(term) not in GENERIC_SCENARIO_TERMS and len(normalize_text(term)) >= 2]
    specific_hit = False

    for reject_term in seed.get("reject_terms", []):
        reject_norm = normalize_text(reject_term)
        if reject_norm and reject_norm in haystack:
            return 0, [f"reject:{reject_term}"]

    for term in terms:
        term_norm = normalize_text(term)
        if not term_norm:
            continue
        if term_norm in title:
            score += 45
            reasons.append(f"title:{term}")
            matched_terms.add(term_norm)
            specific_hit = specific_hit or term in anchors
        elif term_norm in module:
            score += 28
            reasons.append(f"module:{term}")
            matched_terms.add(term_norm)
            specific_hit = specific_hit or term in anchors
        elif term_norm in category:
            score += 22
            reasons.append(f"category:{term}")
            matched_terms.add(term_norm)
            specific_hit = specific_hit or term in anchors
        elif term_norm in keywords:
            score += 18
            reasons.append(f"keyword:{term}")
            matched_terms.add(term_norm)
            specific_hit = specific_hit or term in anchors
        elif term_norm in trigger or term_norm in failure or term_norm in fix:
            score += 14
            reasons.append(f"detail:{term}")
            matched_terms.add(term_norm)
            specific_hit = specific_hit or term in anchors
        elif term_norm in haystack:
            score += 8
            reasons.append(f"substring:{term}")
            matched_terms.add(term_norm)
            specific_hit = specific_hit or term in anchors

    if not specific_hit:
        return 0, []
    if len(matched_terms) >= 2:
        score += min(len(matched_terms), 6) * 8
        reasons.append(f"multi_terms:{len(matched_terms)}")
    if row.get("has_detail"):
        score += 8
    if row.get("window_status") == "current":
        score += 10
    return score, reasons


def build_seed_scenario_candidate(seed: dict, bugs: list[dict]) -> dict | None:
    ranked = []
    for row in bugs:
        score, reasons = scenario_seed_score(row, seed)
        if score >= 32:
            ranked.append((score, row, reasons))
    ranked.sort(key=ranked_bug_sort_key)
    if not ranked:
        return None

    examples = []
    bug_ids = []
    for score, row, reasons in ranked[:12]:
        bug_ids.append(str(row.get("id", "")))
        examples.append(
            {
                "id": str(row.get("id", "")),
                "title": row.get("title", ""),
                "module": row.get("module", ""),
                "category": row.get("category", ""),
                "created_at": row.get("created_at", ""),
                "window_status": row.get("window_status", ""),
                "score": score,
                "reasons": reasons[:8],
            }
        )

    max_score = ranked[0][0]
    if len(ranked) >= 2 or max_score >= 90:
        confidence = "high"
    elif max_score >= 55:
        confidence = "medium"
    else:
        confidence = "low"

    reasons = [
        f"matched_bug_count={len(ranked)}",
        f"top_score={max_score}",
        "seeded_from_known_testing_features",
    ]
    if any(row.get("has_detail") for _, row, _ in ranked[:5]):
        reasons.append("has_detail_evidence")
    return {
        "scenario": seed["scenario"],
        "source": "seed",
        "domain": seed.get("domain", ""),
        "module": seed.get("module", ""),
        "aliases": seed.get("aliases", []),
        "confidence": confidence,
        "confidence_reasons": reasons,
        "bug_count": len(ranked),
        "bug_ids": bug_ids,
        "issue_patterns": seed.get("issue_patterns", []),
        "must_check": seed.get("must_check", []),
        "examples": examples,
    }


def extract_bracket_candidates(bugs: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in bugs:
        text = f"{row.get('title', '')} {' '.join(row.get('keywords', []))}"
        for raw in re.findall(r"【([^】]{2,30})】", text):
            pieces = [raw.strip(), *[part.strip() for part in re.split(r"[-/｜|、，,;\s]+", raw)]]
            for name in pieces:
                if not name or len(name) < 2 or len(name) > 14:
                    continue
                if name.lower() in GENERIC_SCENARIO_CANDIDATES or name in GENERIC_SCENARIO_CANDIDATES:
                    continue
                grouped[name].append(row)

    candidates = []
    for name, rows in grouped.items():
        unique = {str(row.get("id", "")): row for row in rows if row.get("id")}
        if len(unique) < 2:
            continue
        ordered = sorted(unique.values(), key=detail_sort_key, reverse=True)
        confidence = "medium" if len(unique) >= 3 else "low"
        candidates.append(
            {
                "scenario": name,
                "source": "title_bracket",
                "domain": "",
                "module": "",
                "aliases": [name],
                "confidence": confidence,
                "confidence_reasons": [f"title_bracket_bug_count={len(unique)}"],
                "bug_count": len(unique),
                "bug_ids": [str(row.get("id", "")) for row in ordered[:12]],
                "issue_patterns": ["标题中多次出现同一功能入口，建议人工 review 后升级为正式场景"],
                "must_check": [],
                "examples": [
                    {
                        "id": str(row.get("id", "")),
                        "title": row.get("title", ""),
                        "module": row.get("module", ""),
                        "category": row.get("category", ""),
                        "created_at": row.get("created_at", ""),
                        "window_status": row.get("window_status", ""),
                        "score": 0,
                        "reasons": ["title_bracket"],
                    }
                    for row in ordered[:8]
                ],
            }
        )
    candidates.sort(key=lambda item: (item["confidence"] != "medium", -item["bug_count"], item["scenario"]))
    return candidates


def build_scenario_candidates(bugs: list[dict]) -> list[dict]:
    candidates = []
    seen = set()
    for seed in SCENARIO_SEEDS:
        candidate = build_seed_scenario_candidate(seed, bugs)
        if not candidate:
            continue
        candidates.append(candidate)
        seen.add(candidate["scenario"])
    for candidate in extract_bracket_candidates(bugs):
        if candidate["scenario"] in seen:
            continue
        candidates.append(candidate)
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda item: (confidence_order.get(item["confidence"], 9), -item["bug_count"], item["scenario"]))
    return candidates


def build_scenario_report(payload: dict) -> str:
    lines = [
        "# 紫鸟雷区场景候选报告",
        "",
        f"- 生成时间：{payload['generated_at']}",
        f"- 归一化 Bug 数：{payload['source']['total_bugs']}",
        f"- 候选场景数：{len(payload['candidates'])}",
        f"- 高置信正式索引数：{payload['source']['high_confidence_seed_scenarios']}",
        "",
    ]
    for confidence in ["high", "medium", "low"]:
        group = [item for item in payload["candidates"] if item.get("confidence") == confidence]
        if not group:
            continue
        lines.append(f"## {confidence}")
        for item in group:
            lines.append(f"- {item['scenario']}（{item['source']}，Bug {item['bug_count']} 条）")
            if item.get("issue_patterns"):
                lines.append(f"  - 易坏点：{'；'.join(item['issue_patterns'][:3])}")
            if item.get("must_check"):
                lines.append(f"  - 必测：{'；'.join(item['must_check'][:3])}")
            examples = item.get("examples", [])[:3]
            if examples:
                evidence = "；".join(f"{example['id']} {example['title']}" for example in examples)
                lines.append(f"  - 证据：{evidence}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_build_scenarios(args: argparse.Namespace) -> None:
    source_path = Path(args.source) if args.source else NORMALIZED_BUGS_FILE
    if not source_path.exists():
        raise SystemExit(f"{source_path} does not exist. Run normalize-bugs first.")
    bugs = load_jsonl(source_path)
    candidates = build_scenario_candidates(bugs)
    high_index = [item for item in candidates if item["source"] == "seed" and item["confidence"] == "high"]
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at": generated_at,
        "source": {
            "normalized_bugs": str(source_path),
            "total_bugs": len(bugs),
            "high_confidence_seed_scenarios": len(high_index),
        },
        "candidates": candidates,
    }
    SCENARIO_CANDIDATES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SCENARIO_CANDIDATES_REPORT_FILE.write_text(build_scenario_report(payload), encoding="utf-8")
    index_payload = {
        "version": 1,
        "generated_at": generated_at,
        "source": payload["source"],
        "scenarios": high_index,
    }
    SCENARIO_INDEX_FILE.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    by_confidence = Counter(item["confidence"] for item in candidates)
    print(f"Wrote {len(candidates)} scenario candidates to {SCENARIO_CANDIDATES_FILE}")
    print(f"Wrote review report to {SCENARIO_CANDIDATES_REPORT_FILE}")
    print(f"Wrote {len(high_index)} high-confidence scenarios to {SCENARIO_INDEX_FILE}")
    print(f"Confidence counts: {dict(by_confidence)}")


def load_scenario_index() -> list[dict]:
    if not SCENARIO_INDEX_FILE.exists():
        return []
    data = json.loads(SCENARIO_INDEX_FILE.read_text(encoding="utf-8"))
    return data.get("scenarios", [])


def scenario_haystack(item: dict) -> str:
    fields = [
        item.get("scenario", ""),
        item.get("domain", ""),
        item.get("module", ""),
        " ".join(item.get("aliases", [])),
        " ".join(item.get("issue_patterns", [])),
        " ".join(item.get("must_check", [])),
    ]
    for example in item.get("examples", []):
        fields.extend([example.get("id", ""), example.get("title", ""), example.get("module", ""), example.get("category", "")])
    return normalize_text(" ".join(str(value) for value in fields))


def score_scenario(item: dict, query: str) -> tuple[int, list[str]]:
    query_norm = normalize_text(query)
    terms = query_terms(query_norm)
    haystack = scenario_haystack(item)
    haystack_tokens = tokens(haystack)
    score = 0
    reasons: list[str] = []
    scenario_name = normalize_text(item.get("scenario", ""))
    anchor_terms = {
        normalize_text(term)
        for term in [item.get("scenario", ""), *item.get("aliases", [])]
        if normalize_text(term) and normalize_text(term) not in GENERIC_SCENARIO_TERMS
    }
    strong_match = False
    anchor_match = False
    if scenario_name and scenario_name in query_norm:
        score += 180
        reasons.append(f"scenario:{item.get('scenario')}")
        strong_match = True
        anchor_match = True
    for alias in item.get("aliases", []):
        alias_norm = normalize_text(alias)
        if not alias_norm or alias_norm == scenario_name or alias_norm in GENERIC_SCENARIO_TERMS:
            continue
        if alias_norm in query_norm:
            score += 120
            reasons.append(f"query_alias:{alias}")
            strong_match = True
            if alias_norm in anchor_terms:
                anchor_match = True
                score += 40
                reasons.append(f"specific_alias:{alias}")
        elif alias_norm in haystack and any(part in query_norm for part in tokens(alias_norm) if part not in GENERIC_SCENARIO_TERMS):
            score += 45
            reasons.append(f"related_alias:{alias}")
            if alias_norm in anchor_terms:
                anchor_match = True
    matched_terms = set()
    for term in terms:
        if term in haystack_tokens:
            score += 22
            matched_terms.add(term)
            reasons.append(f"token:{term}")
            if term in anchor_terms:
                anchor_match = True
        elif term in haystack:
            score += 9
            matched_terms.add(term)
            reasons.append(f"substring:{term}")
            if term in anchor_terms:
                anchor_match = True
    if len(matched_terms) >= 2:
        score += min(len(matched_terms), 6) * 14
        reasons.append(f"multi_terms:{len(matched_terms)}")
    if item.get("confidence") == "high":
        score += 25
    if item.get("bug_count", 0) >= 2:
        score += 15
    if score > 0 and not matched_terms and not any(reason.startswith(("scenario:", "query_alias:")) for reason in reasons):
        return 0, []
    if not strong_match and not anchor_match:
        return 0, []
    return score, reasons


def rank_scenarios(
    query: str,
    limit: int | None = None,
    min_score: int = 45,
    scenario_items: list[dict] | None = None,
) -> list[tuple[int, dict, list[str]]]:
    ranked = []
    for item in scenario_items if scenario_items is not None else load_scenario_index():
        score, reasons = score_scenario(item, query)
        if score >= min_score:
            ranked.append((score, item, reasons))
    ranked.sort(key=lambda pair: (-pair[0], -pair[1].get("bug_count", 0), pair[1].get("scenario", "")))
    if limit is not None:
        return ranked[:limit]
    return ranked


def print_scenario_hits(
    query: str,
    limit: int,
    explain: bool = False,
    scenario_items: list[dict] | None = None,
) -> None:
    ranked = rank_scenarios(query, limit=limit, scenario_items=scenario_items)
    if not ranked:
        return
    print("Scenario index hits:")
    for score, item, reasons in ranked:
        print(f"[{score}] {item.get('scenario')} | {item.get('domain')} / {item.get('module')} | confidence={item.get('confidence')} | bugs={item.get('bug_count')}")
        if item.get("issue_patterns"):
            print(f"  Risk patterns: {'; '.join(item.get('issue_patterns', [])[:3])}")
        if item.get("must_check"):
            print("  Must check:")
            for check in item.get("must_check", [])[:4]:
                print(f"    - {check}")
        examples = item.get("examples", [])[:3]
        if examples:
            print(f"  Evidence: {'; '.join(example.get('id', '') + ' ' + example.get('title', '') for example in examples)}")
        if explain:
            print(f"  Reasons: {', '.join(reasons[:10])}")
    print()


def cmd_scenario_search(args: argparse.Namespace) -> None:
    if not SCENARIO_INDEX_FILE.exists():
        raise SystemExit(f"{SCENARIO_INDEX_FILE} does not exist. Run build-scenarios first.")
    ranked = rank_scenarios(args.query, limit=args.limit, min_score=args.min_score)
    if not ranked:
        print(f"No scenario index match for: {args.query}")
        return
    print_scenario_hits(args.query, args.limit, args.explain)


def score_bug_detail(row: dict, query: str, context: dict | None = None) -> tuple[int, list[str]]:
    query_norm = normalize_text(query)
    direct_terms = literal_query_terms(query_norm)
    if context is None:
        context = detect_query_context(query, load_alias_config())
    expanded_terms = set(context["expanded_terms"]) - direct_terms
    haystack_fields = [
        row.get("title", ""),
        row.get("module", ""),
        row.get("category", ""),
        " ".join(row.get("keywords", [])),
        " ".join(row.get("trigger_conditions", [])),
        " ".join(row.get("failure_symptoms", [])),
        " ".join(row.get("expected_result", [])),
        " ".join(row.get("fix_clues", [])),
    ]
    haystack = normalize_text(" ".join(str(value) for value in haystack_fields))
    primary_haystack = normalize_text(" ".join(str(value) for value in [row.get("title", ""), row.get("module", "")]))
    haystack_tokens = tokens(haystack)
    score = 0
    reasons: list[str] = []
    matched_direct_terms: set[str] = set()
    matched_expanded_terms: set[str] = set()
    matched_feature = False
    direct_feature_evidence: set[str] = set()
    scored_query_aliases: set[str] = set()
    feature_expansion_score = 0
    for feature_match in context["features"]:
        feature = normalize_text(feature_match["feature"])
        direct_feature_match = bool(feature_match.get("direct_name_match"))
        if direct_feature_match and feature and feature in haystack:
            score += 120
            reasons.append(f"feature:{feature_match['feature']}")
            matched_feature = True
            direct_feature_evidence.add(feature)

        # Only aliases literally present in the query are strong evidence. Other
        # aliases from the same feature broaden recall, but must not dominate a
        # direct title match (for example, 附加账号 outranking 授权成员).
        for alias in feature_match["aliases"]:
            alias_norm = normalize_text(alias)
            if any(alias_norm != term and alias_norm in term for term in direct_terms):
                continue
            if alias_norm and alias_norm in haystack and alias_norm not in scored_query_aliases:
                score += 80
                reasons.append(f"alias:{alias}")
                matched_feature = True
                scored_query_aliases.add(alias_norm)
                if direct_feature_match:
                    direct_feature_evidence.add(feature)

        if direct_feature_match or feature_match["aliases"]:
            related_aliases = {
                normalize_text(alias)
                for alias in feature_match["spec"].get("aliases", [])
                if normalize_text(alias) and normalize_text(alias) not in scored_query_aliases
            }
            related_matches = {alias for alias in related_aliases if alias in haystack}
            if related_matches:
                increment = min(60, len(related_matches) * 15)
                feature_expansion_score += increment
                reasons.append(f"feature_related:{feature_match['feature']}:{len(related_matches)}")
                matched_feature = True
                direct_feature_evidence.add(feature)

    score += min(feature_expansion_score, 60)
    if direct_feature_evidence:
        score += 35
        reasons.append(f"direct_feature_evidence:{len(direct_feature_evidence)}")

    for term in direct_terms:
        if term in haystack_tokens:
            score += 38
            reasons.append(f"direct_token:{term}")
            matched_direct_terms.add(term)
        elif term in haystack:
            score += 18
            reasons.append(f"direct_substring:{term}")
            matched_direct_terms.add(term)
        if term in primary_haystack:
            score += 28
            reasons.append(f"primary:{term}")

    # Expanded terms are recall hints only. Cap their total contribution so a
    # row matching many broad siblings cannot outrank direct query evidence.
    for term in expanded_terms:
        if term in haystack_tokens:
            matched_expanded_terms.add(term)
        elif term in haystack:
            matched_expanded_terms.add(term)
    if matched_expanded_terms:
        score += min(30, len(matched_expanded_terms) * 5)
        reasons.append(f"expanded_terms:{len(matched_expanded_terms)}")

    if len(matched_direct_terms) >= 2:
        score += min(72, len(matched_direct_terms) * 18)
        reasons.append(f"multi_direct:{len(matched_direct_terms)}")
    weak_terms = {normalize_text(term) for term in context.get("weak_terms", set())}
    anchor_terms = {term for term in direct_terms if term in QUERY_ANCHOR_TERMS and term not in weak_terms}
    covered_anchors = {term for term in anchor_terms if term in haystack}
    for feature in direct_feature_evidence:
        compact_feature = re.sub(r"\s+", "", feature)
        covered_anchors.update(term for term in anchor_terms if re.sub(r"\s+", "", term) in compact_feature)
    missing_anchor_count = len(anchor_terms - covered_anchors)
    if missing_anchor_count:
        penalty = 45 if not covered_anchors else missing_anchor_count * 25
        score = max(0, score - penalty)
        reasons.append(f"missing_query_anchors:{missing_anchor_count}")
    if not matched_feature and not matched_direct_terms and not matched_expanded_terms:
        return 0, []
    if row.get("has_detail"):
        score += 10
    if score > 0:
        recency_adjustment, recency_reason = bug_recency_adjustment(row)
        score = max(0, score + recency_adjustment)
        reasons.append(recency_reason)
    return score, reasons


def cmd_bug_search(args: argparse.Namespace) -> None:
    scenario_evidence_ids: set[str] = set()
    scenario_items = getattr(args, "_scenario_items", None)
    if not args.no_scenarios and (scenario_items is not None or SCENARIO_INDEX_FILE.exists()):
        print_scenario_hits(args.query, min(3, args.limit), args.explain, scenario_items=scenario_items)
        for _, scenario, _ in rank_scenarios(args.query, limit=3, scenario_items=scenario_items):
            scenario_evidence_ids.update(str(bug_id) for bug_id in scenario.get("bug_ids", []))
    ranked = []
    bug_rows = getattr(args, "_bug_rows", None)
    if bug_rows is None:
        if not NORMALIZED_BUGS_FILE.exists():
            print(
                "Bug detail cache unavailable; run "
                "scripts/refresh_openviking_bug_cache.ps1 before relying on "
                "historical Bug detail recall."
            )
            return
        bug_rows = load_jsonl(NORMALIZED_BUGS_FILE)
    context = detect_query_context(args.query, getattr(args, "_alias_config", None) or load_alias_config())
    for row in bug_rows:
        score, reasons = score_bug_detail(row, args.query, context=context)
        if score >= args.min_score or str(row.get("id", "")) in scenario_evidence_ids:
            if score < args.min_score:
                score = args.min_score
                reasons = ["scenario_evidence"]
            ranked.append((score, row, reasons))
    ranked.sort(key=ranked_bug_sort_key)
    has_strong_detail = any(
        score >= 100 and any(reason.startswith(("feature:", "alias:")) for reason in reasons)
        for score, _, reasons in ranked
    )
    if has_strong_detail:
        ranked = [
            (score, row, reasons)
            for score, row, reasons in ranked
            if score >= 100 or str(row.get("id", "")) in scenario_evidence_ids or any(reason.startswith(("feature:", "alias:")) for reason in reasons)
        ]
    if not ranked:
        print(f"No bug detail match for: {args.query}")
        return
    print("Bug detail hits:")
    for score, row, reasons in ranked[: args.limit]:
        print(f"[{score}] {row.get('id')} | {row.get('module')} | {row.get('category')}")
        print(f"  Title: {row.get('title')}")
        if args.explain:
            print(f"  Reasons: {', '.join(reasons[:12])}")
        if row.get("trigger_conditions"):
            print("  Trigger:")
            for line in row["trigger_conditions"][:3]:
                print(f"    - {line}")
        if row.get("failure_symptoms"):
            print("  Failure:")
            for line in row["failure_symptoms"][:3]:
                print(f"    - {line}")
        if row.get("fix_clues"):
            print("  Fix clues:")
            for line in row["fix_clues"][:2]:
                print(f"    - {line}")
        print()


def cmd_radar_search(args: argparse.Namespace) -> None:
    queries = []
    seen = set()
    for query in [args.query, *args.related]:
        normalized = normalize_text(query)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        queries.append(query)

    shared = {
        "_scenario_items": load_scenario_index(),
        "_alias_config": load_alias_config(),
    }
    if NORMALIZED_BUGS_FILE.exists():
        shared["_bug_rows"] = load_jsonl(NORMALIZED_BUGS_FILE)

    recall_args = argparse.Namespace(
        query=args.query,
        limit=args.recall_limit,
        group_limit=args.group_limit,
        check_limit=args.check_limit,
        evidence_limit=args.evidence_limit,
        explain=args.explain,
    )
    cmd_recall(recall_args)

    for index, query in enumerate(queries, 1):
        print(f"=== Bug query {index}/{len(queries)}: {query} ===")
        bug_args = argparse.Namespace(
            query=query,
            limit=args.bug_limit,
            min_score=args.min_score,
            explain=args.explain,
            no_scenarios=args.no_scenarios,
            **shared,
        )
        cmd_bug_search(bug_args)


def infer_domain(category: str, module: str, title: str) -> str:
    text = f"{category} {module} {title}"
    if any(key in text for key in ["V5客户端", "V6客户端", "客户端", "内核", "开发者模式", "资源包"]):
        return "客户端"
    if any(key in text for key in ["安卓", "IOS", "移动端"]):
        return "移动端"
    if "官网" in text:
        return "官网"
    if "运维后台" in text:
        return "运维后台"
    if "店铺" in text:
        return "店铺内"
    return "管理系统"


RULES = [
    ("账号权限与授权", ["账号", "附加账号", "主账号", "授权", "角色", "权限", "登录凭证"]),
    ("列表筛选搜索导出", ["列表", "筛选", "搜索", "导出", "排序", "时间范围", "分页", "刷新"]),
    ("访问策略与安全策略", ["访问策略", "会员安全策略", "生效成员", "页面拦截", "元素拦截"]),
    ("安全监管与告警", ["事中监管", "安全监管", "告警", "审批", "监管日志", "预警"]),
    ("客户端资源包与升级", ["资源包", "热更", "升级", "old_version", "new_version", "跳转服务"]),
    ("内核与开发者模式", ["内核", "开发者模式", "F12", "UI调试", "无头", "火狐"]),
    ("移动端状态切换", ["移动端", "安卓", "ios", "IOS", "切换公司", "监管模式"]),
    ("远程服务模式", ["服务模式", "向日葵", "远程", "被控", "主控", "外部依赖"]),
    ("文案与翻译", ["文案", "短信", "模板", "翻译", "key", "英文", "提示"]),
    ("数据一致性与缓存", ["不一致", "旧数据", "缓存", "未刷新", "不同步", "重复", "丢失"]),
]


def cluster_name_for(item: dict) -> str:
    text = " ".join(str(item.get(key) or "") for key in ["title", "category", "module", "defect_type"])
    for cluster, keywords in RULES:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return cluster
    return "其他高频线上缺陷"


CHECK_LIBRARY = {
    "账号权限与授权": ["权限入口可见性和可操作性一致", "授权成员筛选与实际授权关系一致", "主账号/附加账号平台与登录凭证重复校验正确", "无权限角色不能绕过入口操作", "操作日志和详情数据正确"],
    "列表筛选搜索导出": ["筛选条件组合后列表数据正确", "导出范围和列表一致", "特殊字符、空值、异常输入搜索不报错", "时间范围结束日覆盖完整", "刷新、分页、切换筛选后数据不丢失"],
    "访问策略与安全策略": ["成员/部门/角色生效范围正确", "启用/禁用/编辑后配置端状态刷新正确", "新开店铺、刷新店铺、已打开店铺分别验证执行效果", "无权限成员不能绕过策略配置或执行", "策略日志和实际拦截结果一致"],
    "安全监管与告警": ["监管模式切换后列表和状态刷新正确", "预警/非预警筛选组合正确", "过期审批事件不可继续操作", "关键动作能触发告警", "监管日志统计与实际状态一致"],
    "客户端资源包与升级": ["资源包热更前后版本号和入口正确", "资源包未更新时有兜底", "升级、中断、旧缓存场景可恢复", "埋点版本上报正确", "多开工作台资源版本一致"],
    "内核与开发者模式": ["不同内核权限表现一致", "F12/开发者工具入口不能绕过权限", "UI调试和普通入口配置一致", "切换内核后配置仍生效", "无头模式补测"],
    "移动端状态切换": ["切换公司后账号、权限和列表刷新正确", "安卓/iOS同路径分别验证", "后台切前台后状态正确", "切换监管模式后旧数据不残留", "登录方式限制提示准确"],
    "远程服务模式": ["主控/被控连接链路正常", "对话和消息可达", "外部远程依赖登录后不异常断开", "断开重连后状态恢复", "Windows和多屏场景覆盖"],
    "文案与翻译": ["新增文案中英文和其他语言齐全", "短信/通知模板符合场景", "不显示key或中文兜底", "长文本布局不溢出", "提示语与实际权限一致"],
    "数据一致性与缓存": ["操作后列表、详情、日志一致", "刷新/重进/重新登录后状态一致", "重复数据有拦截或去重", "缓存不会展示已失效数据", "跨账号/跨环境不串数据"],
    "其他高频线上缺陷": ["按标题复现关键路径", "验证状态刷新和异常提示", "覆盖权限、边界、刷新、重进", "保留当前需求差异待确认"],
}

RISK_LIBRARY = {
    "账号权限与授权": "账号、角色、授权和登录凭证链路缺陷数量最高，容易出现权限入口可见、授权关系不准、重复校验错误或操作日志不一致。",
    "列表筛选搜索导出": "列表型页面容易在筛选、搜索、导出、时间范围和刷新分页后出现展示数据与真实条件不一致。",
    "访问策略与安全策略": "访问策略和会员安全策略跨管理端配置、成员/部门/角色范围和店铺内执行效果，容易出现配置已改但执行未生效或已打开店铺状态不确定。",
    "安全监管与告警": "事中监管、访问审批、告警和监管日志受状态切换、过期事件、筛选组合影响大，容易漏测状态刷新和触发链路。",
    "客户端资源包与升级": "客户端资源包、热更、升级弹窗、埋点版本和旧缓存组合容易造成升级失败、页面加载异常或版本上报错误。",
    "内核与开发者模式": "内核能力、开发者模式权限和调试入口容易在不同内核或权限组合下表现不一致。",
    "移动端状态切换": "移动端公司切换、登录方式切换、监管模式切换后容易出现旧数据残留、状态不刷新或平台兼容问题。",
    "远程服务模式": "远程服务模式依赖主控端、被控端和外部远程链路，容易出现连接、对话、消息和异常断开问题。",
    "文案与翻译": "短信模板、提示文案、权限文案和新增前端文案容易与真实场景不一致，也容易遗漏多语言和长文案布局。",
    "数据一致性与缓存": "跨列表、详情、日志、缓存、Redis或来源字段的数据容易不同步，刷新或重新进入后才暴露。",
    "其他高频线上缺陷": "该组缺陷主题分散，但仍需按标题覆盖核心路径，并补充权限、边界、刷新、重进和异常提示检查。",
}


def cmd_cluster_feishu(args: argparse.Namespace) -> None:
    source_path = Path(args.source) if args.source else RAW_DIR / f"view_{FEISHU_VIEW_ID}_normalized.json"
    if source_path.suffix.lower() == ".jsonl":
        all_items = load_jsonl(source_path)
        items = [item for item in all_items if "current_182d" in item.get("view_memberships", [])]
        source_metadata = {
            "type": "normalized_bug_archive",
            "path": str(source_path),
            "membership_filter": "current_182d",
        }
    else:
        data = json.loads(source_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        source_metadata = data.get("source", {})

    clusters: dict[str, dict] = {}
    for item in items:
        cluster = cluster_name_for(item)
        bucket = clusters.setdefault(
            cluster,
            {
                "cluster": cluster,
                "count": 0,
                "domains": Counter(),
                "categories": Counter(),
                "modules": Counter(),
                "statuses": Counter(),
                "severities": Counter(),
                "examples": [],
                "must_check": CHECK_LIBRARY.get(cluster, CHECK_LIBRARY["其他高频线上缺陷"]),
            },
        )
        bucket["count"] += 1
        bucket["domains"][infer_domain(item.get("category", ""), item.get("module", ""), item.get("title", ""))] += 1
        bucket["categories"][item.get("category") or "未填"] += 1
        bucket["modules"][item.get("module") or "未填"] += 1
        bucket["statuses"][item.get("status") or "未填"] += 1
        bucket["severities"][item.get("severity") or "未填"] += 1
        if len(bucket["examples"]) < 8:
            bucket["examples"].append({"id": item.get("id"), "title": item.get("title"), "category": item.get("category"), "module": item.get("module"), "created_at": item.get("created_at")})

    serializable = []
    for bucket in sorted(clusters.values(), key=lambda x: (-x["count"], x["cluster"])):
        serializable.append(
            {
                "cluster": bucket["cluster"],
                "count": bucket["count"],
                "domains": dict(bucket["domains"].most_common()),
                "categories": dict(bucket["categories"].most_common(10)),
                "modules": dict(bucket["modules"].most_common(10)),
                "statuses": dict(bucket["statuses"].most_common()),
                "severities": dict(bucket["severities"].most_common()),
                "must_check": bucket["must_check"],
                "examples": bucket["examples"],
            }
        )

    result = {
        "source": source_metadata,
        "total_items": len(items),
        "cluster_count": len(serializable),
        "clusters": serializable,
    }
    CLUSTERS_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_FILE.write_text(render_cluster_report(result), encoding="utf-8")
    print(f"Wrote clusters to {CLUSTERS_FILE}")
    print(f"Wrote report to {REPORT_FILE}")


def safe_id(text: str) -> str:
    mapping = {
        "账号权限与授权": "ACCOUNT-AUTH",
        "列表筛选搜索导出": "LIST-FILTER-EXPORT",
        "安全监管与告警": "SECURITY-SUPERVISION",
        "客户端资源包与升级": "CLIENT-RESOURCE-UPGRADE",
        "内核与开发者模式": "KERNEL-DEVTOOLS",
        "移动端状态切换": "MOBILE-STATE-SWITCH",
        "远程服务模式": "REMOTE-SERVICE",
        "文案与翻译": "COPY-I18N",
        "数据一致性与缓存": "DATA-CACHE-CONSISTENCY",
        "其他高频线上缺陷": "OTHER-HIGH-FREQ",
    }
    return mapping.get(text, re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-") or "CLUSTER")


def cmd_sync_clusters(args: argparse.Namespace) -> None:
    data = json.loads(CLUSTERS_FILE.read_text(encoding="utf-8"))
    records = []
    today = datetime.now().date().isoformat()
    for cluster in data.get("clusters", []):
        modules = list(cluster.get("modules", {}).keys())
        categories = list(cluster.get("categories", {}).keys())
        domains = list(cluster.get("domains", {}).keys())
        examples = cluster.get("examples", [])
        name = cluster.get("cluster", "未知聚类")
        record = {
            "id": f"ZN-FEISHU-CLUSTER-{safe_id(name)}",
            "source": "feishu_cluster",
            "domain": "/".join(domains[:3]) or "紫鸟",
            "module": "/".join(modules[:5]) or "未填",
            "category": "/".join(categories[:3]) or "线上缺陷",
            "scene": name,
            "risk": RISK_LIBRARY.get(name, RISK_LIBRARY["其他高频线上缺陷"]),
            "must_check": cluster.get("must_check", []),
            "keywords": [name, *modules[:8], *categories[:5]],
            "evidence": [f"{example.get('id')}: {example.get('title')}" for example in examples[:8]],
            "confidence": "confirmed" if cluster.get("count", 0) >= 3 else "inferred",
            "last_seen": today,
            "source_count": cluster.get("count", 0),
        }
        records.append(record)

    GENERATED_LANDMINES_FILE.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} generated landmines to {GENERATED_LANDMINES_FILE}")


def render_cluster_report(result: dict) -> str:
    lines = [
        "# 紫鸟线上缺陷雷区聚类",
        "",
        f"- 数据源视图：{result.get('source', {}).get('view_url', '')}",
        f"- 导入数量：{result.get('total_items', 0)}",
        f"- 聚类数量：{result.get('cluster_count', 0)}",
        "",
        "## 聚类结果",
        "",
    ]
    for cluster in result.get("clusters", []):
        lines.append(f"### {cluster['cluster']}（{cluster['count']} 条）")
        lines.append("")
        lines.append(f"- 主要域：{format_counter(cluster.get('domains', {}))}")
        lines.append(f"- 主要模块：{format_counter(cluster.get('modules', {}))}")
        lines.append(f"- 缺陷分类：{format_counter(cluster.get('categories', {}))}")
        lines.append("- 必测点：")
        for check in cluster.get("must_check", []):
            lines.append(f"  - {check}")
        lines.append("- 样例：")
        for example in cluster.get("examples", [])[:5]:
            lines.append(f"  - {example.get('id')}: {example.get('title')}")
        lines.append("")
    return "\n".join(lines)


def format_counter(counter: dict) -> str:
    return "，".join(f"{key} {value}" for key, value in counter.items()) or "无"


def tokens(text: str) -> set[str]:
    text = text.lower()
    chunks = re.findall(r"[\w\u4e00-\u9fff]+", text)
    return {chunk for chunk in chunks if chunk}


KNOWN_QUERY_TERMS = [
    "云号",
    "云号码",
    "紫鸟云号",
    "购买",
    "订单",
    "支付",
    "套餐",
    "权益",
    "开通",
    "续费",
    "编辑账号",
    "账号锁定",
    "账号保护",
    "账号",
    "编辑",
    "账号列表",
    "授权成员",
    "登录凭证",
    "书签",
    "收藏",
    "资源包",
    "升级",
    "内核",
    "无头模式",
    "事中监管",
    "筛选",
    "导出",
    "首页",
    "账号动态",
    "账户余额",
    "余额明细",
    "复制账号",
    "共享账号",
    "设备回收站",
    "自定义视图",
    "黑名单",
    "黑名单管理",
    "添加成员",
    "创建成员",
    "部门管理",
    "添加监管账号",
    "监管对象",
    "成员监管",
    "生效账号",
    "指定账号",
    "急需续费",
    "续费列表",
    "即将到期",
    "即将过期",
    "缓存管理",
    "文件下载设置",
    "路径冲突",
    "店铺文件下载路径",
    "账号临时缓存",
    "紫鸟客户端缓存",
    "内核下载文件",
    "内核解压文件",
]

QUERY_COMPANION_TERMS = {
    "购买": ["订单", "支付", "套餐", "开通", "续费"],
    "急需续费": ["续费", "即将到期", "即将过期", "到期提醒"],
    "路径冲突": ["缓存管理", "文件下载设置", "误删除", "安装目录"],
}

QUERY_ANCHOR_TERMS = {
    "云号",
    "紫鸟云号",
    "账号",
    "账号列表",
    "编辑账号",
    "账号锁定",
    "账号保护",
    "书签",
    "收藏",
    "资源包",
    "内核",
    "事中监管",
    "账号动态",
    "账户余额",
    "复制账号",
    "共享账号",
    "设备回收站",
    "自定义视图",
    "黑名单",
    "黑名单管理",
    "添加成员",
    "创建成员",
    "部门管理",
    "添加监管账号",
    "监管对象",
    "成员监管",
    "急需续费",
    "续费列表",
    "即将到期",
    "即将过期",
    "缓存管理",
    "文件下载设置",
    "路径冲突",
}


def query_terms(text: str) -> set[str]:
    result = literal_query_terms(text)
    for term in list(result):
        result.update(QUERY_COMPANION_TERMS.get(term, []))
    return result


def literal_query_terms(text: str) -> set[str]:
    norm = normalize_text(text)
    stripped = re.sub(r"(我要|需要|开始|准备|测试|测|相关|功能|页面|模块|的)", " ", norm)
    result = set(tokens(stripped))
    known_matches = set()
    for term in KNOWN_QUERY_TERMS:
        term_norm = normalize_text(term)
        if term_norm in norm:
            known_matches.add(term_norm)
    # Chinese requirement phrases are often written without spaces. Preserve
    # the most specific known terms inside a longer chunk (for example keep
    # "账号锁定" inside "店铺账号锁定申请审批"); otherwise same-feature Bugs can
    # receive score 0 while broader alias matches dominate the result.
    specific_known_matches = {
        term
        for term in known_matches
        if not any(term != other and term in other for other in known_matches)
    }
    result.update(specific_known_matches)
    result = {term for term in result if term}
    return {
        term
        for term in result
        if term in specific_known_matches
        or not any(term != other and term in other for other in result)
    }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def evidence_key(item: dict) -> str:
    return item.get("evidence_level") or item.get("source") or "unknown"


def detect_query_context(query: str, alias_config: dict) -> dict:
    query_norm = normalize_text(query)
    compact_query = re.sub(r"\s+", "", query_norm)
    features = alias_config.get("features", {})
    global_weak_terms = set(alias_config.get("global_weak_terms", []))
    matches = []
    expanded_terms = set(query_terms(query))
    preferred_ids: set[str] = set()
    weak_terms = set(global_weak_terms)

    for feature, spec in features.items():
        aliases = [feature, *spec.get("aliases", [])]
        matched_aliases = [alias for alias in aliases if normalize_text(alias) and normalize_text(alias) in query_norm]
        if not matched_aliases:
            continue
        feature_norm = normalize_text(feature)
        matches.append(
            {
                "feature": feature,
                "aliases": matched_aliases,
                "spec": spec,
                "direct_name_match": bool(feature_norm and re.sub(r"\s+", "", feature_norm) in compact_query),
            }
        )
        expanded_terms.update(tokens(" ".join(aliases)))
        preferred_ids.update(spec.get("prefer_ids", []))
        weak_terms.update(spec.get("weak_terms", []))

    return {
        "query": query,
        "query_norm": query_norm,
        "features": matches,
        "expanded_terms": expanded_terms,
        "preferred_ids": preferred_ids,
        "weak_terms": weak_terms,
    }


def item_haystack(item: dict, include_evidence: bool = True) -> str:
    fields = [
        item.get("id", ""),
        item.get("domain", ""),
        item.get("module", ""),
        item.get("category", ""),
        item.get("scene", ""),
        item.get("risk", ""),
        " ".join(item.get("keywords", [])),
        " ".join(item.get("related_modules", [])),
    ]
    if include_evidence:
        fields.append(" ".join(str(value) for value in item.get("evidence", [])))
    return normalize_text(" ".join(str(value) for value in fields))


def item_evidence_text(item: dict) -> str:
    return normalize_text(" ".join(str(value) for value in item.get("evidence", [])))


def score_item(item: dict, context: dict, rules: dict) -> tuple[int, list[str]]:
    q = context["expanded_terms"]
    if not q:
        return 0, []

    weights = rules.get("match_weights", DEFAULT_RECALL_RULES["match_weights"])
    priorities = rules.get("evidence_priority", DEFAULT_RECALL_RULES["evidence_priority"])
    haystack = item_haystack(item, include_evidence=False)
    evidence_text = item_evidence_text(item)
    item_tokens = tokens(haystack)
    evidence_tokens = tokens(evidence_text)

    score = 0
    reasons: list[str] = []
    item_id = item.get("id")
    strong_context_match = False
    if item_id in context["preferred_ids"]:
        score += weights.get("preferred_id", 500)
        reasons.append("preferred_id")
        strong_context_match = True

    for feature_match in context["features"]:
        feature = feature_match["feature"]
        aliases = list(dict.fromkeys([*feature_match["aliases"], *feature_match["spec"].get("aliases", [])]))
        if normalize_text(feature) in haystack:
            score += weights.get("canonical_feature", 120)
            reasons.append(f"feature:{feature}")
            strong_context_match = True
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if alias_norm and alias_norm in haystack:
                score += weights.get("alias_phrase", 90)
                reasons.append(f"alias:{alias}")
                strong_context_match = True

    for term in q:
        if term in context["weak_terms"] and (term in item_tokens or term in haystack or term in evidence_text):
            score += weights.get("weak_term_penalty", -20)
            reasons.append(f"weak:{term}")
            continue
        if term in item_tokens:
            score += weights.get("exact_token", 18)
            reasons.append(f"token:{term}")
        elif term in haystack:
            score += weights.get("substring", 6)
            reasons.append(f"substring:{term}")
        elif term in evidence_tokens:
            score += weights.get("evidence_exact_token", 8)
            reasons.append(f"evidence_token:{term}")
        elif term in evidence_text:
            score += weights.get("evidence_substring", 3)
            reasons.append(f"evidence_substring:{term}")

    if score <= 0 or not reasons:
        return 0, []

    if item.get("source") in {"derived_cluster", "feishu_cluster"} and context["features"] and not strong_context_match:
        return 0, []

    confidence = item.get("confidence")
    if confidence == "confirmed":
        score += weights.get("confirmed_bonus", 25)
    elif confidence == "seed":
        score += weights.get("seed_bonus", 8)

    score += priorities.get(evidence_key(item), priorities.get(item.get("source", ""), 0))

    return score, reasons


def rank_landmines(query: str, limit: int | None = None) -> list[tuple[int, dict, list[str]]]:
    alias_config = load_alias_config()
    rules = load_recall_rules()
    context = detect_query_context(query, alias_config)
    minimum_score = rules.get("minimum_score", DEFAULT_RECALL_RULES["minimum_score"])
    ranked = []
    for item in load_landmines():
        score, reasons = score_item(item, context, rules)
        if score >= minimum_score:
            ranked.append((score, item, reasons))
    generic_ids = set(rules.get("generic_cluster_ids", []))
    suppress_threshold = rules.get("suppress_generic_cluster_when_specific_score", 250)
    has_specific_hit = any(
        item.get("id") not in generic_ids and score >= suppress_threshold
        for score, item, _ in ranked
    )
    if generic_ids and has_specific_hit:
        ranked = [
            (score, item, reasons)
            for score, item, reasons in ranked
            if item.get("id") not in generic_ids
        ]
    ranked.sort(key=lambda pair: (-pair[0], -evidence_rank(pair[1], rules), pair[1].get("id", "")))
    if limit is not None:
        return ranked[:limit]
    return ranked


def evidence_rank(item: dict, rules: dict) -> int:
    priorities = rules.get("evidence_priority", DEFAULT_RECALL_RULES["evidence_priority"])
    return priorities.get(evidence_key(item), priorities.get(item.get("source", ""), 0))


def cmd_search(args: argparse.Namespace) -> None:
    ranked = rank_landmines(args.query, args.limit)

    if not ranked:
        print(f"No landmine match for: {args.query}")
        return

    for score, item, reasons in ranked:
        print(f"[{score}] {item.get('id')} | {item.get('category')} | {item.get('module')}")
        print(f"  Source: {item.get('source', 'unknown')} | Evidence level: {item.get('evidence_level', item.get('source', 'unknown'))}")
        if args.explain:
            print(f"  Reasons: {', '.join(reasons[:12])}")
        print(f"  Scene: {item.get('scene')}")
        print(f"  Risk: {item.get('risk')}")
        checks = item.get("must_check", [])
        if checks:
            print("  Must check:")
            for check in checks[:6]:
                print(f"    - {check}")
        evidence = item.get("evidence", [])
        if evidence:
            print(f"  Evidence: {'; '.join(str(x) for x in evidence[:3])}")
        print()


def evidence_group(item: dict) -> str:
    source = item.get("source")
    level = evidence_key(item)
    if level == "direct_bug" or source in {"feishu_online_bug", "tester_note"}:
        return "direct"
    if source in {"derived_cluster", "feishu_cluster"}:
        return "cluster"
    return "supplemental"


GROUP_LABELS = {
    "direct": "历史线上 Bug 直接命中",
    "cluster": "同类雷区推导",
    "supplemental": "建议补充检查",
}


def cmd_recall(args: argparse.Namespace) -> None:
    ranked = rank_landmines(args.query, args.limit)
    if not ranked:
        print(f"No landmine match for: {args.query}")
        return

    groups: dict[str, list[tuple[int, dict, list[str]]]] = {"direct": [], "cluster": [], "supplemental": []}
    for row in ranked:
        groups[evidence_group(row[1])].append(row)

    print(f"测前雷区召回：{args.query}")
    print()
    for group_key in ["direct", "cluster", "supplemental"]:
        rows = groups[group_key]
        if not rows:
            continue
        print(f"## {GROUP_LABELS[group_key]}")
        for score, item, reasons in rows[: args.group_limit]:
            print(f"- {item.get('id')}（score={score}）：{item.get('scene')}")
            print(f"  风险：{item.get('risk')}")
            checks = item.get("must_check", [])[: args.check_limit]
            if checks:
                print("  必测：")
                for check in checks:
                    print(f"  - {check}")
            evidence = item.get("evidence", [])[: args.evidence_limit]
            if evidence:
                print("  证据：")
                for entry in evidence:
                    print(f"  - {entry}")
            if args.explain:
                print(f"  来源：{item.get('source')} / {evidence_key(item)}")
                print(f"  命中原因：{', '.join(reasons[:10])}")
        print()


RADAR_CHANGE_PROFILES = {
    "ui_copy",
    "list_query",
    "permission_authorization",
    "lifecycle",
    "client_runtime",
    "shared_component",
    "migration_compatibility",
    "security_sensitive",
}

RADAR_DIMENSIONS = {
    "data_persistence",
    "display_consistency",
    "query_semantics",
    "permission_scope",
    "state_transition",
    "runtime_chain",
    "isolation_concurrency",
    "resource_release_recovery",
    "shared_consumers",
    "downstream_records",
    "compatibility",
    "security_privacy",
    "i18n_copy",
}

RADAR_PROFILE_CORE_DIMENSIONS = {
    "ui_copy": {"display_consistency", "i18n_copy"},
    "list_query": {"display_consistency", "query_semantics"},
    "permission_authorization": {"permission_scope"},
    "lifecycle": {"state_transition"},
    "client_runtime": {"runtime_chain"},
    "shared_component": {"shared_consumers"},
    "migration_compatibility": {"compatibility"},
    "security_sensitive": {"security_privacy"},
}

RADAR_EVIDENCE_LEVELS = {"direct", "strong_related", "same_model", "adjacent"}
RADAR_VERSION_SCOPES = {"current", "cross_version", "legacy", "unknown"}
RADAR_PRIORITIES = {"high", "medium", "low"}
RADAR_BASES = {"historical", "cluster", "requirement", "inference", "business_rule", "historical_testcase"}
RADAR_SOURCE_STATUSES = {"confirmed", "conflicted", "unknown"}
RADAR_CERTAINTIES = {"confirmed", "conditional"}
RADAR_CONSTRAINT_KINDS = {"invariant", "negative", "exclusion"}
RADAR_SCOPE_STATUSES = {"confirmed", "unknown"}
RADAR_REMOTE_STATUSES = {"queried", "no_match", "unavailable", "not_configured", "skipped"}
RADAR_TESTCASE_REVIEW_DECISIONS = {"selected", "scope_audit_only", "rejected"}
RADAR_EVIDENCE_SOURCE_TYPES = {
    "feishu_bug",
    "tester_experience",
    "cluster",
    "openviking_accepted",
    "openviking_testcase",
    "openviking_normalized",
    "openviking_defect",
}
RADAR_EVIDENCE_ROLES = {
    "risk_history",
    "behavior_rule",
    "regression_hint",
    "tester_experience",
    "cluster_signal",
}
RADAR_ASSERTION_BASIS_ROLES = {
    "historical": {"risk_history", "tester_experience"},
    "historical_testcase": {"regression_hint"},
    "business_rule": {"behavior_rule"},
    "cluster": {"cluster_signal"},
}
RADAR_OBLIGATION_EVIDENCE_ROLES = {"risk_history", "regression_hint", "tester_experience"}
RADAR_APPLICABILITY_STATUSES = {"matched", "not_matched", "unknown"}
RADAR_BRIDGE_KINDS = {
    "same_execution_point",
    "shared_data_model",
    "shared_component",
    "shared_runtime_dependency",
    "shared_lifecycle",
}
RADAR_BRIDGE_STATUSES = {"confirmed", "unknown", "none"}
RADAR_PROVENANCE_RELATIONS = {"independent_history", "same_requirement", "unknown"}
RADAR_ADMISSION_STATUSES = {"selected", "scope_audit_only", "rejected"}
RADAR_OPENVIKING_SOURCE_TYPES = {
    "openviking_accepted",
    "openviking_testcase",
    "openviking_normalized",
    "openviking_defect",
}


def radar_issue(code: str, detail: str) -> str:
    return f"{code}: {detail}"


def markdown_anchor_section(draft: str, anchor: str) -> str | None:
    """Return the most specific Markdown heading section containing an anchor."""
    anchor_norm = normalize_text(anchor)
    if not anchor_norm:
        return None
    headings = list(re.finditer(r"(?m)^(#{2,4})\s+(.+?)\s*$", draft))
    candidates: list[tuple[int, int, int, str]] = []
    for index, heading in enumerate(headings):
        start = heading.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(draft)
        section_text = draft[start:end]
        if anchor_norm not in normalize_text(section_text):
            continue
        level = len(heading.group(1))
        title = heading.group(2).strip()
        title_contains_anchor = int(anchor_norm in normalize_text(title))
        candidates.append((title_contains_anchor, level, -index, f"h{level}:{title}"))
    if not candidates:
        return "document-root" if anchor_norm in normalize_text(draft) else None
    return max(candidates)[3]


def radar_id_map(items: object, collection: str, errors: list[str]) -> dict[str, dict]:
    if not isinstance(items, list):
        errors.append(radar_issue("invalid_collection", f"{collection} must be a list"))
        return {}
    result: dict[str, dict] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(radar_issue("invalid_item", f"{collection}[{index}] must be an object"))
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            errors.append(radar_issue("missing_id", f"{collection}[{index}] has no id"))
            continue
        if item_id in result:
            errors.append(radar_issue("duplicate_id", f"{collection} contains duplicate id {item_id}"))
            continue
        result[item_id] = item
    return result


def load_radar_benchmarks() -> dict[str, dict]:
    if not RADAR_BENCHMARKS_FILE.exists():
        return {}
    data = json.loads(RADAR_BENCHMARKS_FILE.read_text(encoding="utf-8"))
    return {str(case.get("id")): case for case in data.get("cases", []) if case.get("id")}


def validate_radar_plan(
    plan: object,
    draft: str | None = None,
    benchmark: dict | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(plan, dict):
        return [radar_issue("invalid_plan", "plan must be a JSON object")], warnings

    version = plan.get("version")
    if version not in {1, 2, 3, 4, 5}:
        errors.append(radar_issue("invalid_version", "version must be 1, 2, 3, 4, or 5"))
    strict_plan = version in {2, 3, 4, 5}
    remote_plan = version in {3, 4, 5}
    assertion_plan = version in {4, 5}
    testcase_review_plan = version == 5

    requirement = plan.get("requirement")
    if not isinstance(requirement, dict):
        errors.append(radar_issue("invalid_requirement", "requirement must be an object"))
        requirement = {}
    for field in ["title", "object"]:
        if not str(requirement.get(field, "")).strip():
            errors.append(radar_issue("missing_requirement_field", field))
    surfaces = requirement.get("surfaces", [])
    if not isinstance(surfaces, list) or not any(str(value).strip() for value in surfaces):
        errors.append(radar_issue("missing_surfaces", "at least one surface is required"))
    profiles = set(requirement.get("change_profiles", [])) if isinstance(requirement.get("change_profiles", []), list) else set()
    if not profiles:
        errors.append(radar_issue("missing_change_profiles", "at least one change profile is required"))
    for profile in sorted(profiles - RADAR_CHANGE_PROFILES):
        errors.append(radar_issue("unknown_change_profile", profile))

    impacts = radar_id_map(plan.get("impact_inventory"), "impact_inventory", errors)
    evidence = radar_id_map(plan.get("evidence", []), "evidence", errors)
    risks = radar_id_map(plan.get("risks"), "risks", errors)
    exclusions = radar_id_map(plan.get("exclusions", []), "exclusions", errors)
    constraints = radar_id_map(plan.get("requirement_constraints", []) if not strict_plan else plan.get("requirement_constraints"), "requirement_constraints", errors)
    conflicts = radar_id_map(plan.get("requirement_conflicts", []) if not strict_plan else plan.get("requirement_conflicts"), "requirement_conflicts", errors)
    scope_models = radar_id_map(plan.get("scope_models", []) if not strict_plan else plan.get("scope_models"), "scope_models", errors)
    obligations = radar_id_map(
        plan.get("coverage_obligations", []) if not remote_plan else plan.get("coverage_obligations"),
        "coverage_obligations",
        errors,
    )

    remote_knowledge = plan.get("remote_knowledge")
    remote_status = ""
    remote_read_refs: set[str] = set()
    if remote_plan:
        if not isinstance(remote_knowledge, dict):
            errors.append(radar_issue("invalid_remote_knowledge", "version 3 or 4 requires a remote_knowledge object"))
            remote_knowledge = {}
        remote_status = str(remote_knowledge.get("status", "")).strip()
        if remote_status not in RADAR_REMOTE_STATUSES:
            errors.append(radar_issue("invalid_remote_status", remote_status or "missing"))
        if not str(remote_knowledge.get("reason", "")).strip():
            errors.append(radar_issue("missing_remote_reason", remote_status or "unknown"))
        queries = remote_knowledge.get("queries", [])
        read_refs = remote_knowledge.get("read_refs", [])
        if not isinstance(queries, list):
            errors.append(radar_issue("invalid_remote_queries", "queries must be a list"))
            queries = []
        if not isinstance(read_refs, list):
            errors.append(radar_issue("invalid_remote_read_refs", "read_refs must be a list"))
            read_refs = []
        if len(queries) > 5:
            errors.append(radar_issue("remote_query_budget_exceeded", str(len(queries))))
        if len(read_refs) > 8:
            errors.append(radar_issue("remote_read_budget_exceeded", str(len(read_refs))))
        if remote_status in {"queried", "no_match"} and not queries:
            errors.append(radar_issue("remote_status_without_query", remote_status))
        if remote_status == "queried" and not read_refs:
            errors.append(radar_issue("queried_without_read", "at least one viking:// item must be read"))
        for ref in read_refs:
            if not str(ref).startswith("viking://"):
                errors.append(radar_issue("invalid_remote_read_ref", str(ref)))
            else:
                remote_read_refs.add(str(ref))

    testcase_review = plan.get("historical_testcase_review")
    testcase_review_status = ""
    testcase_review_candidates: dict[str, dict] = {}
    if testcase_review_plan:
        if not isinstance(testcase_review, dict):
            errors.append(radar_issue(
                "invalid_historical_testcase_review",
                "version 5 requires a historical_testcase_review object",
            ))
            testcase_review = {}
        testcase_review_status = str(testcase_review.get("status", "")).strip()
        if testcase_review_status not in RADAR_REMOTE_STATUSES:
            errors.append(radar_issue(
                "invalid_historical_testcase_review_status",
                testcase_review_status or "missing",
            ))
        if not str(testcase_review.get("reason", "")).strip():
            errors.append(radar_issue(
                "missing_historical_testcase_review_reason",
                testcase_review_status or "unknown",
            ))
        testcase_queries = testcase_review.get("queries", [])
        testcase_candidates = testcase_review.get("candidates", [])
        if not isinstance(testcase_queries, list):
            errors.append(radar_issue("invalid_historical_testcase_queries", "queries must be a list"))
            testcase_queries = []
        if not isinstance(testcase_candidates, list):
            errors.append(radar_issue("invalid_historical_testcase_candidates", "candidates must be a list"))
            testcase_candidates = []
        if len(testcase_queries) > 5:
            errors.append(radar_issue("historical_testcase_query_budget_exceeded", str(len(testcase_queries))))
        if testcase_review_status in {"queried", "no_match"} and not testcase_queries:
            errors.append(radar_issue(
                "historical_testcase_status_without_query",
                testcase_review_status,
            ))
        if testcase_review_status == "queried" and not testcase_candidates:
            errors.append(radar_issue(
                "historical_testcase_queried_without_candidates",
                "use no_match when the search produced no candidates",
            ))
        if testcase_review_status in {"no_match", "unavailable", "not_configured", "skipped"} and testcase_candidates:
            errors.append(radar_issue(
                "historical_testcase_status_conflicts_with_candidates",
                testcase_review_status,
            ))
        for index, candidate in enumerate(testcase_candidates):
            if not isinstance(candidate, dict):
                errors.append(radar_issue("invalid_historical_testcase_candidate", str(index)))
                continue
            candidate_id = str(candidate.get("candidate_id", "")).strip()
            if not candidate_id:
                errors.append(radar_issue("missing_historical_testcase_candidate_id", str(index)))
                continue
            if candidate_id in testcase_review_candidates:
                errors.append(radar_issue("duplicate_historical_testcase_candidate_id", candidate_id))
                continue
            testcase_review_candidates[candidate_id] = candidate
            if not str(candidate.get("source_ref", "")).startswith("viking://"):
                errors.append(radar_issue("invalid_historical_testcase_source_ref", candidate_id))
            if not str(candidate.get("title", "")).strip():
                errors.append(radar_issue("missing_historical_testcase_title", candidate_id))
            decision = candidate.get("decision")
            if decision not in RADAR_TESTCASE_REVIEW_DECISIONS:
                errors.append(radar_issue(
                    "invalid_historical_testcase_decision",
                    f"{candidate_id}={decision}",
                ))
            if not str(candidate.get("reason", "")).strip():
                errors.append(radar_issue("missing_historical_testcase_decision_reason", candidate_id))
            risk_ids = candidate.get("risk_ids", [])
            if not isinstance(risk_ids, list):
                errors.append(radar_issue("invalid_historical_testcase_risk_ids", candidate_id))
            if decision == "selected" and not str(candidate.get("evidence_id", "")).strip():
                errors.append(radar_issue("selected_historical_testcase_without_evidence", candidate_id))
            if decision == "selected" and not risk_ids:
                errors.append(radar_issue("selected_historical_testcase_without_influence", candidate_id))

    for impact_id, item in impacts.items():
        if not str(item.get("label", "")).strip():
            errors.append(radar_issue("missing_impact_label", impact_id))
        if item.get("priority") not in RADAR_PRIORITIES:
            errors.append(radar_issue("invalid_impact_priority", f"{impact_id}={item.get('priority')}"))
        if strict_plan and item.get("source_status") not in RADAR_SOURCE_STATUSES:
            errors.append(radar_issue("invalid_impact_source_status", f"{impact_id}={item.get('source_status')}"))

    for constraint_id, item in constraints.items():
        if not str(item.get("label", "")).strip():
            errors.append(radar_issue("missing_constraint_label", constraint_id))
        if item.get("kind") not in RADAR_CONSTRAINT_KINDS:
            errors.append(radar_issue("invalid_constraint_kind", f"{constraint_id}={item.get('kind')}"))
        if item.get("priority") not in RADAR_PRIORITIES:
            errors.append(radar_issue("invalid_constraint_priority", f"{constraint_id}={item.get('priority')}"))

    conflict_risk_ids: dict[str, list[str]] = {}
    for conflict_id, item in conflicts.items():
        if not str(item.get("label", "")).strip():
            errors.append(radar_issue("missing_conflict_label", conflict_id))
        if not str(item.get("reason", "")).strip():
            errors.append(radar_issue("missing_conflict_reason", conflict_id))
        impact_ids = item.get("impact_ids", [])
        if not isinstance(impact_ids, list) or not impact_ids:
            errors.append(radar_issue("conflict_without_impact", conflict_id))
        else:
            for impact_id in impact_ids:
                if impact_id not in impacts:
                    errors.append(radar_issue("unknown_conflict_impact", f"{conflict_id}->{impact_id}"))
        risk_ids = item.get("risk_ids", [])
        if not isinstance(risk_ids, list) or not risk_ids:
            errors.append(radar_issue("conflict_without_risk", conflict_id))
            risk_ids = []
        conflict_risk_ids[conflict_id] = risk_ids

    if strict_plan and "client_runtime" in profiles and not scope_models:
        errors.append(radar_issue("missing_scope_model", "client_runtime requires resource ownership and sharing review"))
    unknown_scope_risks: set[str] = set()
    for scope_id, item in scope_models.items():
        if not str(item.get("subject", "")).strip():
            errors.append(radar_issue("missing_scope_subject", scope_id))
        status = item.get("status")
        if status not in RADAR_SCOPE_STATUSES:
            errors.append(radar_issue("invalid_scope_status", f"{scope_id}={status}"))
        for field in ["owner", "sharing", "lifecycle", "reason"]:
            if not str(item.get(field, "")).strip():
                errors.append(radar_issue("missing_scope_field", f"{scope_id}.{field}"))
        risk_ids = item.get("risk_ids", [])
        if not isinstance(risk_ids, list) or not risk_ids:
            errors.append(radar_issue("scope_without_risk", scope_id))
            risk_ids = []
        if status == "unknown":
            unknown_scope_risks.update(str(risk_id) for risk_id in risk_ids)

    dimension_rows = plan.get("dimension_applicability")
    if not isinstance(dimension_rows, list):
        errors.append(radar_issue("invalid_collection", "dimension_applicability must be a list"))
        dimension_rows = []
    dimension_status: dict[str, str] = {}
    for index, row in enumerate(dimension_rows):
        if not isinstance(row, dict):
            errors.append(radar_issue("invalid_item", f"dimension_applicability[{index}] must be an object"))
            continue
        dimension = str(row.get("dimension", "")).strip()
        status = str(row.get("status", "")).strip()
        reason = str(row.get("reason", "")).strip()
        if dimension not in RADAR_DIMENSIONS:
            errors.append(radar_issue("unknown_dimension", dimension or f"index {index}"))
            continue
        if dimension in dimension_status:
            errors.append(radar_issue("duplicate_dimension", dimension))
            continue
        if status not in {"applicable", "not_applicable"}:
            errors.append(radar_issue("invalid_dimension_status", f"{dimension}={status}"))
        if not reason:
            errors.append(radar_issue("missing_dimension_reason", dimension))
        dimension_status[dimension] = status
    for dimension in sorted(RADAR_DIMENSIONS - set(dimension_status)):
        errors.append(radar_issue("dimension_not_assessed", dimension))
    for profile in profiles & RADAR_CHANGE_PROFILES:
        for dimension in RADAR_PROFILE_CORE_DIMENSIONS.get(profile, set()):
            if dimension_status.get(dimension) != "applicable":
                errors.append(radar_issue("profile_core_dimension_not_applicable", f"{profile}->{dimension}"))

    legacy_in_scope = bool(requirement.get("legacy_in_scope", False))
    for evidence_id, item in evidence.items():
        level = item.get("level")
        version_scope = item.get("version_scope")
        if level not in RADAR_EVIDENCE_LEVELS:
            errors.append(radar_issue("invalid_evidence_level", f"{evidence_id}={level}"))
        if version_scope not in RADAR_VERSION_SCOPES:
            errors.append(radar_issue("invalid_version_scope", f"{evidence_id}={version_scope}"))
        source_type = str(item.get("source_type", "")).strip()
        evidence_role = str(item.get("evidence_role", "")).strip()
        applicability_status = str(item.get("applicability_status", "")).strip()
        source_ref = str(item.get("source_ref", "")).strip()
        if remote_plan:
            if source_type not in RADAR_EVIDENCE_SOURCE_TYPES:
                errors.append(radar_issue("invalid_evidence_source_type", f"{evidence_id}={source_type or 'missing'}"))
            if evidence_role not in RADAR_EVIDENCE_ROLES:
                errors.append(radar_issue("invalid_evidence_role", f"{evidence_id}={evidence_role or 'missing'}"))
            if not source_ref:
                errors.append(radar_issue("missing_source_ref", evidence_id))
            if not str(item.get("source_updated_at", "")).strip():
                errors.append(radar_issue("missing_source_updated_at", evidence_id))
            if applicability_status not in RADAR_APPLICABILITY_STATUSES:
                errors.append(radar_issue("invalid_applicability_status", f"{evidence_id}={applicability_status or 'missing'}"))
            if source_type in RADAR_OPENVIKING_SOURCE_TYPES and not source_ref.startswith("viking://"):
                errors.append(radar_issue("invalid_openviking_source_ref", evidence_id))
            if source_type in RADAR_OPENVIKING_SOURCE_TYPES:
                provenance_relation = str(item.get("provenance_relation", "")).strip()
                admission_status = str(item.get("admission_status", "")).strip()
                claim_boundary = str(item.get("claim_boundary", "")).strip()
                if provenance_relation not in RADAR_PROVENANCE_RELATIONS:
                    errors.append(
                        radar_issue(
                            "invalid_provenance_relation",
                            f"{evidence_id}={provenance_relation or 'missing'}",
                        )
                    )
                if admission_status not in RADAR_ADMISSION_STATUSES:
                    errors.append(
                        radar_issue(
                            "invalid_admission_status",
                            f"{evidence_id}={admission_status or 'missing'}",
                        )
                    )
                if not claim_boundary:
                    errors.append(radar_issue("missing_claim_boundary", evidence_id))
                if provenance_relation == "same_requirement" and admission_status == "selected":
                    errors.append(radar_issue("same_requirement_selected", evidence_id))
                if applicability_status == "not_matched" and admission_status == "selected":
                    errors.append(radar_issue("not_matched_remote_selected", evidence_id))
                if admission_status == "selected" and source_ref not in remote_read_refs:
                    errors.append(radar_issue("selected_remote_not_read", evidence_id))
            if source_type in {"feishu_bug", "openviking_defect"} and not str(item.get("bug_id", "")).strip():
                errors.append(radar_issue("missing_bug_id", evidence_id))
            expected_role = {
                "feishu_bug": "risk_history",
                "openviking_defect": "risk_history",
                "openviking_accepted": "behavior_rule",
                "openviking_testcase": "regression_hint",
                "openviking_normalized": "regression_hint",
                "tester_experience": "tester_experience",
                "cluster": "cluster_signal",
            }.get(source_type)
            if expected_role and evidence_role != expected_role:
                errors.append(radar_issue("evidence_role_source_mismatch", f"{evidence_id}:{source_type}->{evidence_role}"))
        elif not str(item.get("bug_id", "")).strip():
            errors.append(radar_issue("missing_bug_id", evidence_id))
        if not str(item.get("applicability_reason", "")).strip():
            errors.append(radar_issue("missing_evidence_reason", evidence_id))
        if level == "direct" and (item.get("same_object") is not True or item.get("same_entry_or_chain") is not True):
            errors.append(radar_issue("invalid_direct_evidence", evidence_id))
        if level == "direct" and version_scope == "legacy" and not legacy_in_scope:
            errors.append(radar_issue("legacy_direct_evidence", evidence_id))
        if level == "direct" and version_scope == "unknown":
            warnings.append(radar_issue("unknown_direct_version", evidence_id))
        if assertion_plan and level == "strong_related":
            bridge = item.get("bridge")
            if not isinstance(bridge, dict):
                errors.append(radar_issue("missing_strong_related_bridge", evidence_id))
                continue
            bridge_kind = str(bridge.get("kind", "")).strip()
            bridge_status = str(bridge.get("status", "")).strip()
            bridge_description = str(bridge.get("description", "")).strip()
            current_trigger = str(bridge.get("current_trigger", "")).strip()
            if bridge_kind not in RADAR_BRIDGE_KINDS:
                errors.append(
                    radar_issue(
                        "invalid_evidence_bridge_kind",
                        f"{evidence_id}={bridge_kind or 'missing'}",
                    )
                )
            if bridge_status not in RADAR_BRIDGE_STATUSES:
                errors.append(
                    radar_issue(
                        "invalid_evidence_bridge_status",
                        f"{evidence_id}={bridge_status or 'missing'}",
                    )
                )
            if not bridge_description:
                errors.append(radar_issue("missing_evidence_bridge_description", evidence_id))
            if not current_trigger:
                errors.append(radar_issue("missing_evidence_bridge_trigger", evidence_id))
            if bridge_status != "confirmed":
                errors.append(radar_issue("strong_related_bridge_not_confirmed", evidence_id))
            if applicability_status != "matched":
                errors.append(
                    radar_issue(
                        "strong_related_applicability_not_matched",
                        f"{evidence_id}={applicability_status or 'missing'}",
                    )
                )
            if bridge_kind == "same_execution_point" and item.get("same_entry_or_chain") is not True:
                errors.append(radar_issue("same_execution_bridge_without_same_chain", evidence_id))

    obligation_sources: dict[str, set[str]] = {}
    obligation_mechanisms: dict[str, str] = {}
    for obligation_id, item in obligations.items():
        mechanism = str(item.get("failure_mechanism", "")).strip()
        assertion = str(item.get("required_assertion", "")).strip()
        priority = item.get("priority")
        if not mechanism:
            errors.append(radar_issue("missing_obligation_mechanism", obligation_id))
        else:
            normalized_mechanism = normalize_text(mechanism)
            if normalized_mechanism in obligation_mechanisms:
                errors.append(
                    radar_issue(
                        "duplicate_obligation_mechanism",
                        f"{obligation_id} duplicates {obligation_mechanisms[normalized_mechanism]}",
                    )
                )
            else:
                obligation_mechanisms[normalized_mechanism] = obligation_id
        trigger_conditions = item.get("trigger_conditions", [])
        if (
            not isinstance(trigger_conditions, list)
            or not trigger_conditions
            or not all(str(value).strip() for value in trigger_conditions)
        ):
            errors.append(radar_issue("missing_obligation_triggers", obligation_id))
        if not assertion:
            errors.append(radar_issue("missing_obligation_assertion", obligation_id))
        if priority not in RADAR_PRIORITIES:
            errors.append(radar_issue("invalid_obligation_priority", f"{obligation_id}={priority}"))
        source_ids = item.get("source_ids", [])
        if not isinstance(source_ids, list) or not source_ids:
            errors.append(radar_issue("obligation_without_sources", obligation_id))
            source_ids = []
        source_set: set[str] = set()
        for source_id in source_ids:
            source_id = str(source_id)
            if source_id not in evidence:
                errors.append(radar_issue("unknown_obligation_source", f"{obligation_id}->{source_id}"))
                continue
            source_set.add(source_id)
            source_item = evidence[source_id]
            if source_item.get("level") not in {"direct", "strong_related"}:
                errors.append(radar_issue("weak_obligation_source", f"{obligation_id}->{source_id}"))
            if remote_plan and source_item.get("evidence_role") not in RADAR_OBLIGATION_EVIDENCE_ROLES:
                errors.append(radar_issue("invalid_obligation_source_role", f"{obligation_id}->{source_id}"))
            if source_item.get("source_type") in RADAR_OPENVIKING_SOURCE_TYPES:
                if source_item.get("admission_status") != "selected":
                    errors.append(radar_issue("non_selected_obligation_source", f"{obligation_id}->{source_id}"))
                if source_item.get("provenance_relation") == "same_requirement":
                    errors.append(radar_issue("same_requirement_obligation_source", f"{obligation_id}->{source_id}"))
        obligation_sources[obligation_id] = source_set

    covered_impacts: set[str] = set()
    covered_constraints: set[str] = set()
    covered_obligations: set[str] = set()
    obligation_risk_ids: dict[str, list[str]] = defaultdict(list)
    risks_by_dimension: dict[str, list[str]] = defaultdict(list)
    assertion_render_anchors: dict[str, str] = {}
    assertion_draft_anchors: list[tuple[str, str]] = []
    assertion_condition_draft_anchors: list[tuple[str, str]] = []
    for risk_id, item in risks.items():
        dimension = item.get("dimension")
        priority = item.get("priority")
        basis = item.get("basis")
        if dimension not in RADAR_DIMENSIONS:
            errors.append(radar_issue("invalid_risk_dimension", f"{risk_id}={dimension}"))
        elif dimension_status.get(dimension) != "applicable":
            errors.append(radar_issue("risk_dimension_not_applicable", f"{risk_id}->{dimension}"))
        else:
            risks_by_dimension[dimension].append(risk_id)
        if priority not in RADAR_PRIORITIES:
            errors.append(radar_issue("invalid_risk_priority", f"{risk_id}={priority}"))
        if basis not in RADAR_BASES:
            errors.append(radar_issue("invalid_risk_basis", f"{risk_id}={basis}"))
        certainty = item.get("certainty")
        if strict_plan and certainty not in RADAR_CERTAINTIES:
            errors.append(radar_issue("invalid_risk_certainty", f"{risk_id}={certainty}"))
        if certainty == "conditional" and not str(item.get("condition", "")).strip():
            errors.append(radar_issue("conditional_risk_without_condition", risk_id))
        observable = str(item.get("observable_focus", "")).strip()
        if not observable:
            errors.append(radar_issue("missing_observable_focus", risk_id))
        anchor = str(item.get("render_anchor", "")).strip()
        if priority in {"high", "medium"} and not anchor:
            errors.append(radar_issue("missing_render_anchor", risk_id))
        impact_ids = item.get("impact_ids", [])
        if not isinstance(impact_ids, list) or not impact_ids:
            errors.append(radar_issue("risk_without_impact", risk_id))
            impact_ids = []
        else:
            for impact_id in impact_ids:
                if impact_id not in impacts:
                    errors.append(radar_issue("unknown_impact_reference", f"{risk_id}->{impact_id}"))
                else:
                    covered_impacts.add(impact_id)
        source_ids = item.get("source_ids", [])
        if not isinstance(source_ids, list):
            errors.append(radar_issue("invalid_source_ids", risk_id))
            source_ids = []
        for source_id in source_ids:
            if source_id not in evidence:
                errors.append(radar_issue("unknown_evidence_reference", f"{risk_id}->{source_id}"))
                continue
            if remote_plan:
                source_item = evidence[source_id]
                source_applicability = source_item.get("applicability_status")
                if source_applicability == "not_matched":
                    errors.append(radar_issue("not_matched_evidence_used", f"{risk_id}->{source_id}"))
                if source_applicability == "unknown" and certainty != "conditional":
                    errors.append(radar_issue("unknown_evidence_requires_condition", f"{risk_id}->{source_id}"))
                if source_item.get("source_type") in RADAR_OPENVIKING_SOURCE_TYPES:
                    admission_status = source_item.get("admission_status")
                    provenance_relation = source_item.get("provenance_relation")
                    if admission_status != "selected":
                        errors.append(radar_issue("non_selected_remote_evidence_used", f"{risk_id}->{source_id}"))
                    if provenance_relation == "same_requirement":
                        errors.append(radar_issue("same_requirement_evidence_used", f"{risk_id}->{source_id}"))
                    if provenance_relation == "unknown" and certainty != "conditional":
                        errors.append(radar_issue("unknown_provenance_requires_condition", f"{risk_id}->{source_id}"))
        assertion_source_union: set[str] = set()
        assertion_history_sources: dict[str, set[str]] = {}
        if assertion_plan:
            assertions = item.get("assertions")
            if not isinstance(assertions, list) or not assertions:
                errors.append(radar_issue("missing_assertions", risk_id))
                assertions = []
            assertion_ids: set[str] = set()
            assertion_bases: set[str] = set()
            assertion_certainties: set[str] = set()
            for index, assertion in enumerate(assertions):
                assertion_ref = f"{risk_id}.assertions[{index}]"
                if not isinstance(assertion, dict):
                    errors.append(radar_issue("invalid_assertion", assertion_ref))
                    continue
                assertion_id = str(assertion.get("id", "")).strip()
                if not assertion_id:
                    errors.append(radar_issue("missing_assertion_id", assertion_ref))
                    assertion_id = f"index-{index}"
                elif assertion_id in assertion_ids:
                    errors.append(radar_issue("duplicate_assertion_id", f"{risk_id}.{assertion_id}"))
                assertion_ids.add(assertion_id)
                assertion_ref = f"{risk_id}.{assertion_id}"

                if not str(assertion.get("text", "")).strip():
                    errors.append(radar_issue("missing_assertion_text", assertion_ref))
                assertion_basis = assertion.get("basis")
                if assertion_basis not in RADAR_BASES:
                    errors.append(radar_issue("invalid_assertion_basis", f"{assertion_ref}={assertion_basis}"))
                else:
                    assertion_bases.add(str(assertion_basis))
                assertion_certainty = assertion.get("certainty")
                if assertion_certainty not in RADAR_CERTAINTIES:
                    errors.append(
                        radar_issue("invalid_assertion_certainty", f"{assertion_ref}={assertion_certainty}")
                    )
                else:
                    assertion_certainties.add(str(assertion_certainty))
                if assertion_certainty == "conditional" and not str(assertion.get("condition", "")).strip():
                    errors.append(radar_issue("conditional_assertion_without_condition", assertion_ref))
                condition_render_anchor = str(assertion.get("condition_render_anchor", "")).strip()
                if assertion_certainty == "conditional" and not condition_render_anchor:
                    errors.append(radar_issue("conditional_assertion_without_render_anchor", assertion_ref))
                if condition_render_anchor:
                    assertion_condition_draft_anchors.append((assertion_ref, condition_render_anchor))

                assertion_source_ids = assertion.get("source_ids", [])
                if not isinstance(assertion_source_ids, list):
                    errors.append(radar_issue("invalid_assertion_source_ids", assertion_ref))
                    assertion_source_ids = []
                assertion_source_set = {str(value) for value in assertion_source_ids}
                assertion_source_union.update(assertion_source_set)
                if assertion_basis in {"historical", "cluster", "business_rule", "historical_testcase"} and not assertion_source_set:
                    errors.append(radar_issue("assertion_without_evidence", assertion_ref))
                if assertion_basis == "inference" and assertion_source_set:
                    errors.append(radar_issue("inference_assertion_has_evidence", assertion_ref))
                if assertion_basis == "requirement" and assertion_source_set:
                    errors.append(radar_issue("requirement_assertion_has_evidence", assertion_ref))

                for source_id in assertion_source_set:
                    if source_id not in evidence:
                        errors.append(radar_issue("unknown_assertion_source", f"{assertion_ref}->{source_id}"))
                        continue
                    if source_id not in {str(value) for value in source_ids}:
                        errors.append(radar_issue("assertion_source_not_in_risk", f"{assertion_ref}->{source_id}"))
                    source_item = evidence[source_id]
                    source_applicability = source_item.get("applicability_status")
                    if source_applicability == "not_matched":
                        errors.append(radar_issue("not_matched_assertion_evidence", f"{assertion_ref}->{source_id}"))
                    if source_applicability == "unknown" and assertion_certainty != "conditional":
                        errors.append(
                            radar_issue("unknown_assertion_evidence_requires_condition", f"{assertion_ref}->{source_id}")
                        )
                    if source_item.get("source_type") in RADAR_OPENVIKING_SOURCE_TYPES:
                        if source_item.get("admission_status") != "selected":
                            errors.append(radar_issue("non_selected_assertion_evidence", f"{assertion_ref}->{source_id}"))
                        if source_item.get("provenance_relation") == "same_requirement":
                            errors.append(radar_issue("same_requirement_assertion_evidence", f"{assertion_ref}->{source_id}"))
                        if source_item.get("provenance_relation") == "unknown" and assertion_certainty != "conditional":
                            errors.append(
                                radar_issue("unknown_assertion_provenance_requires_condition", f"{assertion_ref}->{source_id}")
                            )

                source_roles = {
                    str(evidence[source_id].get("evidence_role", ""))
                    for source_id in assertion_source_set
                    if source_id in evidence
                }
                if assertion_basis == "business_rule" and "behavior_rule" not in source_roles:
                    errors.append(radar_issue("business_rule_assertion_without_rule_evidence", assertion_ref))
                if assertion_basis == "historical_testcase" and "regression_hint" not in source_roles:
                    errors.append(radar_issue("testcase_assertion_without_testcase_evidence", assertion_ref))
                allowed_roles = RADAR_ASSERTION_BASIS_ROLES.get(str(assertion_basis))
                if allowed_roles is not None:
                    invalid_roles = source_roles - allowed_roles
                    if invalid_roles:
                        errors.append(
                            radar_issue(
                                "assertion_basis_evidence_role_mismatch",
                                f"{assertion_ref}:{assertion_basis}->{','.join(sorted(invalid_roles))}",
                            )
                        )
                if assertion_basis in {"historical", "historical_testcase"}:
                    strong_sources = {
                        source_id
                        for source_id in assertion_source_set
                        if source_id in evidence
                        and evidence[source_id].get("level") in {"direct", "strong_related"}
                        and evidence[source_id].get("evidence_role") in RADAR_OBLIGATION_EVIDENCE_ROLES
                    }
                    if strong_sources:
                        assertion_history_sources[assertion_ref] = strong_sources

                assertion_anchor = str(assertion.get("render_anchor", "")).strip()
                if priority in {"high", "medium"} and not assertion_anchor:
                    errors.append(radar_issue("missing_assertion_render_anchor", assertion_ref))
                if assertion_anchor:
                    normalized_anchor = normalize_text(assertion_anchor)
                    prior_assertion = assertion_render_anchors.get(normalized_anchor)
                    if prior_assertion:
                        errors.append(
                            radar_issue(
                                "duplicate_assertion_render_anchor",
                                f"{assertion_ref} duplicates {prior_assertion}",
                            )
                        )
                    else:
                        assertion_render_anchors[normalized_anchor] = assertion_ref
                    assertion_draft_anchors.append((assertion_ref, assertion_anchor))

            unused_risk_sources = {str(value) for value in source_ids} - assertion_source_union
            for source_id in sorted(unused_risk_sources):
                errors.append(radar_issue("risk_source_without_assertion", f"{risk_id}->{source_id}"))
            if assertion_bases and basis not in assertion_bases:
                errors.append(
                    radar_issue(
                        "risk_basis_not_in_assertions",
                        f"{risk_id}:{basis} not in {','.join(sorted(assertion_bases))}",
                    )
                )
            if certainty == "conditional" and "conditional" not in assertion_certainties:
                errors.append(radar_issue("conditional_risk_without_conditional_assertion", risk_id))
        coverage_obligation_ids = item.get("coverage_obligation_ids", [])
        if remote_plan and not isinstance(coverage_obligation_ids, list):
            errors.append(radar_issue("invalid_coverage_obligation_ids", risk_id))
            coverage_obligation_ids = []
        elif not isinstance(coverage_obligation_ids, list):
            coverage_obligation_ids = []
        for obligation_id in coverage_obligation_ids:
            obligation_id = str(obligation_id)
            if obligation_id not in obligations:
                errors.append(radar_issue("unknown_obligation_reference", f"{risk_id}->{obligation_id}"))
                continue
            covered_obligations.add(obligation_id)
            obligation_risk_ids[obligation_id].append(risk_id)
            missing_sources = obligation_sources.get(obligation_id, set()) - {str(value) for value in source_ids}
            if missing_sources:
                errors.append(
                    radar_issue(
                        "obligation_sources_not_in_risk",
                        f"{risk_id}->{obligation_id}:{','.join(sorted(missing_sources))}",
                    )
                )
        if assertion_plan and assertion_history_sources:
            mapped_obligation_sources: set[str] = set()
            for obligation_id in coverage_obligation_ids:
                mapped_obligation_sources.update(obligation_sources.get(str(obligation_id), set()))
            for assertion_ref, strong_sources in assertion_history_sources.items():
                missing_sources = strong_sources - mapped_obligation_sources
                if missing_sources:
                    errors.append(
                        radar_issue(
                            "assertion_history_without_obligation",
                            f"{assertion_ref}:{','.join(sorted(missing_sources))}",
                        )
                    )
        constraint_ids = item.get("constraint_ids", [])
        if not isinstance(constraint_ids, list):
            errors.append(radar_issue("invalid_constraint_ids", risk_id))
            constraint_ids = []
        for constraint_id in constraint_ids:
            if constraint_id not in constraints:
                errors.append(radar_issue("unknown_constraint_reference", f"{risk_id}->{constraint_id}"))
            else:
                covered_constraints.add(constraint_id)
        if basis in {"historical", "cluster", "business_rule", "historical_testcase"} and not source_ids:
            errors.append(radar_issue("historical_risk_without_evidence", risk_id))
        if basis == "inference" and source_ids:
            warnings.append(radar_issue("inference_has_evidence", risk_id))
        if remote_plan and basis in {"historical", "historical_testcase"}:
            has_strong_history = any(
                source_id in evidence
                and evidence[source_id].get("level") in {"direct", "strong_related"}
                and evidence[source_id].get("evidence_role") in RADAR_OBLIGATION_EVIDENCE_ROLES
                for source_id in source_ids
            )
            if has_strong_history and not coverage_obligation_ids:
                errors.append(radar_issue("historical_risk_without_obligation", risk_id))
        if remote_plan and source_ids:
            source_roles = {str(evidence[source_id].get("evidence_role", "")) for source_id in source_ids if source_id in evidence}
            if basis == "business_rule" and "behavior_rule" not in source_roles:
                errors.append(radar_issue("business_rule_without_rule_evidence", risk_id))
            if basis == "historical_testcase" and "regression_hint" not in source_roles:
                errors.append(radar_issue("historical_testcase_without_testcase_evidence", risk_id))

        if strict_plan:
            uncertain_impacts = [
                impact_id
                for impact_id in impact_ids
                if impact_id in impacts and impacts[impact_id].get("source_status") in {"conflicted", "unknown"}
            ]
            if uncertain_impacts and certainty != "conditional":
                errors.append(radar_issue("uncertain_impact_requires_condition", f"{risk_id}->{','.join(uncertain_impacts)}"))

    excluded_targets = set()
    for exclusion_id, item in exclusions.items():
        target_id = str(item.get("target_id", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not target_id:
            errors.append(radar_issue("missing_exclusion_target", exclusion_id))
        else:
            excluded_targets.add(target_id)
        if not reason:
            errors.append(radar_issue("missing_exclusion_reason", exclusion_id))

    for conflict_id, risk_ids in conflict_risk_ids.items():
        for risk_id in risk_ids:
            if risk_id not in risks:
                errors.append(radar_issue("unknown_conflict_risk", f"{conflict_id}->{risk_id}"))
            elif risks[risk_id].get("certainty") != "conditional" or not str(risks[risk_id].get("condition", "")).strip():
                errors.append(radar_issue("conflict_risk_not_conditional", f"{conflict_id}->{risk_id}"))

    for risk_id in unknown_scope_risks:
        if risk_id not in risks:
            errors.append(radar_issue("unknown_scope_risk", risk_id))
        elif risks[risk_id].get("certainty") != "conditional" or not str(risks[risk_id].get("condition", "")).strip():
            errors.append(radar_issue("unknown_scope_risk_not_conditional", risk_id))

    for impact_id in impacts:
        if impact_id not in covered_impacts and impact_id not in excluded_targets:
            errors.append(radar_issue("impact_uncovered", impact_id))
    for constraint_id, item in constraints.items():
        if item.get("priority") in {"high", "medium"} and constraint_id not in covered_constraints and constraint_id not in excluded_targets:
            errors.append(radar_issue("constraint_uncovered", constraint_id))
    for obligation_id, item in obligations.items():
        if item.get("priority") in {"high", "medium"} and obligation_id not in covered_obligations and obligation_id not in excluded_targets:
            errors.append(radar_issue("obligation_uncovered", obligation_id))
    for dimension, status in dimension_status.items():
        if status == "applicable" and not risks_by_dimension.get(dimension):
            errors.append(radar_issue("applicable_dimension_without_risk", dimension))

    if testcase_review_plan:
        selected_review_evidence_ids: set[str] = set()
        for candidate_id, candidate in testcase_review_candidates.items():
            decision = candidate.get("decision")
            evidence_id = str(candidate.get("evidence_id", "")).strip()
            candidate_risk_ids = candidate.get("risk_ids", [])
            if not isinstance(candidate_risk_ids, list):
                candidate_risk_ids = []
            for risk_id in candidate_risk_ids:
                if risk_id not in risks:
                    errors.append(radar_issue(
                        "historical_testcase_unknown_risk",
                        f"{candidate_id}->{risk_id}",
                    ))
            if decision != "selected":
                continue
            selected_review_evidence_ids.add(evidence_id)
            evidence_item = evidence.get(evidence_id)
            if not evidence_item:
                errors.append(radar_issue(
                    "historical_testcase_unknown_evidence",
                    f"{candidate_id}->{evidence_id}",
                ))
                continue
            if evidence_item.get("evidence_role") != "regression_hint":
                errors.append(radar_issue(
                    "historical_testcase_evidence_role_mismatch",
                    f"{candidate_id}->{evidence_id}",
                ))
            if evidence_item.get("admission_status") != "selected":
                errors.append(radar_issue(
                    "historical_testcase_evidence_not_selected",
                    f"{candidate_id}->{evidence_id}",
                ))
            for risk_id in candidate_risk_ids:
                if risk_id in risks and evidence_id not in set(risks[risk_id].get("source_ids", [])):
                    errors.append(radar_issue(
                        "historical_testcase_influence_not_traced",
                        f"{candidate_id}->{risk_id}",
                    ))
        selected_regression_evidence_ids = {
            evidence_id
            for evidence_id, item in evidence.items()
            if item.get("source_type") in RADAR_OPENVIKING_SOURCE_TYPES
            and item.get("evidence_role") == "regression_hint"
            and item.get("admission_status") == "selected"
        }
        for evidence_id in sorted(selected_regression_evidence_ids - selected_review_evidence_ids):
            errors.append(radar_issue(
                "selected_historical_testcase_missing_review",
                evidence_id,
            ))

    if remote_plan:
        has_openviking_evidence = any(item.get("source_type") in RADAR_OPENVIKING_SOURCE_TYPES for item in evidence.values())
        has_selected_openviking_evidence = any(
            item.get("source_type") in RADAR_OPENVIKING_SOURCE_TYPES
            and item.get("admission_status") == "selected"
            for item in evidence.values()
        )
        if remote_status == "queried" and not has_selected_openviking_evidence:
            warnings.append(radar_issue("queried_without_selected_remote_evidence", "remote evidence was read but none was selected"))
        if remote_status in {"no_match", "unavailable", "not_configured", "skipped"} and has_openviking_evidence:
            errors.append(radar_issue("remote_status_conflicts_with_evidence", remote_status))

    if draft is not None:
        draft_norm = normalize_text(draft)
        for risk_id, item in risks.items():
            if item.get("priority") not in {"high", "medium"}:
                continue
            anchor = normalize_text(str(item.get("render_anchor", "")))
            if anchor and anchor not in draft_norm:
                errors.append(radar_issue("draft_missing_risk", f"{risk_id}:{item.get('render_anchor')}"))
        if assertion_plan:
            for assertion_ref, assertion_anchor in assertion_draft_anchors:
                if normalize_text(assertion_anchor) not in draft_norm:
                    errors.append(
                        radar_issue("draft_missing_assertion", f"{assertion_ref}:{assertion_anchor}")
                    )
            for assertion_ref, condition_anchor in assertion_condition_draft_anchors:
                if normalize_text(condition_anchor) not in draft_norm:
                    errors.append(
                        radar_issue(
                            "draft_missing_assertion_condition",
                            f"{assertion_ref}:{condition_anchor}",
                        )
                    )
        if re.search(r"用例\s*(id|编号)|前置条件|预期结果", draft, flags=re.IGNORECASE):
            warnings.append(radar_issue("testcase_shaped_draft", "draft may be turning into full testcases"))
        generation_process_patterns = (
            r"新增(?:的)?(?:直接|强相关)?历史\s*(?:Bug|缺陷)",
            r"新增(?:直接|强相关)历史",
        )
        if any(re.search(pattern, draft, flags=re.IGNORECASE) for pattern in generation_process_patterns):
            errors.append(
                radar_issue(
                    "draft_generation_process_wording",
                    "use stable evidence labels instead of generation-timeline wording",
                )
            )
        if remote_status == "queried" and re.search(r"OpenViking", draft, flags=re.IGNORECASE):
            warnings.append(
                radar_issue(
                    "draft_exposes_remote_implementation",
                    "describe selected source categories instead of the successful retrieval implementation",
                )
            )

        for obligation_id, linked_risk_ids in obligation_risk_ids.items():
            if len(linked_risk_ids) < 2:
                continue
            section_rows = []
            for risk_id in linked_risk_ids:
                anchor = str(risks.get(risk_id, {}).get("render_anchor", "")).strip()
                section = markdown_anchor_section(draft, anchor) if anchor else None
                if section:
                    section_rows.append((risk_id, section))
            distinct_sections = {section for _, section in section_rows}
            if len(distinct_sections) > 1:
                detail = "; ".join(f"{risk_id}@{section}" for risk_id, section in section_rows)
                warnings.append(
                    radar_issue(
                        "obligation_split_across_sections",
                        f"{obligation_id} -> {detail}; keep one primary visible home unless the claims are materially different",
                    )
                )

        risk_priorities = [
            str(item.get("priority"))
            for item in risks.values()
            if item.get("priority") in RADAR_PRIORITIES
        ]
        if len(risk_priorities) >= 4:
            dominant_priority, dominant_count = Counter(risk_priorities).most_common(1)[0]
            if dominant_count / len(risk_priorities) >= 0.8:
                warnings.append(
                    radar_issue(
                        "risk_priority_saturation",
                        f"{dominant_priority}={dominant_count}/{len(risk_priorities)}; verify that the final labels create a useful execution order",
                    )
                )

    if benchmark:
        benchmark_id = benchmark.get("id", "unknown")
        required_profiles = set(benchmark.get("required_profiles", []))
        for profile in sorted(required_profiles - profiles):
            errors.append(radar_issue("benchmark_missing_profile", f"{benchmark_id}:{profile}"))
        applicable_dimensions = {dimension for dimension, status in dimension_status.items() if status == "applicable"}
        for dimension in sorted(set(benchmark.get("required_dimensions", [])) - applicable_dimensions):
            errors.append(radar_issue("benchmark_missing_dimension", f"{benchmark_id}:{dimension}"))
        bug_levels = {str(item.get("bug_id")): item.get("level") for item in evidence.values()}
        for bug_id in benchmark.get("required_bug_ids", []):
            if str(bug_id) not in bug_levels:
                errors.append(radar_issue("benchmark_missing_bug", f"{benchmark_id}:{bug_id}"))
        for bug_id in benchmark.get("forbidden_direct_bug_ids", []):
            if bug_levels.get(str(bug_id)) == "direct":
                errors.append(radar_issue("benchmark_forbidden_direct", f"{benchmark_id}:{bug_id}"))
        impact_text = normalize_text(" ".join(str(item.get("label", "")) for item in impacts.values()))
        for term in benchmark.get("required_impact_terms", []):
            if normalize_text(str(term)) not in impact_text:
                errors.append(radar_issue("benchmark_missing_impact", f"{benchmark_id}:{term}"))

    return errors, warnings


def print_radar_validation(errors: list[str], warnings: list[str]) -> None:
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- ERROR {error}")
    else:
        print("PASS")
    for warning in warnings:
        print(f"- WARNING {warning}")


def cmd_radar_check(args: argparse.Namespace) -> None:
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    draft = Path(args.draft).read_text(encoding="utf-8") if args.draft else None
    benchmark = None
    if args.benchmark:
        benchmark = load_radar_benchmarks().get(args.benchmark)
        if benchmark is None:
            raise SystemExit(f"Unknown radar benchmark: {args.benchmark}")
    errors, warnings = validate_radar_plan(plan, draft=draft, benchmark=benchmark)
    print_radar_validation(errors, warnings)
    if errors:
        raise SystemExit(1)


def cmd_radar_eval(args: argparse.Namespace) -> None:
    if not RADAR_EVAL_PLAN_FILE.exists():
        raise SystemExit(f"Missing radar eval plan: {RADAR_EVAL_PLAN_FILE}")
    base_plan = json.loads(RADAR_EVAL_PLAN_FILE.read_text(encoding="utf-8"))
    failures: list[str] = []

    errors, _ = validate_radar_plan(base_plan, draft="端口占用兜底 进程与端口释放")
    if errors:
        failures.append(f"valid plan failed: {'; '.join(errors)}")

    remote_plan = copy.deepcopy(base_plan)
    remote_plan["version"] = 4
    remote_plan["remote_knowledge"] = {
        "status": "queried",
        "reason": "evaluate remote evidence admission rules",
        "queries": ["客户端底层能力兜底"],
        "read_refs": [
            "viking://resources/testcases/independent-port-fallback",
            "viking://resources/testcases/current-port-requirement",
        ],
    }
    remote_plan["evidence"][0].update(
        {
            "source_type": "feishu_bug",
            "evidence_role": "risk_history",
            "source_ref": "feishu://bug/TEST-001",
            "source_updated_at": "2026-08-01",
            "applicability_status": "matched",
        }
    )
    remote_plan["evidence"].extend(
        [
            {
                "id": "E2",
                "source_type": "openviking_testcase",
                "evidence_role": "regression_hint",
                "source_ref": "viking://resources/testcases/independent-port-fallback",
                "title": "历史端口占用后的兜底场景",
                "level": "strong_related",
                "same_object": True,
                "same_entry_or_chain": True,
                "version_scope": "current",
                "source_updated_at": "2026-07-20",
                "applicability_status": "matched",
                "applicability_reason": "独立历史用例覆盖同一兜底场景",
                "bridge": {
                    "kind": "same_execution_point",
                    "status": "confirmed",
                    "description": "历史用例与当前需求都覆盖同一本地端口兜底执行点",
                    "current_trigger": "默认端口被占用后触发候选端口分配",
                },
                "provenance_relation": "independent_history",
                "admission_status": "selected",
                "claim_boundary": "只证明端口占用后存在可用兜底路径，不证明具体分配算法、日志粒度或重试次数",
            },
            {
                "id": "E3",
                "source_type": "openviking_testcase",
                "evidence_role": "regression_hint",
                "source_ref": "viking://resources/testcases/current-port-requirement",
                "title": "当前需求生成的端口兜底用例",
                "level": "direct",
                "same_object": True,
                "same_entry_or_chain": True,
                "version_scope": "current",
                "source_updated_at": "2026-08-20",
                "applicability_status": "matched",
                "applicability_reason": "仅用于核对当前需求覆盖范围",
                "provenance_relation": "same_requirement",
                "admission_status": "scope_audit_only",
                "claim_boundary": "来自当前同一需求，只能核对需求覆盖，不能证明历史复发风险或提升结论",
            },
        ]
    )
    remote_plan["coverage_obligations"] = [
        {
            "id": "O1",
            "failure_mechanism": "默认本地能力失败后调用链没有切换到可用兜底路径",
            "trigger_conditions": ["默认端口被占用", "启动客户端底层能力"],
            "required_assertion": "调用方取得可用路径且后续运行不被阻塞",
            "priority": "high",
            "source_ids": ["E1", "E2"],
        }
    ]
    remote_plan["risks"][0]["source_ids"].append("E2")
    remote_plan["risks"][0]["coverage_obligation_ids"] = ["O1"]
    remote_plan["risks"][1]["coverage_obligation_ids"] = []
    remote_plan["risks"][0]["assertions"] = [
        {
            "id": "A1",
            "text": "历史 Bug 证明默认能力失败后需要切换到可用兜底路径",
            "basis": "historical",
            "certainty": "confirmed",
            "source_ids": ["E1"],
            "render_anchor": "调用方切换到可用路径",
        },
        {
            "id": "A2",
            "text": "独立历史用例补充了端口占用后的兜底场景",
            "basis": "historical_testcase",
            "certainty": "confirmed",
            "source_ids": ["E2"],
            "render_anchor": "历史用例补充端口占用兜底",
        }
    ]
    remote_plan["risks"][1]["assertions"] = [
        {
            "id": "A3",
            "text": "按实际资源所有者验证退出后的资源释放",
            "basis": "requirement",
            "certainty": "conditional",
            "condition": "资源所有者和释放边界确认后执行",
            "condition_render_anchor": "按实际资源所有者确认后",
            "source_ids": [],
            "render_anchor": "旧资源不阻塞下一次运行",
        }
    ]
    valid_remote_draft = "端口占用兜底 调用方切换到可用路径 历史用例补充端口占用兜底 进程与端口释放 按实际资源所有者确认后 旧资源不阻塞下一次运行"
    errors, _ = validate_radar_plan(remote_plan, draft=valid_remote_draft)
    if errors:
        failures.append(f"valid remote plan failed: {'; '.join(errors)}")

    testcase_review_plan = copy.deepcopy(remote_plan)
    testcase_review_plan["version"] = 5
    testcase_review_plan["historical_testcase_review"] = {
        "status": "queried",
        "reason": "evaluate historical testcase candidates before radar handoff",
        "queries": ["本地端口 占用 兜底 历史用例"],
        "candidates": [
            {
                "candidate_id": "TC-ZINIAO-PORT-FALLBACK",
                "source_ref": "viking://resources/testcases/independent-port-fallback",
                "title": "历史端口占用后的兜底场景",
                "decision": "selected",
                "reason": "same execution point and observable fallback result",
                "evidence_id": "E2",
                "risk_ids": ["R1"],
            }
        ],
    }
    errors, _ = validate_radar_plan(testcase_review_plan, draft=valid_remote_draft)
    if errors:
        failures.append(f"valid testcase-review plan failed: {'; '.join(errors)}")

    missing_testcase_review = copy.deepcopy(testcase_review_plan)
    missing_testcase_review.pop("historical_testcase_review")
    errors, _ = validate_radar_plan(missing_testcase_review, draft=valid_remote_draft)
    if not any(error.startswith("invalid_historical_testcase_review:") for error in errors):
        failures.append(f"missing testcase review: expected invalid_historical_testcase_review, got {errors}")

    no_candidate_testcase_review = copy.deepcopy(testcase_review_plan)
    no_candidate_testcase_review["historical_testcase_review"]["candidates"] = []
    errors, _ = validate_radar_plan(no_candidate_testcase_review, draft=valid_remote_draft)
    if not any(error.startswith("historical_testcase_queried_without_candidates:") for error in errors):
        failures.append(f"empty testcase review: expected queried_without_candidates, got {errors}")

    untraced_testcase_review = copy.deepcopy(testcase_review_plan)
    untraced_testcase_review["historical_testcase_review"]["candidates"][0]["risk_ids"] = ["R2"]
    errors, _ = validate_radar_plan(untraced_testcase_review, draft=valid_remote_draft)
    if not any(error.startswith("historical_testcase_influence_not_traced:") for error in errors):
        failures.append(f"untraced testcase influence: expected influence_not_traced, got {errors}")

    valid_cross_object_bridge = copy.deepcopy(remote_plan)
    valid_cross_object_bridge["evidence"][1]["same_object"] = False
    valid_cross_object_bridge["evidence"][1]["same_entry_or_chain"] = False
    valid_cross_object_bridge["evidence"][1]["bridge"] = {
        "kind": "shared_component",
        "status": "confirmed",
        "description": "两个入口复用同一本地端口分配组件",
        "current_trigger": "当前入口调用该共享分配组件",
    }
    errors, _ = validate_radar_plan(valid_cross_object_bridge, draft=valid_remote_draft)
    if errors:
        failures.append(f"valid cross-object bridge failed: {'; '.join(errors)}")

    split_obligation_plan = copy.deepcopy(remote_plan)
    split_obligation_plan["risks"][1]["source_ids"] = ["E1", "E2"]
    split_obligation_plan["risks"][1]["coverage_obligation_ids"] = ["O1"]
    split_obligation_plan["risks"][1]["assertions"].extend(
        [
            {
                "id": "A4",
                "text": "同一历史故障机制被放入第二个可见风险",
                "basis": "historical",
                "certainty": "confirmed",
                "source_ids": ["E1"],
                "render_anchor": "同一故障义务第二处",
            },
            {
                "id": "A5",
                "text": "同一历史用例也被放入第二个可见风险",
                "basis": "historical_testcase",
                "certainty": "confirmed",
                "source_ids": ["E2"],
                "render_anchor": "同一历史用例第二处",
            },
        ]
    )
    split_obligation_draft = """## 运行兜底
### 默认能力失败
端口占用兜底 调用方切换到可用路径 历史用例补充端口占用兜底
### 资源释放
进程与端口释放 按实际资源所有者确认后 旧资源不阻塞下一次运行 同一故障义务第二处 同一历史用例第二处
"""
    errors, warnings = validate_radar_plan(split_obligation_plan, draft=split_obligation_draft)
    if errors:
        failures.append(f"split obligation warning fixture failed validation: {'; '.join(errors)}")
    if not any(warning.startswith("obligation_split_across_sections:") for warning in warnings):
        failures.append(f"split obligation warning fixture: expected obligation_split_across_sections, got {warnings}")

    priority_saturation_plan = copy.deepcopy(base_plan)
    for risk_id, anchor in [("R3", "第三个高优先级风险"), ("R4", "第四个高优先级风险")]:
        extra_risk = copy.deepcopy(priority_saturation_plan["risks"][0])
        extra_risk["id"] = risk_id
        extra_risk["title"] = anchor
        extra_risk["render_anchor"] = anchor
        priority_saturation_plan["risks"].append(extra_risk)
    saturation_draft = "端口占用兜底 进程与端口释放 第三个高优先级风险 第四个高优先级风险"
    errors, warnings = validate_radar_plan(priority_saturation_plan, draft=saturation_draft)
    if errors:
        failures.append(f"priority saturation warning fixture failed validation: {'; '.join(errors)}")
    if not any(warning.startswith("risk_priority_saturation:") for warning in warnings):
        failures.append(f"priority saturation warning fixture: expected risk_priority_saturation, got {warnings}")

    compatible_v3_plan = copy.deepcopy(remote_plan)
    compatible_v3_plan["version"] = 3
    for item in compatible_v3_plan["risks"]:
        item.pop("assertions", None)
    errors, _ = validate_radar_plan(compatible_v3_plan, draft="端口占用兜底 进程与端口释放")
    if errors:
        failures.append(f"compatible version 3 plan failed: {'; '.join(errors)}")

    mutations = []
    uncovered = copy.deepcopy(base_plan)
    uncovered["risks"][0]["impact_ids"] = []
    mutations.append(("uncovered-impact", uncovered, None, "impact_uncovered"))

    invalid_direct = copy.deepcopy(base_plan)
    invalid_direct["evidence"][0]["same_object"] = False
    mutations.append(("invalid-direct", invalid_direct, None, "invalid_direct_evidence"))

    missing_strong_bridge = copy.deepcopy(remote_plan)
    missing_strong_bridge["evidence"][1].pop("bridge", None)
    mutations.append(
        (
            "missing-strong-related-bridge",
            missing_strong_bridge,
            None,
            "missing_strong_related_bridge",
        )
    )

    unknown_strong_bridge = copy.deepcopy(remote_plan)
    unknown_strong_bridge["evidence"][1]["bridge"]["status"] = "unknown"
    mutations.append(
        (
            "unknown-strong-related-bridge",
            unknown_strong_bridge,
            None,
            "strong_related_bridge_not_confirmed",
        )
    )

    unmatched_strong_evidence = copy.deepcopy(remote_plan)
    unmatched_strong_evidence["evidence"][1]["applicability_status"] = "unknown"
    mutations.append(
        (
            "unmatched-strong-related-evidence",
            unmatched_strong_evidence,
            None,
            "strong_related_applicability_not_matched",
        )
    )

    invalid_execution_bridge = copy.deepcopy(remote_plan)
    invalid_execution_bridge["evidence"][1]["same_entry_or_chain"] = False
    mutations.append(
        (
            "same-execution-bridge-without-same-chain",
            invalid_execution_bridge,
            None,
            "same_execution_bridge_without_same_chain",
        )
    )

    legacy_direct = copy.deepcopy(base_plan)
    legacy_direct["evidence"][0]["version_scope"] = "legacy"
    mutations.append(("legacy-direct", legacy_direct, None, "legacy_direct_evidence"))

    missing_dimension = copy.deepcopy(base_plan)
    for row in missing_dimension["dimension_applicability"]:
        if row["dimension"] == "permission_scope":
            row["status"] = "applicable"
            row["reason"] = "evaluation mutation"
    mutations.append(("applicable-dimension-without-risk", missing_dimension, None, "applicable_dimension_without_risk"))

    missing_profile_core = copy.deepcopy(base_plan)
    for row in missing_profile_core["dimension_applicability"]:
        if row["dimension"] == "runtime_chain":
            row["status"] = "not_applicable"
            row["reason"] = "evaluation mutation"
    mutations.append(("profile-core-dimension", missing_profile_core, None, "profile_core_dimension_not_applicable"))

    mutations.append(("draft-missing-risk", base_plan, "端口占用兜底", "draft_missing_risk"))

    uncovered_constraint = copy.deepcopy(base_plan)
    uncovered_constraint["risks"][0]["constraint_ids"] = []
    mutations.append(("uncovered-constraint", uncovered_constraint, None, "constraint_uncovered"))

    unknown_scope_unconditional = copy.deepcopy(base_plan)
    unknown_scope_unconditional["risks"][1]["certainty"] = "confirmed"
    unknown_scope_unconditional["risks"][1].pop("condition", None)
    mutations.append(("unknown-scope-unconditional", unknown_scope_unconditional, None, "unknown_scope_risk_not_conditional"))

    conflict_unconditional = copy.deepcopy(base_plan)
    conflict_unconditional["impact_inventory"][1]["source_status"] = "conflicted"
    conflict_unconditional["requirement_conflicts"] = [
        {
            "id": "Q1",
            "label": "资源释放时点冲突",
            "reason": "两个需求段落给出不同释放时点",
            "impact_ids": ["I2"],
            "risk_ids": ["R2"],
        }
    ]
    conflict_unconditional["risks"][1]["certainty"] = "confirmed"
    conflict_unconditional["risks"][1].pop("condition", None)
    mutations.append(("conflict-unconditional", conflict_unconditional, None, "conflict_risk_not_conditional"))

    same_requirement_selected = copy.deepcopy(remote_plan)
    same_requirement_selected["evidence"][2]["admission_status"] = "selected"
    mutations.append(("same-requirement-selected", same_requirement_selected, None, "same_requirement_selected"))

    same_requirement_used = copy.deepcopy(remote_plan)
    same_requirement_used["risks"][0]["source_ids"].append("E3")
    mutations.append(("same-requirement-used", same_requirement_used, None, "non_selected_remote_evidence_used"))

    unknown_provenance_unconditional = copy.deepcopy(remote_plan)
    unknown_provenance_unconditional["evidence"][1]["provenance_relation"] = "unknown"
    mutations.append(
        (
            "unknown-provenance-unconditional",
            unknown_provenance_unconditional,
            None,
            "unknown_provenance_requires_condition",
        )
    )

    missing_claim_boundary = copy.deepcopy(remote_plan)
    missing_claim_boundary["evidence"][1].pop("claim_boundary", None)
    mutations.append(("missing-claim-boundary", missing_claim_boundary, None, "missing_claim_boundary"))

    non_selected_remote_used = copy.deepcopy(remote_plan)
    non_selected_remote_used["evidence"][1]["admission_status"] = "scope_audit_only"
    mutations.append(("non-selected-remote-used", non_selected_remote_used, None, "non_selected_remote_evidence_used"))

    missing_obligation_mapping = copy.deepcopy(remote_plan)
    missing_obligation_mapping["risks"][0]["coverage_obligation_ids"] = []
    mutations.append(
        (
            "missing-obligation-mapping",
            missing_obligation_mapping,
            None,
            "historical_risk_without_obligation",
        )
    )

    weak_obligation_source = copy.deepcopy(remote_plan)
    weak_obligation_source["evidence"][1]["level"] = "adjacent"
    mutations.append(("weak-obligation-source", weak_obligation_source, None, "weak_obligation_source"))

    obligation_source_not_in_risk = copy.deepcopy(remote_plan)
    obligation_source_not_in_risk["risks"][0]["source_ids"].remove("E2")
    mutations.append(
        (
            "obligation-source-not-in-risk",
            obligation_source_not_in_risk,
            None,
            "obligation_sources_not_in_risk",
        )
    )

    missing_assertions = copy.deepcopy(remote_plan)
    missing_assertions["risks"][0].pop("assertions", None)
    mutations.append(("missing-assertions", missing_assertions, None, "missing_assertions"))

    assertion_without_evidence = copy.deepcopy(remote_plan)
    assertion_without_evidence["risks"][0]["assertions"][0]["source_ids"] = []
    mutations.append(
        ("assertion-without-evidence", assertion_without_evidence, None, "assertion_without_evidence")
    )

    inference_assertion_has_evidence = copy.deepcopy(remote_plan)
    inference_assertion_has_evidence["risks"][0]["assertions"][0]["basis"] = "inference"
    mutations.append(
        (
            "inference-assertion-has-evidence",
            inference_assertion_has_evidence,
            None,
            "inference_assertion_has_evidence",
        )
    )

    conditional_assertion_without_condition = copy.deepcopy(remote_plan)
    conditional_assertion_without_condition["risks"][1]["assertions"][0].pop("condition", None)
    mutations.append(
        (
            "conditional-assertion-without-condition",
            conditional_assertion_without_condition,
            None,
            "conditional_assertion_without_condition",
        )
    )

    conditional_assertion_without_render_anchor = copy.deepcopy(remote_plan)
    conditional_assertion_without_render_anchor["risks"][1]["assertions"][0].pop(
        "condition_render_anchor", None
    )
    mutations.append(
        (
            "conditional-assertion-without-render-anchor",
            conditional_assertion_without_render_anchor,
            None,
            "conditional_assertion_without_render_anchor",
        )
    )

    conditional_risk_without_conditional_assertion = copy.deepcopy(remote_plan)
    conditional_risk_without_conditional_assertion["risks"][1]["assertions"][0]["certainty"] = "confirmed"
    conditional_risk_without_conditional_assertion["risks"][1]["assertions"][0].pop("condition", None)
    conditional_risk_without_conditional_assertion["risks"][1]["assertions"][0].pop(
        "condition_render_anchor", None
    )
    mutations.append(
        (
            "conditional-risk-without-conditional-assertion",
            conditional_risk_without_conditional_assertion,
            None,
            "conditional_risk_without_conditional_assertion",
        )
    )

    assertion_basis_role_mismatch = copy.deepcopy(remote_plan)
    assertion_basis_role_mismatch["risks"][0]["assertions"][1]["basis"] = "historical"
    mutations.append(
        (
            "assertion-basis-role-mismatch",
            assertion_basis_role_mismatch,
            None,
            "assertion_basis_evidence_role_mismatch",
        )
    )

    requirement_assertion_has_evidence = copy.deepcopy(remote_plan)
    requirement_assertion_has_evidence["risks"][1]["source_ids"] = ["E1"]
    requirement_assertion_has_evidence["risks"][1]["assertions"][0]["source_ids"] = ["E1"]
    mutations.append(
        (
            "requirement-assertion-has-evidence",
            requirement_assertion_has_evidence,
            None,
            "requirement_assertion_has_evidence",
        )
    )

    risk_basis_not_in_assertions = copy.deepcopy(remote_plan)
    risk_basis_not_in_assertions["risks"][1]["basis"] = "inference"
    mutations.append(
        (
            "risk-basis-not-in-assertions",
            risk_basis_not_in_assertions,
            None,
            "risk_basis_not_in_assertions",
        )
    )

    assertion_source_not_in_risk = copy.deepcopy(remote_plan)
    assertion_source_not_in_risk["risks"][0]["source_ids"].remove("E2")
    mutations.append(
        (
            "assertion-source-not-in-risk",
            assertion_source_not_in_risk,
            None,
            "assertion_source_not_in_risk",
        )
    )

    duplicate_assertion_anchor = copy.deepcopy(remote_plan)
    duplicate_assertion_anchor["risks"][1]["assertions"].append(
        {
            "id": "A3",
            "text": "另一条独立的需求推导",
            "basis": "requirement",
            "certainty": "confirmed",
            "source_ids": [],
            "render_anchor": "旧资源不阻塞下一次运行",
        }
    )
    mutations.append(
        (
            "duplicate-assertion-anchor",
            duplicate_assertion_anchor,
            None,
            "duplicate_assertion_render_anchor",
        )
    )

    mutations.append(
        (
            "draft-missing-assertion",
            remote_plan,
            "端口占用兜底 进程与端口释放",
            "draft_missing_assertion",
        )
    )

    mutations.append(
        (
            "draft-missing-assertion-condition",
            remote_plan,
            "端口占用兜底 调用方切换到可用路径 历史用例补充端口占用兜底 进程与端口释放 旧资源不阻塞下一次运行",
            "draft_missing_assertion_condition",
        )
    )

    mutations.append(
        (
            "draft-generation-process-wording",
            remote_plan,
            f"{valid_remote_draft} 新增直接历史 Bug",
            "draft_generation_process_wording",
        )
    )

    for name, plan, draft, expected_code in mutations:
        errors, _ = validate_radar_plan(plan, draft=draft)
        if not any(error.startswith(f"{expected_code}:") for error in errors):
            failures.append(f"{name}: expected {expected_code}, got {errors}")

    benchmarks = load_radar_benchmarks()
    bug_rows = load_jsonl(NORMALIZED_BUGS_FILE) if NORMALIZED_BUGS_FILE.exists() else []
    for benchmark_id, case in benchmarks.items():
        found_ids: set[str] = set()
        for query_spec in case.get("queries", []):
            if isinstance(query_spec, dict):
                query = str(query_spec.get("text", ""))
                query_required_ids = [str(value) for value in query_spec.get("required_bug_ids", [])]
            else:
                query = str(query_spec)
                query_required_ids = []
            ranked = []
            for row in bug_rows:
                score, reasons = score_bug_detail(row, query)
                if score >= 20:
                    ranked.append((score, row, reasons))
            ranked.sort(key=ranked_bug_sort_key)
            all_query_ids = [str(row.get("id")) for _, row, _ in ranked[: args.limit]]
            found_ids.update(all_query_ids)
            max_rank = int(query_spec.get("max_rank", args.limit)) if isinstance(query_spec, dict) else args.limit
            precision_ids = all_query_ids[:max_rank]
            query_missing = [bug_id for bug_id in query_required_ids if bug_id not in precision_ids]
            if query_missing:
                failures.append(f"{benchmark_id}: query '{query}' missing {', '.join(query_missing)} within top {max_rank}")
        missing = [str(bug_id) for bug_id in case.get("required_bug_ids", []) if str(bug_id) not in found_ids]
        print(f"RADAR BENCHMARK: {benchmark_id} [{case.get('group', 'unknown')}]")
        print(f"  found: {', '.join(sorted(found_ids))}")
        if missing:
            failures.append(f"{benchmark_id}: missing recall evidence {', '.join(missing)}")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nPASS")


EVAL_CASES = [
    {
        "query": "我要测书签相关的",
        "must_first": "ZN-LM-BOOKMARK-DIRECT-001",
        "must_include": ["ZN-LM-BOOKMARK-DIRECT-001"],
        "must_not_include": ["ZN-FEISHU-CLUSTER-OTHER-HIGH-FREQ"],
    },
    {
        "query": "我要测账号列表",
        "must_include": ["ZN-LM-ADMIN-LIST-FILTER-EXPORT-001", "ZN-FEISHU-CLUSTER-ACCOUNT-AUTH"],
    },
    {
        "query": "我要测客户端资源包升级",
        "must_include": ["ZN-LM-CLIENT-UPGRADE-RESOURCE-001", "ZN-FEISHU-CLUSTER-CLIENT-RESOURCE-UPGRADE"],
    },
    {
        "query": "我要测新内核",
        "must_include": ["ZN-LM-KERNEL-HEADLESS-001", "ZN-LM-CLIENT-DEVTOOLS-KERNEL-001"],
    },
    {
        "query": "我要测事中监管",
        "must_include": ["ZN-LM-SECURITY-SUPERVISION-001", "ZN-FEISHU-CLUSTER-SECURITY-SUPERVISION"],
    },
]


DETAIL_EVAL_CASES = [
    {
        "query": "编辑账号",
        "must_include": ["7000646298", "7000742305", "7006444075"],
    },
    {
        "query": "云号的购买",
        "must_include": ["7056385834"],
    },
    {
        "query": "首页 账号动态",
        "must_include": ["6987643227"],
    },
    {
        "query": "首页 账户余额",
        "must_include": ["6837952696", "7042820490"],
        "must_include_within": 5,
    },
    {
        "query": "账号 复制账号",
        "must_include": ["7048013238"],
    },
    {
        "query": "账号 共享账号",
        "must_include": ["6828314272", "7004858499"],
    },
    {
        "query": "设备 设备回收站",
        "must_include": ["7056233504", "7024468557"],
    },
    {
        "query": "设备 自定义视图",
        "must_include": ["7020981779", "7004776884"],
    },
    {
        "query": "云号 黑名单管理",
        "must_include": ["6993900715", "6993804185"],
        "must_include_within": 3,
    },
    {
        "query": "管理 添加成员",
        "must_include": ["6894008782"],
    },
    {
        "query": "管理 部门管理",
        "must_include": ["6849737071", "7067557986"],
    },
    {
        "query": "安全 添加监管账号",
        "must_include": ["6995479452"],
    },
    {
        "query": "账号菜单 急需续费列表",
        "must_include": ["6913372508", "7000929026"],
    },
    {
        "query": "账号列表 授权成员",
        "must_include": ["7006444075", "7054669387", "6925323396"],
        "must_include_within": 8,
    },
    {
        "query": "授权成员 账号列表查看 权限 通知",
        "must_include": ["6925323396"],
        "must_include_within": 5,
    },
    {
        "query": "授权成员弹窗 搜索 CPU 页面卡顿",
        "must_include": ["6956970539"],
    },
    {
        "query": "缓存管理 文件下载路径冲突",
        "must_include": ["7053017623", "6948519315", "6930524928"],
    },
    {
        "query": "本地端口 端口分配兜底",
        "must_include": ["7074871545"],
    },
    {
        "query": "多开工作台 打开店铺 进程残留",
        "must_include": ["7060791962"],
    },
]


SCENARIO_EVAL_CASES = [
    {
        "query": "缓存管理 文件下载路径冲突",
        "must_first": "缓存路径设置",
        "must_include_bug_ids": ["7053017623", "6948519315", "6930524928"],
    },
    {
        "query": "账号菜单 急需续费列表",
        "must_first": "急需续费列表",
        "must_include_bug_ids": ["6913372508", "7000929026"],
    },
    {
        "query": "账号 复制账号",
        "must_first": "复制账号",
        "must_include_bug_ids": ["7048013238", "7063536518"],
    },
    {
        "query": "账号 共享账号",
        "must_first": "共享账号",
        "must_include_bug_ids": ["6828314272", "7004858499"],
    },
    {
        "query": "v5.290.61 账号支持按成员或部门或角色授权",
        "must_first": "账号授权",
        "must_include_bug_ids": ["7006444075", "7054669387", "6925323396", "6956970539"],
    },
    {
        "query": "云号的购买",
        "must_first": "云号购买",
        "must_include_bug_ids": ["7056385834"],
    },
    {
        "query": "设备 自定义视图",
        "must_first": "自定义视图",
        "must_include_bug_ids": ["7020981779", "7004776884"],
    },
    {
        "query": "管理 添加成员",
        "must_first": "添加成员",
        "must_include_bug_ids": ["6894008782"],
    },
    {
        "query": "安全 添加监管账号",
        "must_first": "添加监管账号",
        "must_include_bug_ids": ["6995479452"],
    },
    {
        "query": "打开店铺 IP检测 代理 cookie",
        "must_first": "打开店铺链路",
    },
    {
        "query": "本地端口 端口分配兜底",
        "must_first": "本地端口",
    },
    {
        "query": "多开工作台 打开店铺",
        "must_first": "多开工作台",
    },
]


def cmd_eval(args: argparse.Namespace) -> None:
    failures = []
    reference_time = datetime(2026, 8, 24, tzinfo=timezone.utc)
    recency_cases = [
        ("2026-02-24T00:00:00+00:00", 20, "recent_182_days"),
        ("2026-02-23T00:00:00+00:00", 5, "age_182_364_days"),
        ("2025-08-25T00:00:00+00:00", 5, "age_182_364_days"),
        ("2025-08-24T00:00:00+00:00", -5, "age_365_plus_days"),
        ("", 0, "age_unknown"),
    ]
    for created_at, expected_score, expected_reason in recency_cases:
        actual_score, actual_reason = bug_recency_adjustment(
            {"created_at": created_at},
            reference_time=reference_time,
        )
        if (actual_score, actual_reason) != (expected_score, expected_reason):
            failures.append(
                "recency boundary "
                f"{created_at or 'missing'}: expected {(expected_score, expected_reason)}, "
                f"got {(actual_score, actual_reason)}"
            )
    for case in EVAL_CASES:
        ranked = rank_landmines(case["query"], args.limit)
        ids = [item.get("id") for _, item, _ in ranked]
        first_id = ids[0] if ids else None
        print(f"CASE: {case['query']}")
        print(f"  top: {', '.join(ids[:5])}")
        if case.get("must_first") and first_id != case["must_first"]:
            failures.append(f"{case['query']}: expected first {case['must_first']}, got {first_id}")
        for expected in case.get("must_include", []):
            if expected not in ids:
                failures.append(f"{case['query']}: missing {expected}")
        for unexpected in case.get("must_not_include", []):
            if unexpected in ids:
                failures.append(f"{case['query']}: unexpected {unexpected}")

    if NORMALIZED_BUGS_FILE.exists():
        normalized_rows = load_jsonl(NORMALIZED_BUGS_FILE)
        actual_current = {
            str(row.get("id")) for row in normalized_rows if "current_182d" in row.get("view_memberships", [])
        }
        actual_historical = {
            str(row.get("id")) for row in normalized_rows if "historical_view" in row.get("view_memberships", [])
        }
        if CURRENT_VIEW_SNAPSHOT.exists() and HISTORICAL_VIEW_SNAPSHOT.exists():
            membership_index = build_view_membership_index()
            expected_current = {
                item_id
                for item_id, value in membership_index.items()
                if "current_182d" in value["view_memberships"]
            }
            expected_historical = {
                item_id
                for item_id, value in membership_index.items()
                if "historical_view" in value["view_memberships"]
            }
            if actual_current != expected_current:
                failures.append(
                    f"view membership current_182d mismatch: expected {len(expected_current)}, got {len(actual_current)}"
                )
            if actual_historical != expected_historical:
                failures.append(
                    "view membership historical_view mismatch: "
                    f"expected {len(expected_historical)}, got {len(actual_historical)}"
                )
        else:
            allowed_memberships = {"current_182d", "historical_view"}
            for row in normalized_rows:
                memberships = row.get("view_memberships")
                source_view_ids = row.get("source_view_ids")
                if not isinstance(memberships, list) or not isinstance(source_view_ids, list):
                    failures.append(f"normalized Bug {row.get('id')} has invalid view membership fields")
                    break
                if set(memberships) - allowed_memberships:
                    failures.append(f"normalized Bug {row.get('id')} has unknown view membership")
                    break
        if len({str(row.get('id')) for row in normalized_rows}) != len(normalized_rows):
            failures.append("normalized Bug archive contains duplicate IDs")
        for case in DETAIL_EVAL_CASES:
            ranked = []
            for row in load_jsonl(NORMALIZED_BUGS_FILE):
                score, reasons = score_bug_detail(row, case["query"])
                if score >= 20:
                    ranked.append((score, row, reasons))
            ranked.sort(key=ranked_bug_sort_key)
            ids = [row.get("id") for _, row, _ in ranked[: args.limit]]
            print(f"DETAIL CASE: {case['query']}")
            print(f"  top: {', '.join(ids[:5])}")
            first_id = ids[0] if ids else None
            if case.get("must_first") and first_id != case["must_first"]:
                failures.append(f"{case['query']}: expected first detail {case['must_first']}, got {first_id}")
            for expected in case.get("must_include", []):
                if expected not in ids:
                    failures.append(f"{case['query']}: missing detail {expected}")
            must_include_within = case.get("must_include_within")
            if must_include_within:
                precision_ids = ids[: int(must_include_within)]
                for expected in case.get("must_include", []):
                    if expected not in precision_ids:
                        failures.append(
                            f"{case['query']}: detail {expected} not within top {must_include_within}"
                        )
            for unexpected in case.get("must_not_include", []):
                if unexpected in ids:
                    failures.append(f"{case['query']}: unexpected detail {unexpected}")

    if SCENARIO_INDEX_FILE.exists():
        for case in SCENARIO_EVAL_CASES:
            ranked = rank_scenarios(case["query"], args.limit)
            names = [item.get("scenario") for _, item, _ in ranked]
            print(f"SCENARIO CASE: {case['query']}")
            print(f"  top: {', '.join(names[:5])}")
            first_name = names[0] if names else None
            if case.get("must_first") and first_name != case["must_first"]:
                failures.append(f"{case['query']}: expected first scenario {case['must_first']}, got {first_name}")
            top_ids = set()
            for _, item, _ in ranked[:3]:
                top_ids.update(str(bug_id) for bug_id in item.get("bug_ids", []))
            for expected in case.get("must_include_bug_ids", []):
                if expected not in top_ids:
                    failures.append(f"{case['query']}: scenario missing bug evidence {expected}")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nPASS")


def cmd_summary(args: argparse.Namespace) -> None:
    items = load_landmines()
    by_category = Counter(item.get("category", "unknown") for item in items)
    by_module = Counter(item.get("module", "unknown") for item in items)
    by_source = Counter(item.get("source", "unknown") for item in items)

    print(f"Total landmines: {len(items)}")
    print("\nBy source:")
    for key, count in by_source.most_common():
        print(f"  {key}: {count}")
    print("\nBy category:")
    for key, count in by_category.most_common(args.limit):
        print(f"  {key}: {count}")
    print("\nBy module:")
    for key, count in by_module.most_common(args.limit):
        print(f"  {key}: {count}")


def cmd_add(args: argparse.Namespace) -> None:
    raw = Path(args.json_file).read_text(encoding="utf-8") if args.json_file else input()
    item = json.loads(raw)
    required = ["id", "source", "domain", "module", "category", "scene", "risk", "must_check", "keywords", "evidence", "confidence"]
    missing = [key for key in required if key not in item]
    if missing:
        raise SystemExit(f"Missing required fields: {', '.join(missing)}")
    with DATA_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Added {item['id']} to {DATA_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search and maintain the Ziniao landmine map.")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search landmines by module, feature, or keyword.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--explain", action="store_true", help="Show scoring reasons.")
    search.set_defaults(func=cmd_search)

    recall = sub.add_parser("recall", help="Recall landmines grouped by evidence level.")
    recall.add_argument("query")
    recall.add_argument("--limit", type=int, default=12)
    recall.add_argument("--group-limit", type=int, default=3)
    recall.add_argument("--check-limit", type=int, default=5)
    recall.add_argument("--evidence-limit", type=int, default=4)
    recall.add_argument("--explain", action="store_true", help="Show source and scoring reasons.")
    recall.set_defaults(func=cmd_recall)

    eval_cmd = sub.add_parser("eval", help="Run recall quality regression checks.")
    eval_cmd.add_argument("--limit", type=int, default=8)
    eval_cmd.set_defaults(func=cmd_eval)

    radar_check = sub.add_parser("radar-check", help="Validate a structured radar plan and optional rendered draft.")
    radar_check.add_argument("plan", help="Path to the structured radar plan JSON.")
    radar_check.add_argument("--draft", help="Optional rendered Markdown draft whose risk anchors must match the plan.")
    radar_check.add_argument("--benchmark", help="Optional evaluation-only benchmark id.")
    radar_check.set_defaults(func=cmd_radar_check)

    radar_eval = sub.add_parser("radar-eval", help="Run generic radar-plan validator and cross-type recall regressions.")
    radar_eval.add_argument("--limit", type=int, default=20, help="Per-query Bug detail recall depth for benchmark evaluation.")
    radar_eval.set_defaults(func=cmd_radar_eval)

    summary = sub.add_parser("summary", help="Show local landmine counts.")
    summary.add_argument("--limit", type=int, default=12)
    summary.set_defaults(func=cmd_summary)

    add = sub.add_parser("add", help="Append one normalized JSON landmine.")
    add.add_argument("json_file", nargs="?")
    add.set_defaults(func=cmd_add)

    import_feishu = sub.add_parser("import-feishu", help="Read the configured Feishu online-defect view into local normalized JSON.")
    import_feishu.add_argument("--view-id", help="Feishu view ID. Defaults to the configured current-window view.")
    import_feishu.add_argument("--view-url", help="Feishu view URL. Defaults from --view-id or the configured current view.")
    import_feishu.add_argument("--output", help="Optional normalized JSON output path.")
    import_feishu.add_argument("--max-pages", type=int, default=0, help="Stop after this many pages; 0 means all pages.")
    import_feishu.add_argument("--sleep", type=float, default=0.2, help="Delay between Feishu pages.")
    import_feishu.add_argument("--save-pages", action="store_true", help="Also save raw paged MCP responses for debugging.")
    import_feishu.set_defaults(func=cmd_import_feishu)

    import_details = sub.add_parser("import-details", help="Fetch full Feishu defect detail fields into local JSONL.")
    import_details.add_argument("--source", help="Path to normalized Feishu view JSON. Defaults to the configured view import.")
    import_details.add_argument(
        "--current-source",
        help="Optional canonical current-window view JSON. Use it with a broader historical --source so old rows remain archived.",
    )
    import_details.add_argument("--limit", type=int, default=0, help="Only fetch the first N work items; 0 means all.")
    import_details.add_argument("--sleep", type=float, default=0.1, help="Delay between detail requests.")
    import_details.add_argument("--resume", action="store_true", help="Reuse rows already present in the long-term detail archive.")
    import_details.add_argument("--flush-each", action="store_true", help="Write progress after each fetched work item.")
    import_details.set_defaults(func=cmd_import_details)

    normalize_bugs = sub.add_parser("normalize-bugs", help="Convert Feishu detail JSONL into searchable normalized bug evidence.")
    normalize_bugs.add_argument("--source", help="Path to detail JSONL. Defaults to the long-term detail archive when present.")
    normalize_bugs.set_defaults(func=cmd_normalize_bugs)

    refresh_memberships = sub.add_parser(
        "refresh-view-memberships",
        help="Recompute current and historical view memberships in the long-term detail archive.",
    )
    refresh_memberships.add_argument("--source", help="Path to detail JSONL. Defaults to the long-term detail archive.")
    refresh_memberships.set_defaults(func=cmd_refresh_view_memberships)

    build_scenarios = sub.add_parser("build-scenarios", help="Build scenario candidates and a high-confidence scenario index from normalized Bugs.")
    build_scenarios.add_argument("--source", help="Path to normalized Bugs JSONL. Defaults to data/normalized_bugs.jsonl.")
    build_scenarios.set_defaults(func=cmd_build_scenarios)

    scenario_search = sub.add_parser("scenario-search", help="Search the high-confidence scenario index before reading individual Bugs.")
    scenario_search.add_argument("query")
    scenario_search.add_argument("--limit", type=int, default=5)
    scenario_search.add_argument("--min-score", type=int, default=45)
    scenario_search.add_argument("--explain", action="store_true", help="Show scoring reasons.")
    scenario_search.set_defaults(func=cmd_scenario_search)

    sanitize_details = sub.add_parser("sanitize-details", help="Re-clean imported Feishu detail JSONL in place.")
    sanitize_details.add_argument("--source", help="Path to detail JSONL. Defaults to the long-term detail archive when present.")
    sanitize_details.set_defaults(func=cmd_sanitize_details)

    bug_search = sub.add_parser("bug-search", help="Search normalized Feishu bug details by feature or keyword.")
    bug_search.add_argument("query")
    bug_search.add_argument("--limit", type=int, default=8)
    bug_search.add_argument("--min-score", type=int, default=20)
    bug_search.add_argument("--explain", action="store_true", help="Show scoring reasons.")
    bug_search.add_argument("--no-scenarios", action="store_true", help="Do not print scenario index hits before Bug details.")
    bug_search.set_defaults(func=cmd_bug_search)

    radar_search = sub.add_parser(
        "radar-search",
        help="Run one grouped recall and multiple Bug-detail queries in one process with shared read-only data.",
    )
    radar_search.add_argument("query", help="Primary requirement or feature query used for grouped recall.")
    radar_search.add_argument(
        "--related",
        action="append",
        default=[],
        help="Additional narrow Bug query. Repeat this option for multiple queries.",
    )
    radar_search.add_argument("--recall-limit", type=int, default=12)
    radar_search.add_argument("--group-limit", type=int, default=3)
    radar_search.add_argument("--check-limit", type=int, default=5)
    radar_search.add_argument("--evidence-limit", type=int, default=4)
    radar_search.add_argument("--bug-limit", type=int, default=8)
    radar_search.add_argument("--min-score", type=int, default=20)
    radar_search.add_argument("--no-scenarios", action="store_true")
    radar_search.add_argument("--explain", action="store_true", help="Show source and scoring reasons.")
    radar_search.set_defaults(func=cmd_radar_search)

    cluster_feishu = sub.add_parser("cluster-feishu", help="Cluster the normalized Feishu import into reusable testing landmines.")
    cluster_feishu.add_argument("--source", help="Path to normalized Feishu JSON. Defaults to the configured view import.")
    cluster_feishu.set_defaults(func=cmd_cluster_feishu)

    sync_clusters = sub.add_parser("sync-clusters", help="Convert Feishu clusters into generated search landmines.")
    sync_clusters.set_defaults(func=cmd_sync_clusters)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
