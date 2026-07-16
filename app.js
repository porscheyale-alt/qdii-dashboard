/* QDII 净值看板交互逻辑。涨红跌绿（A股习惯）。 */
(function(){
  const UP="up", DOWN="down";
  // 读取内联数据；若为占位符（本地未内联），则回退 fetch data.json
  let DATA = null;
  let state = { group:"全部", kw:"", sort:"rate_desc" };
  let chart = null;

  // 自选：存 localStorage，按基金代码记忆，每个浏览器独立
  const FAV_KEY = "qdii_favs";
  function loadFavs(){
    try{ return new Set(JSON.parse(localStorage.getItem(FAV_KEY)||"[]")); }
    catch(e){ return new Set(); }
  }
  let favs = loadFavs();
  function isFav(code){ return favs.has(code); }
  function toggleFav(code){
    if(favs.has(code)) favs.delete(code); else favs.add(code);
    localStorage.setItem(FAV_KEY, JSON.stringify([...favs]));
  }

  try{
    const raw = document.getElementById("fundData").textContent.trim();
    if(raw && raw[0]==="{") DATA = JSON.parse(raw);
  }catch(e){ console.warn("inline parse fail", e); }

  function boot(data){
    DATA = data;
    render();
  }

  if(DATA){ render(); }
  else{
    fetch("data.json").then(r=>r.json()).then(boot).catch(err=>{
      document.getElementById("tbody").innerHTML =
        '<tr><td colspan="7" class="empty">数据加载失败：请通过本地服务器打开，或运行 fetch_data.py 生成 data.json</td></tr>';
    });
  }

  function fmtRate(r){
    if(r===null||r===undefined) return {t:"--",c:""};
    const c = r>0?UP:(r<0?DOWN:"");
    const s = (r>0?"+":"")+r.toFixed(2)+"%";
    return {t:s,c:c};
  }

  function render(){
    if(!DATA) return;
    document.getElementById("metaInfo").textContent =
      "数据更新："+DATA.updated_at+" ｜ 共 "+DATA.count+" 只";
    buildTabs();
    buildSummary();
    buildTable();
    document.getElementById("foot").innerHTML =
      "说明：净值来源于公开数据（天天基金），QDII 单位净值通常 T+1（部分 T+2）公布，非实时行情。"+
      "颜色遵循 A 股习惯：<span class='up'>涨为红</span> / <span class='down'>跌为绿</span>。"+
      "点击任意一行查看近 30 日净值走势。额度信息因每日变化极小，未纳入监控。";
    bindEvents();
  }

  function groups(){
    const g = ["全部"];
    DATA.funds.forEach(f=>{ if(!g.includes(f.group)) g.push(f.group); });
    return g;
  }

  function buildTabs(){
    const el = document.getElementById("tabs");
    const favTab = `<div class="tab ${state.group==='自选'?'active':''}" data-g="自选">★ 自选<span class="cnt">${favs.size}</span></div>`;
    el.innerHTML = favTab + groups().map(g=>
      `<div class="tab ${g===state.group?'active':''}" data-g="${g}">${g}</div>`).join("");
    el.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{
      state.group=t.dataset.g; buildTabs(); buildTable();
    });
  }

  function filtered(){
    let arr = DATA.funds.slice();
    if(state.group==="自选") arr = arr.filter(f=>isFav(f.code));
    else if(state.group!=="全部") arr = arr.filter(f=>f.group===state.group);
    if(state.kw){
      const k = state.kw.toLowerCase();
      arr = arr.filter(f=>f.name.toLowerCase().includes(k)||f.code.includes(k));
    }
    if(state.sort==="rate_desc") arr.sort((a,b)=>(b.latest_rate??-999)-(a.latest_rate??-999));
    else if(state.sort==="rate_asc") arr.sort((a,b)=>(a.latest_rate??999)-(b.latest_rate??999));
    else arr.sort((a,b)=>a.name.localeCompare(b.name,"zh"));
    return arr;
  }

  function buildSummary(){
    const fs = DATA.funds.filter(f=>f.latest_rate!==null&&f.latest_rate!==undefined);
    const up = fs.filter(f=>f.latest_rate>0).length;
    const down = fs.filter(f=>f.latest_rate<0).length;
    const flat = fs.length-up-down;
    const avg = fs.reduce((s,f)=>s+f.latest_rate,0)/(fs.length||1);
    const top = fs.slice().sort((a,b)=>b.latest_rate-a.latest_rate)[0];
    const bot = fs.slice().sort((a,b)=>a.latest_rate-b.latest_rate)[0];
    const avgCls = avg>0?UP:(avg<0?DOWN:"");
    const cards = [
      {l:"今日上涨",cc:"c-up",v:`<span class="up">${up}</span> <small>只</small>`},
      {l:"今日下跌",cc:"c-down",v:`<span class="down">${down}</span> <small>只</small>`},
      {l:"平盘",cc:"",v:`${flat} <small>只</small>`},
      {l:"平均涨跌幅",cc:avg>0?"c-up":(avg<0?"c-down":""),v:`<span class="${avgCls}">${(avg>0?"+":"")+avg.toFixed(2)}%</span>`},
      {l:"涨幅榜首",cc:"c-up",v:top?`<span class="up">+${top.latest_rate.toFixed(2)}%</span><br><small>${top.name.slice(0,10)}</small>`:"--"},
      {l:"跌幅榜首",cc:"c-down",v:bot?`<span class="${bot.latest_rate<0?'down':''}">${bot.latest_rate.toFixed(2)}%</span><br><small>${bot.name.slice(0,10)}</small>`:"--"},
    ];
    document.getElementById("summary").innerHTML = cards.map(c=>
      `<div class="scard ${c.cc}"><div class="lbl">${c.l}</div><div class="val">${c.v}</div></div>`).join("");
  }

  function sparkline(canvas, hist){
    const navs = hist.map(h=>h.nav);
    const up = navs[navs.length-1] >= navs[0];
    const ctx = canvas.getContext("2d");
    new Chart(ctx,{type:"line",data:{labels:navs.map((_,i)=>i),
      datasets:[{data:navs,borderColor:up?getCss("--up"):getCss("--down"),
        borderWidth:1.5,pointRadius:0,tension:.3,fill:false}]},
      options:{responsive:false,plugins:{legend:{display:false},tooltip:{enabled:false}},
        scales:{x:{display:false},y:{display:false}},animation:false}});
  }

  function getCss(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}

  function buildTable(){
    const arr = filtered();
    const tb = document.getElementById("tbody");
    if(!arr.length){
      const msg = state.group==="自选"
        ? "还没有自选基金。点任意一行左侧的 ☆ 收藏，收藏后可在这里集中查看。"
        : "无匹配基金";
      tb.innerHTML = '<tr><td colspan="7" class="empty">'+msg+'</td></tr>';
      return;
    }
    tb.innerHTML = arr.map((f,i)=>{
      const r = fmtRate(f.latest_rate);
      const on = isFav(f.code);
      const pillCls = r.c===UP?"up":(r.c===DOWN?"down":"flat");
      return `<tr data-code="${f.code}">
        <td class="star-col"><span class="star ${on?'on':''}" data-fav="${f.code}" title="${on?'取消自选':'加入自选'}">${on?'★':'☆'}</span></td>
        <td class="fname">${f.name}<div class="code">${f.code}</div></td>
        <td class="col-group"><span class="grp-tag">${f.group}</span></td>
        <td class="num">${f.latest_nav.toFixed(4)}</td>
        <td class="num"><span class="pill ${pillCls}">${r.t}</span></td>
        <td class="col-spark"><canvas class="spark" id="sp_${f.code}" width="110" height="30"></canvas></td>
        <td class="num code col-date">${f.latest_date}</td>
      </tr>`;
    }).join("");
    arr.forEach(f=>{ const cv=document.getElementById("sp_"+f.code); if(cv) sparkline(cv,f.history); });
    // 行点击开抽屉；星标点击切换自选（阻止冒泡，避免同时开抽屉）
    tb.querySelectorAll("tr[data-code]").forEach(tr=>tr.onclick=()=>openDrawer(tr.dataset.code));
    tb.querySelectorAll(".star").forEach(s=>s.onclick=(e)=>{
      e.stopPropagation();
      toggleFav(s.dataset.fav);
      buildTabs();
      buildTable();
    });
  }

  function openDrawer(code){
    const f = DATA.funds.find(x=>x.code===code);
    if(!f) return;
    document.getElementById("dName").textContent = f.name;
    document.getElementById("dCode").textContent = "代码 "+f.code+" ｜ "+f.group;
    // 区间统计
    const hist=f.history, first=hist[0].nav, last=hist[hist.length-1].nav;
    const chg=((last-first)/first*100);
    const maxNav=Math.max(...hist.map(h=>h.nav)), minNav=Math.min(...hist.map(h=>h.nav));
    const r=fmtRate(f.latest_rate), chgCls=chg>0?UP:(chg<0?DOWN:"");
    document.getElementById("dStats").innerHTML = `
      <div class="dstat"><div class="l">最新净值</div><div class="v">${last.toFixed(4)}</div></div>
      <div class="dstat"><div class="l">今日涨跌</div><div class="v"><span class="pill ${r.c===UP?'up':(r.c===DOWN?'down':'flat')}">${r.t}</span></div></div>
      <div class="dstat"><div class="l">近${hist.length}日累计</div><div class="v ${chgCls}">${(chg>0?"+":"")+chg.toFixed(2)}%</div></div>
      <div class="dstat"><div class="l">区间最高</div><div class="v">${maxNav.toFixed(4)}</div></div>
      <div class="dstat"><div class="l">区间最低</div><div class="v">${minNav.toFixed(4)}</div></div>
      <div class="dstat"><div class="l">净值日期</div><div class="v" style="font-size:14px">${f.latest_date}</div></div>`;
    // 主图
    if(chart) chart.destroy();
    const up = last>=first;
    chart = new Chart(document.getElementById("navChart").getContext("2d"),{
      type:"line",
      data:{labels:hist.map(h=>h.date.slice(5)),
        datasets:[{label:"单位净值",data:hist.map(h=>h.nav),
          borderColor:up?getCss("--up"):getCss("--down"),backgroundColor:(up?"rgba(224,45,45,.08)":"rgba(10,163,79,.08)"),
          borderWidth:2,pointRadius:0,tension:.25,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{y:{grid:{color:"#eef0f3"}},x:{grid:{display:false},ticks:{maxTicksLimit:8}}}}});
    // 明细表（倒序）
    document.getElementById("navRows").innerHTML = hist.slice().reverse().map(h=>{
      const rr=fmtRate(h.rate);
      return `<tr><td>${h.date}</td><td>${h.nav.toFixed(4)}</td><td class="${rr.c}">${rr.t}</td></tr>`;
    }).join("");
    document.getElementById("mask").classList.add("show");
    document.getElementById("drawer").classList.add("show");
  }

  function closeDrawer(){
    document.getElementById("mask").classList.remove("show");
    document.getElementById("drawer").classList.remove("show");
  }

  function bindEvents(){
    document.getElementById("searchInput").oninput=(e)=>{state.kw=e.target.value.trim();buildTable();};
    document.getElementById("sortSel").onchange=(e)=>{state.sort=e.target.value;buildTable();};
    document.getElementById("closeBtn").onclick=closeDrawer;
    document.getElementById("mask").onclick=closeDrawer;
  }
})();
