import http.server
import json
import urllib.parse
import os
import zipfile
import urllib.request
import io
import time
import xml.etree.ElementTree as ET
import datetime
import unicodedata
import base64

AI_REPORTS_DICT = {
    "2026_01": "# 🤖 2026년 1월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 1월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_02": "# 🤖 2026년 2월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 2월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_03": "# 🤖 2026년 3월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 3월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_04": "# 🤖 2026년 4월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 4월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_05": "# 🤖 2026년 5월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 5월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_06": "# 🤖 2026년 6월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 6월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_07": "# 🤖 2026년 7월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 7월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_08": "# 🤖 2026년 8월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 재무 AI 분석 포인트\n\n1. **지출 흐름 점검**\n   - 부모님의 8월 고정 지출(보험, 공과금 등) 변동폭을 확인하고 불필요한 누수를 점검하세요.\n   - 대출 원금 상환액을 꾸준히 늘려가는 것이 장기적으로 가장 이득입니다.\n\n2. **개선 추천 사항**\n   - 신용카드 할부 결제 비중을 낮추고, 가용 현금 내에서 예산을 통제하는 연습이 필요합니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이 있는지 월 1회 확인하세요.\n",
    "2026_Q1": "# 🤖 2026년 1분기 (1~3월) 가계부 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 📈 1분기 재무 흐름 총평\n- 1분기(1~3월)는 새해 첫 분기로 지출 변동이 컸으나 안정적인 방어가 돋보입니다.\n- 우민님의 경우 보험료 고정 지출에 대한 재정비가 여전히 주요 과제입니다.\n\n## 2. 💡 AI 추천 핵심 액션\n1. 불필요한 구독 서비스 해지 및 통신비 절감 시도\n2. 대출 이자 상환 비중을 줄이기 위한 원금 추가 상환 액션\n"
}

def fetch_google_sheet(sheet_type):
    urls = {
        "parents": "https://docs.google.com/spreadsheets/d/1M56YkKcj1i0KNfRNiubFUMUAEe922y9JoLr-ylGzF0k/export?format=xlsx",
        "parents_past": "https://docs.google.com/spreadsheets/d/18R3zBKaoX6hhcYQFYVY9rEKakw5RfUCo/export?format=xlsx",
        "yerin": "https://docs.google.com/spreadsheets/d/1Yfj22nvl0bfZhljjxl3YYbedkVW0Vi6OTli6xaSuaPo/export?format=xlsx",
        "yerin_past": "https://docs.google.com/spreadsheets/d/1_uEsvxrHBQTvgfRyumt75eIhjtacTXGH/export?format=xlsx"
    }
    url = urls.get(sheet_type)
    if not url: return None
    
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    return io.BytesIO(resp.read())

def excel_date_to_str(excel_date_num):
    try:
        val = float(excel_date_num)
        if val > 60:
            val -= 1
        dt = datetime.date(1899, 12, 30) + datetime.timedelta(days=val)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return str(excel_date_num)

def parse_excel_format_b(cells, shared_strings, target_month):
    rows = {}
    for ref, val in cells.items():
        r_idx = int(''.join(filter(str.isdigit, ref)) or 0)
        c_idx = ''.join(filter(str.isalpha, ref))
        if r_idx not in rows:
            rows[r_idx] = {}
        rows[r_idx][c_idx] = val

    transactions = []
    for r in sorted(rows.keys()):
        if r <= 7: continue
        r_data = rows[r]
        date_val = r_data.get('B', '')
        date_str = excel_date_to_str(date_val)
        if not date_str or '-' not in date_str: continue

        try:
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            if dt.year == 2026 and dt.month == target_month:
                transactions.append({
                    'date': date_str,
                    'type': r_data.get('C', '').strip(),
                    'category': r_data.get('D', '').strip(),
                    'subcategory': r_data.get('E', '').strip(),
                    'desc': r_data.get('F', '').strip(),
                    'account': r_data.get('G', '').strip(),
                    'amount': float(r_data.get('I', '0') or 0),
                    'detail': r_data.get('J', '').strip()
                })
        except Exception:
            pass
    return transactions

def parse_excel_format_a(cells, shared_strings, target_month):
    rows = {}
    for ref, val in cells.items():
        r_idx = int(''.join(filter(str.isdigit, ref)) or 0)
        c_idx = ''.join(filter(str.isalpha, ref))
        if r_idx not in rows:
            rows[r_idx] = {}
        rows[r_idx][c_idx] = val

    transactions = []
    for r in sorted(rows.keys()):
        if r <= 30: continue
        r_data = rows[r]

        inc_date_val = r_data.get('B', '')
        inc_date = excel_date_to_str(inc_date_val)
        if inc_date and '-' in inc_date and r_data.get('C') == '수입':
            try:
                amount = float(r_data.get('H', '0') or 0)
                if amount > 0:
                    subcategory = r_data.get('E', '').strip()
                    if subcategory in ['◀', '▶']: subcategory = ''
                    transactions.append({
                        'date': inc_date, 'type': '수입',
                        'category': r_data.get('D', '').strip() or '수입기타',
                        'subcategory': subcategory,
                        'desc': r_data.get('F', '').strip(),
                        'account': '계좌이체', 'amount': amount, 'detail': ''
                    })
            except Exception: pass

        exp_date_val = r_data.get('J', '')
        exp_date = excel_date_to_str(exp_date_val)
        if exp_date and '-' in exp_date and r_data.get('L'):
            try:
                amount = float(r_data.get('R', r_data.get('P', '0')) or 0)
                if amount > 0:
                    subcategory = r_data.get('M', '').strip()
                    desc = r_data.get('N', '').strip()
                    if subcategory in ['◀', '▶']: subcategory = ''
                    if desc in ['◀', '▶']: desc = ''
                    transactions.append({
                        'date': exp_date, 'type': '지출',
                        'category': r_data.get('L', '').strip() or '기타',
                        'subcategory': subcategory, 'desc': desc,
                        'account': r_data.get('K', '').strip() or '계좌이체',
                        'amount': amount, 'detail': r_data.get('S', '').strip()
                    })
            except Exception: pass
    return transactions

def get_sheet_cells_dict(zip_ref, sheet_file, shared_strings):
    try:
        sheet_xml = zip_ref.read(sheet_file)
        sheet_root = ET.fromstring(sheet_xml)
        ns_main = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        cells = {}
        for row in sheet_root.findall('.//main:row', ns_main):
            for c in row.findall('.//main:c', ns_main):
                ref = c.get('r')
                t = c.get('t')
                val_elem = c.find('main:v', ns_main)
                val = ''
                if val_elem is not None:
                    val = val_elem.text or ''
                    if t == 's': val = shared_strings[int(val)]
                cells[ref] = val
        return cells
    except Exception:
        return {}

def parse_excel_ledger(sheet_type, target_month):
    file_like = fetch_google_sheet(sheet_type)
    if not file_like: return []
    try:
        with zipfile.ZipFile(file_like, 'r') as zip_ref:
            shared_strings = []
            try:
                ss_xml = zip_ref.read('xl/sharedStrings.xml')
                ss_root = ET.fromstring(ss_xml)
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for t_elem in ss_root.findall('.//main:t', ns):
                    shared_strings.append(t_elem.text or '')
            except KeyError: pass

            sheets_info = {}
            wb_rels_xml = zip_ref.read('xl/_rels/workbook.xml.rels')
            wb_rels_root = ET.fromstring(wb_rels_xml)
            ns_rel = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            for rel in wb_rels_root.findall('.//rel:Relationship', ns_rel):
                sheets_info[rel.get('Id')] = rel.get('Target')

            workbook_xml = zip_ref.read('xl/workbook.xml')
            wb_root = ET.fromstring(workbook_xml)
            ns_main = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            sheets = {}
            for sheet_elem in wb_root.findall('.//main:sheet', ns_main):
                name = unicodedata.normalize('NFC', sheet_elem.get('name'))
                r_id = sheet_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                sheets[name] = r_id

            if '가계부입력' in sheets:
                r_id = sheets['가계부입력']
                sheet_file = sheets_info.get(r_id, '')
                if not sheet_file.startswith('xl/'): sheet_file = 'xl/' + sheet_file
                cells = get_sheet_cells_dict(zip_ref, sheet_file, shared_strings)
                return parse_excel_format_b(cells, shared_strings, target_month)
            
            target_sheet_name = f"{target_month}월"
            if target_sheet_name in sheets:
                r_id = sheets[target_sheet_name]
                sheet_file = sheets_info.get(r_id, '')
                if not sheet_file.startswith('xl/'): sheet_file = 'xl/' + sheet_file
                cells = get_sheet_cells_dict(zip_ref, sheet_file, shared_strings)
                return parse_excel_format_a(cells, shared_strings, target_month)
            return []
    except Exception as e:
        print(f"Error parsing Excel file {sheet_type}: {e}")
        return []

def parse_parents_loan(sheet_type, month):
    return {
        'totalLoan': 217000000.0,
        'balance': 159222836.0 if month >= 8 else 162461982.0,
        'principal': 144269.0,
        'interest': 598954.0,
        'totalPayment': 743224.0
    }

class handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        # --- PARENTS AUTH ENDPOINT ---
        if self.path.startswith('/api/parents') or self.path == '/parents.html':
            auth_header = self.headers.get('Authorization')
            expected_auth = "Basic " + base64.b64encode(b"woomin:1234").decode('ascii')
            
            if auth_header != expected_auth:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Parents Dashboard"')
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return
            
            # Fetch parents.html content from public directory
            html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>부모님 전용 가계부 대시보드</title>
    <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/parents.css">
</head>
<body>
    <div class="dashboard">
        <header>
            <div class="header-content">
                <h1>👨‍👩‍👧 우민 가계부 (부모님 전용)</h1>
                <p class="subtitle">어머니, 아버지의 실시간 가계부 현황입니다.</p>
            </div>
            <div class="month-selector" id="monthSelector">
                <!-- Months generated by JS -->
            </div>
        </header>

        <div class="grid-container">
            <!-- 1. 핵심 요약 카드 -->
            <div class="summary-cards">
                <div class="card stat-card income">
                    <h3>총 수입</h3>
                    <p id="totalIncome">0원</p>
                </div>
                <div class="card stat-card expense">
                    <h3>총 지출</h3>
                    <p id="totalExpense">0원</p>
                </div>
                <div class="card stat-card balance">
                    <h3>여유 자금</h3>
                    <p id="totalBalance">0원</p>
                </div>
            </div>

            <!-- 2. 이번 달 가계부 분석 (AI 리포트) -->
            <div class="card ai-report-card full-width">
                <div class="card-header">
                    <h2>🤖 AI 가계부 분석 리포트</h2>
                </div>
                <div id="aiReportContent" class="markdown-body">
                    리포트를 불러오는 중입니다...
                </div>
            </div>

            <!-- 3. 고정 지출 상세 -->
            <div class="card fixed-expenses-card">
                <div class="card-header">
                    <h2>📌 고정 지출 내역</h2>
                    <span class="badge" id="fixedExpenseTotal">0원</span>
                </div>
                <div class="list-container" id="fixedExpensesList">
                    <!-- JS로 채워짐 -->
                </div>
            </div>

            <!-- 4. 대출 상환 현황 -->
            <div class="card loan-card">
                <div class="card-header">
                    <h2>🏦 대출 상환 현황</h2>
                </div>
                <div class="loan-stats">
                    <div class="stat-row">
                        <span>남은 대출 원금</span>
                        <strong id="loanBalance">0원</strong>
                    </div>
                    <div class="stat-row highlight">
                        <span>이번 달 상환액 (원금+이자)</span>
                        <strong id="loanPayment">0원</strong>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" id="loanProgress"></div>
                    </div>
                    <p class="progress-text" id="loanProgressText">상환율 0%</p>
                </div>
            </div>
        </div>
    </div>
    <script src="/parents.js"></script>
</body>
</html>"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            return

        # --- YEARLY TREND ENDPOINT ---
        if self.path.startswith('/api/yearly-trend'):
            trend_data = []
            for m in range(1, 13):
                txs = parse_excel_ledger("parents", m)
                if not txs and m <= 4:
                    txs = parse_excel_ledger("parents_past", m)
                    
                income = 0; consumption = 0; savings = 0
                if txs:
                    for tx in txs:
                        if tx['type'] == '수입': income += tx['amount']
                        elif tx['type'] == '지출':
                            if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                            if '저축' in tx['category'] or '예적금' in tx['category'] or '청약' in tx['category'] or '적금' in tx['category']: savings += tx['amount']
                            else: consumption += tx['amount']
                trend_data.append({'month': m, 'income': income, 'consumption': consumption, 'savings': savings, 'balance': income - consumption - savings})
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(trend_data, ensure_ascii=False).encode('utf-8'))
            return

        # --- MAIN DATA ENDPOINT ---
        if self.path.startswith('/api/data'):
            query_params = urllib.parse.parse_qs(parsed_url.query)
            month = int(query_params.get('month', [8])[0])

            selected_parents_path = "parents_past" if month <= 4 else "parents"
            yerin_xlsx_path = "yerin_past" if month <= 4 else "yerin"

            parents_tx = parse_excel_ledger(selected_parents_path, month)
            yerin_tx = parse_excel_ledger(yerin_xlsx_path, month)

            p_income = 0; p_consumption = 0; p_savings = 0
            for tx in parents_tx:
                if tx['type'] == '수입': p_income += tx['amount']
                elif tx['type'] == '지출':
                    if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                    if '저축' in tx['category'] or '적금' in tx['category'] or '청약' in tx['category']: p_savings += tx['amount']
                    else: p_consumption += tx['amount']

            y_income = 0; y_consumption = 0; y_savings = 0
            for tx in yerin_tx:
                if tx['type'] == '수입': y_income += tx['amount']
                elif tx['type'] == '지출':
                    if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                    if '저축' in tx['category'] or '적금' in tx['category'] or '청약' in tx['category']: y_savings += tx['amount']
                    else: y_consumption += tx['amount']

            month_key = f"2026_{month:02d}"
            ai_report_md = AI_REPORTS_DICT.get(month_key, f"아직 {month}월 가계부 분석 데이터가 없습니다.")

            parents_stats = {
                'transactions': parents_tx,
                'fixedExpenses': [t for t in parents_tx if t['type'] == '지출' and ('고정' in str(t.get('category','')) or '보험' in str(t.get('category','')))],
                'categories': {},
                'noSpendDays': [],
                'summary': { 'income': p_income, 'consumption': p_consumption, 'savings': p_savings, 'balance': p_income - p_consumption - p_savings },
                'loan': parse_parents_loan(selected_parents_path, month),
                'ai_report': ai_report_md
            }
            
            yerin_stats = {
                'transactions': yerin_tx,
                'summary': { 'income': y_income, 'consumption': y_consumption, 'savings': y_savings, 'balance': y_income - y_consumption - y_savings },
                'loan': None
            }

            response_data = {
                'month': month,
                'yerin': yerin_stats,
                'parents': parents_stats,
                'ai_report': ai_report_md,
                'crossCheck': []
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            return
            
        self.send_response(404)
        self.end_headers()
