# -*- coding: utf-8 -*-
"""
QDII 净值看板 - 抓数脚本
读取 QDII产品表.xlsx 的全部基金代码，批量拉取天天基金每日净值，生成 data.json。
QDII 净值 T+1（部分 T+2）公布，本脚本抓取最近 N 个交易日净值。
"""
import os, re, json, time, urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
FUNDS = os.path.join(BASE, "funds.json")  # 基金列表（由 Excel 预先提取，云端可用）
OUT = os.path.join(BASE, "data.json")
HISTORY_DAYS = 30  # 每只基金抓取的历史净值条数


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


def main():
    funds = load_funds()
    print(f"共 {len(funds)} 只基金，开始抓取...")
    results = []
    fail = []
    for i, f in enumerate(funds, 1):
        try:
            hist = fetch_nav(f["code"])
            if not hist:
                fail.append(f["code"])
                print(f"[{i}/{len(funds)}] {f['code']} 无数据")
                continue
            latest = hist[-1]
            f2 = dict(f)
            f2["latest_date"] = latest["date"]
            f2["latest_nav"] = latest["nav"]
            f2["latest_rate"] = latest["rate"]
            f2["history"] = hist
            results.append(f2)
            print(f"[{i}/{len(funds)}] {f['code']} {f['name'][:16]} "
                  f"净值{latest['nav']} 涨跌{latest['rate']}%")
        except Exception as e:
            fail.append(f["code"])
            print(f"[{i}/{len(funds)}] {f['code']} ERR {e}")
        time.sleep(0.25)  # 轻微限速，避免被封

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(results),
        "funds": results,
    }
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    print(f"\n完成：成功 {len(results)}，失败 {len(fail)}。输出 -> {OUT}")
    if fail:
        print("失败代码：", ",".join(fail))

    inline_into_html(payload)
    sync_dist()


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
