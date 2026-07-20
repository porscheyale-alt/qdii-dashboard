# -*- coding: utf-8 -*-
"""
QDII 净值看板 - 抓数脚本
读取 QDII产品表.xlsx 的全部基金代码，批量拉取天天基金每日净值，生成 data.json。
QDII 净值 T+1（部分 T+2）公布，本脚本抓取最近 N 个交易日净值。
"""
import os, re, json, time, urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
FUNDS = os.path.join(BASE, "funds.json")  # 基金列表（由 Excel 预先提取，云端可用）
OUT = os.path.join(BASE, "data.json")
HISTORY_DAYS = 30  # 每只基金抓取的历史净值条数
WORKERS = 8        # 并发线程数（多频次抓取需保证每次够快，同时不触发限速）

# 额度覆盖表：天天基金 SGZT 接口返回的额度文本与实际不符时，
# 用人工确认的真实状态覆盖（抓数后套用，每日自动跑数不被冲掉）。
# key=基金代码，value=覆盖后的额度文本。
QUOTA_OVERRIDE = {
    # 博时标普500联接 A/C：接口返回"暂停申购(单日投资上限100元)"但实际已完全暂停
    "050025": "暂停申购",
    "006075": "暂停申购",
    # 博时标普500联接 E：接口只返回"限大额"缺金额，实测单日限额100元
    "018738": "限大额(单日上限100元)",
}


def load_funds():
    """从仓库内 funds.json 读出 (code, name, group) 列表。
    funds.json 由本地 Excel 预先提取（gen_funds.py），使脚本不依赖本地文件，可在云端运行。"""
    with open(FUNDS, encoding="utf-8") as fp:
        return json.load(fp)


def fetch_nav(code):
    """拉取单只基金最近 HISTORY_DAYS 条净值。返回按日期升序的列表。"""
    url = (f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}"
           f"&pageIndex=1&pageSize={HISTORY_DAYS}")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://fundf10.eastmoney.com/jjjz_{code}.html",
    })
    r = urllib.request.urlopen(req, timeout=20)
    data = json.loads(r.read().decode())
    lst = data.get("Data", {}).get("LSJZList", []) or []
    out = []
    for x in lst:
        dwjz = x.get("DWJZ")
        if not dwjz:
            continue
        try:
            nav = float(dwjz)
        except ValueError:
            continue
        rate = x.get("JZZZL")
        try:
            rate = float(rate) if rate not in (None, "") else None
        except ValueError:
            rate = None
        out.append({"date": x.get("FSRQ"), "nav": nav, "rate": rate})
    out.reverse()  # 升序：老 -> 新
    return out


def fetch_quota(code):
    """拉取单只基金申购状态与限额。返回简短文本，如
    '开放申购' / '暂停申购' / '限大额(单日上限10元)'。失败返回 None。"""
    url = (f"https://fundmobapi.eastmoney.com/FundMApi/FundBaseTypeInformation.ashx"
           f"?FCODE={code}&deviceid=1&plat=Iphone&product=EFund&version=6.4.0")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://fund.eastmoney.com/",
    })
    try:
        r = urllib.request.urlopen(req, timeout=20)
        d = json.loads(r.read().decode())
        sgzt = (d.get("Datas") or {}).get("SGZT")
        return sgzt.strip() if sgzt else None
    except Exception:
        return None


def process_one(f):
    """抓取单只基金的净值 + 申购额度，返回 (fund_dict, ok)。"""
    try:
        hist = fetch_nav(f["code"])
        if not hist:
            return f["code"], None
        latest = hist[-1]
        f2 = dict(f)
        f2["latest_date"] = latest["date"]
        f2["latest_nav"] = latest["nav"]
        f2["latest_rate"] = latest["rate"]
        f2["history"] = hist
        f2["quota"] = fetch_quota(f["code"])  # 申购额度/状态
        if f["code"] in QUOTA_OVERRIDE and f2["quota"]:
            f2["quota"] = QUOTA_OVERRIDE[f["code"]]
        return f["code"], f2
    except Exception as e:
        return f["code"], ("ERR", str(e))


def fetch_indices():
    """抓取美股核心指数（纳指综指/标普500/道琼斯）最新点位与涨跌幅，供看板顶部展示参照系。
    数据来源东财行情接口。失败不影响主流程，返回空列表。"""
    # (展示名, secid)
    idx_list = [("纳斯达克", "100.NDX"), ("标普500", "100.SPX"), ("道琼斯", "100.DJIA")]
    out = []
    for name, secid in idx_list:
        try:
            url = (f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}"
                   f"&fields=f43,f58,f169,f170,f60,f86")
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://quote.eastmoney.com/"})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode()) .get("data") or {}
            price = d.get("f43")
            rate = d.get("f170")   # 涨跌幅，放大100倍
            chg = d.get("f169")    # 涨跌额，放大100倍
            if price is None or rate is None:
                continue
            out.append({
                "name": name,
                "point": round(price / 100, 2),      # 点位（东财放大100倍）
                "rate": round(rate / 100, 2),        # 涨跌幅 %
                "change": round((chg or 0) / 100, 2),  # 涨跌额
            })
            print(f"  指数 {name}: {round(price/100,2)} ({round(rate/100,2)}%)")
        except Exception as e:
            print(f"  指数 {name} 抓取失败：{str(e)[:60]}")
    return out


def main():
    funds = load_funds()
    print(f"共 {len(funds)} 只基金，{WORKERS} 线程并发抓取...")
    results = []
    fail = []
    done = 0
    total = len(funds)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for code, res in ex.map(process_one, funds):
            done += 1
            if res is None:
                fail.append(code)
                print(f"[{done}/{total}] {code} 无数据")
            elif isinstance(res, tuple) and res[0] == "ERR":
                fail.append(code)
                print(f"[{done}/{total}] {code} ERR {res[1]}")
            else:
                results.append(res)
                print(f"[{done}/{total}] {code} {res['name'][:16]} "
                      f"净值{res['latest_nav']} 涨跌{res['latest_rate']}% "
                      f"额度[{res.get('quota') or '--'}]")

    # 保持稳定顺序（并发返回顺序与 funds 一致，此处按原始列表再排一次以防万一）
    order = {f["code"]: i for i, f in enumerate(funds)}
    results.sort(key=lambda x: order.get(x["code"], 1e9))

    print("抓取美股核心指数...")
    indices = fetch_indices()

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(results),
        "indices": indices,
        "funds": results,
    }
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    print(f"\n完成：成功 {len(results)}，失败 {len(fail)}。输出 -> {OUT}")
    if fail:
        print("失败代码：", ",".join(fail))

    inline_into_html(payload)
    sync_dist()
    gen_card()


def gen_card():
    """抓数后生成营销卡片 dist/daily.png（依赖 Pillow，装在受管 venv）。
    独立子进程调用，失败不影响主流程。"""
    import subprocess, sys
    base = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(base, "gen_card.py")
    if not os.path.exists(script):
        return
    # 优先受管 venv 的 python（带 Pillow），回退当前解释器
    venv_py = r"C:/Users/liangqi/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    py = venv_py if os.path.exists(venv_py) else sys.executable
    try:
        r = subprocess.run([py, script], capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            print("已生成营销卡片 dist/daily.png。")
        else:
            print("卡片生成失败（不影响数据/推送）：", (r.stderr or r.stdout)[:200])
    except Exception as e:
        print("卡片生成异常（不影响数据/推送）：", e)


def sync_dist():
    """把部署所需文件同步到 dist/（部署源，排除本地日志）。"""
    import shutil
    base = os.path.dirname(os.path.abspath(__file__))
    dist = os.path.join(base, "dist")
    os.makedirs(dist, exist_ok=True)
    for fn in ("index.html", "app.js", "data.json"):
        src = os.path.join(base, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dist, fn))
    print("已同步部署文件到 dist/。")


def inline_into_html(payload):
    """把最新数据内联回 index.html 的 <script id="fundData"> 标签，使看板双击即最新。"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if not os.path.exists(html_path):
        print("未找到 index.html，跳过内联。")
        return
    html = open(html_path, encoding="utf-8").read()
    data_str = json.dumps(payload, ensure_ascii=False, indent=2).replace("</", "<\\/")
    pattern = r'(<script id="fundData" type="application/json">).*?(</script>)'
    new_html, n = re.subn(pattern, lambda m: m.group(1) + data_str + m.group(2),
                          html, count=1, flags=re.S)
    if n == 0:
        print("警告：未匹配到 fundData 标签，index.html 未更新。")
        return
    with open(html_path, "w", encoding="utf-8") as fp:
        fp.write(new_html)
    print(f"已将最新数据内联回 index.html（{payload['count']} 只，{payload['updated_at']}）。")


if __name__ == "__main__":
    main()
