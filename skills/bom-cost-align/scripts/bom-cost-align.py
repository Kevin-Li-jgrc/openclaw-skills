#!/usr/bin/env python3
"""
BOM 成本对齐脚本 v1.1
输入: 原始BOM(22列) + 采购成本表 → 输出: 手工版格式的成本核算Excel

环境变量:
  BOM_BASE  项目根目录（可选，未设置时需传 --base）

用法:
  python3 bom-cost-align.py <项目号> [--base BASE_DIR] [--bom BOM.xlsx] [--cost COST.xlsx]
  python3 bom-cost-align.py MyProject --base /data/projects
  python3 bom-cost-align.py MyProject --dry-run   # 只统计不输出
"""
import openpyxl, os, re, sys, argparse
from openpyxl.styles import Border, Side, PatternFill, Font

# ── 样式 ──
thin = Side(style='thin'); medium = Side(style='medium')
thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
header_border = Border(left=thin, right=thin, top=thin, bottom=medium)
COMP_FILL = PatternFill(start_color='DAEEF3', end_color='DAEEF3', fill_type='solid')
HDR_FILL = PatternFill(start_color='BFBFBF', end_color='BFBFBF', fill_type='solid')
COL_WIDTHS = {'A':38,'B':22,'C':28,'D':12,'E':8,'F':12,'G':14,'H':14,'I':10,'J':14}
HDRS = ['件号','零件名称','型号规格','说明','数量','品牌','单价','价格','组件数量','合计总价']

# ── 工具 ──
def hdr_qty(pn):
    m = re.search(r'×(\d+)', pn)
    return int(m.group(1)) if m else 1

def is_comp(pn): return '（' in pn and '）' in pn
def is_elec(pn): return bool(re.match(r'^E\d+-\d+$', pn))

# ── 采购加载 ──
def load_cost(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    cm = {}
    for r in wb["明细"].iter_rows(min_row=4, values_only=True):
        pn = str(r[0] or "").strip()
        if pn:
            try: cm[pn] = float(r[8]) if r[8] else 0
            except: pass
    wb.close()
    return cm

# ── BOM 解析 (统一22列布局) ──
# 机械: [0]件号 [1]名称 [2]类别 [3]规格 [4]物料代码 [5]说明 [6]数量 [7]品牌 ...
# 电气: [0]件号 [1]名称 [2]规格 [3]型号? [4]? [5]说明 [6]数量 [7]品牌 ...

def parse_mech(ws, cost_map):
    rows, stack = [], []
    for row_data in ws.iter_rows(min_row=2, values_only=True):
        pn = str(row_data[0] or "").strip()
        if not pn: continue
        
        if is_comp(pn):
            code = pn.split('（')[0]
            name = str(row_data[1] or "").strip()
            qty = hdr_qty(pn)
            while stack and code.count('-') <= stack[-1][0].count('-'):
                stack.pop()
            stack.append((code, name or code, qty))
            rows.append(('hdr', {'pn':pn, 'code':code, 'name':name, 'qty':qty}))
            continue
        
        if 'P' not in pn: continue
        try:
            name = str(row_data[1] or "").strip()
            spec = str(row_data[3] or "").strip()
            desc = str(row_data[5] or "").strip()
            brand = str(row_data[7] or "").strip()
            qty = float(row_data[6]) if row_data[6] else 0
        except (ValueError, TypeError):
            continue
        if qty <= 0: continue
        
        ct = cost_map.get(pn, 0)
        up = ct / qty if qty > 0 and ct > 0 else 0
        rows.append(('part', {
            'pn':pn,'name':name,'spec':spec,'desc':desc,
            'qty':qty,'brand':brand,'unit':up,'total':ct,
            'header': stack[-1][0] if stack else ''
        }))
    return rows

def parse_elec(ws, cost_map):
    skip = {'传感器','电气柜','标准件','电缆','辅材','伺服/辊道电机','长周期物料','辅料','标准物料'}
    rows = []
    for row_data in ws.iter_rows(min_row=2, values_only=True):
        pn = str(row_data[0] or "").strip()
        if not pn or pn in skip: continue
        if any(s in pn for s in ['长周期','标准物料','辅料']): continue
        if is_comp(pn): continue
        if not is_elec(pn): continue
        try:
            name = str(row_data[1] or "").strip()
            spec = str(row_data[2] or "").strip()
            desc = str(row_data[5] or "").strip()
            brand = str(row_data[7] or "").strip()
            qty = float(row_data[6]) if row_data[6] else 0
        except (ValueError, TypeError):
            continue
        if qty <= 0: continue
        ct = cost_map.get(pn, 0)
        up = ct / qty if qty > 0 and ct > 0 else 0
        rows.append(('part', {
            'pn':pn,'name':name,'spec':spec,'desc':desc,
            'qty':qty,'brand':brand,'unit':up,'total':ct
        }))
    return rows

def calc_subtotals(mech_rows):
    ct, cur = {}, None
    for rt, d in mech_rows:
        if rt == 'hdr': cur = d['code']; ct[cur] = 0
        elif rt == 'part' and cur: ct[cur] = ct.get(cur, 0) + d['total']
    return ct

# ── 写入 ──
def write_sheet(ws_out, data, comp_total):
    for c, h in enumerate(HDRS, 1):
        cell = ws_out.cell(row=1, column=c, value=h)
        cell.fill = HDR_FILL; cell.border = header_border; cell.font = Font(bold=True)
    
    r = 2
    for rt, d in data:
        if rt == 'hdr':
            for c in range(1, 11):
                ws_out.cell(row=r, column=c).fill = COMP_FILL
                ws_out.cell(row=r, column=c).border = thin_border
            ws_out.cell(row=r, column=1, value=d['pn'])
            ws_out.cell(row=r, column=2, value=d['name'])
            ws_out.cell(row=r, column=9, value=d['qty'])
            ws_out.cell(row=r, column=10, value=round(comp_total.get(d['code'], 0) * d['qty'], 2))
        else:
            for c in range(1, 11):
                ws_out.cell(row=r, column=c).border = thin_border
            ws_out.cell(row=r, column=1, value=d['pn'])
            ws_out.cell(row=r, column=2, value=d['name'])
            ws_out.cell(row=r, column=3, value=d['spec'])
            ws_out.cell(row=r, column=4, value=d['desc'])
            ws_out.cell(row=r, column=5, value=d['qty'])
            ws_out.cell(row=r, column=6, value=d['brand'])
            ws_out.cell(row=r, column=7, value=round(d['unit'], 4))
            ws_out.cell(row=r, column=8, value=round(d['total'], 4))
        r += 1
    for col, w in COL_WIDTHS.items():
        ws_out.column_dimensions[col].width = w

def find_files(d, proj):
    bf = cf = None
    for f in os.listdir(d):
        fp = os.path.join(d, f)
        if not os.path.isfile(fp): continue
        if not bf and f == f"{proj}.xlsx": bf = fp
        elif not cf and proj in f and ('采购成本' in f or '成本核算' in f) and f.endswith('.xlsx'): cf = fp
    return bf, cf

def main():
    p = argparse.ArgumentParser(description='BOM成本对齐')
    p.add_argument('project'); p.add_argument('--base'); p.add_argument('--bom'); p.add_argument('--cost')
    p.add_argument('--out', default='./output'); p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    
    base = a.base or os.environ.get('BOM_BASE', '.')
    odir = a.out
    pd = os.path.join(base, a.project)
    
    bp, cp = (a.bom, a.cost) if a.bom and a.cost else find_files(pd, a.project)
    if not bp: print(f"❌ BOM: {pd}/{a.project}.xlsx 不存在"); sys.exit(1)
    if not cp: print(f"❌ 采购文件: 找不到含 '采购成本/成本核算' 的 xlsx"); sys.exit(1)
    
    print(f"📦 {a.project}  BOM: {os.path.basename(bp)}  采购: {os.path.basename(cp)}")
    cost = load_cost(cp)
    print(f"   采购项: {len(cost)}")
    
    wb = openpyxl.load_workbook(bp, data_only=True)
    mech = parse_mech(wb['机械BOM表'], cost)
    elec = parse_elec(wb['电气BOM表'], cost)
    wb.close()
    
    ct = calc_subtotals(mech)
    
    mp = sum(1 for rt,_ in mech if rt=='part')
    ep = sum(1 for rt,_ in elec if rt=='part')
    mm = sum(1 for rt,d in mech if rt=='part' and d['total']>0)
    em = sum(1 for rt,d in elec if rt=='part' and d['total']>0)
    mt = sum(d['total'] for rt,d in mech if rt=='part')
    et = sum(d['total'] for rt,d in elec if rt=='part')
    
    print(f"   机械: {mp}p/{mm}m ({mm/mp*100 if mp else 0:.0f}%) ¥{mt:,.2f}  "
          f"电气: {ep}p/{em}m ({em/ep*100 if ep else 0:.0f}%) ¥{et:,.2f}  "
          f"合计: ¥{mt+et:,.2f}")
    
    if a.dry_run: print("🔍 --dry-run"); return
    
    os.makedirs(os.path.join(odir, a.project), exist_ok=True)
    op = os.path.join(odir, a.project, f"{a.project}_BOM成本核算_自动生成.xlsx")
    wb2 = openpyxl.Workbook(); wb2.remove(wb2.active)
    write_sheet(wb2.create_sheet('机械BOM'), mech, ct)
    write_sheet(wb2.create_sheet('电气BOM'), elec, {})
    wb2.save(op)
    print(f"✅ {op}")

if __name__ == '__main__':
    main()
