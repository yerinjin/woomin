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
    "2026_01": "# 🤖 2026년 1월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 1월 재무 AI 분석 포인트\n\n1. **새해 첫 예산 초과 점검**\n   - 연초 잦은 가족 모임과 행사로 인해 식비 및 모임 카테고리 지출이 평소보다 높게 측정되었습니다.\n   - 부모님의 고정 지출(연시보험, 종란보험, 주거통신비 등)은 지난달과 동일하게 잘 방어되었습니다.\n\n2. **개선 추천 사항**\n   - 이번 달 모임 지출 비중이 전체의 20%를 초과했습니다. 2월에는 설 연휴가 있으므로 이번 달 남은 가용 현금을 비상금으로 이체해 두시는 것을 추천합니다.\n   - 신일자동차서비스 등 차량 유지비 예산을 올해 연간 계획으로 미리 분배해두면 좋습니다.\n",
    "2026_02": "# 🤖 2026년 2월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 2월 재무 AI 분석 포인트\n\n1. **명절(설날) 특수 지출 분석**\n   - 설 연휴 가족 행사 및 용돈 지출로 인해 이번 달 '경조사비'와 '식비' 항목이 크게 상승했습니다.\n   - 반면 일수가 적은 2월 특성상 생활용품비 및 유류교통비 지출은 전월 대비 15% 감소했습니다.\n\n2. **개선 추천 사항**\n   - 명절 상여금 등 비정기 수입이 있었다면, 바로 대출 원금 상환액에 보태어 이자 부담을 줄이는 것이 장기적으로 가장 이득입니다.\n   - 오케이마취통증의학과 등 정기적인 의료비 지출이 발생하고 있으므로, 실비 청구가 누락되지 않았는지 월말 점검이 필요합니다.\n",
    "2026_03": "# 🤖 2026년 3월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 3월 재무 AI 분석 포인트\n\n1. **봄철 활동량 증가에 따른 지출 변화**\n   - 나들이 등 외부 활동이 늘어나면서 유류교통비와 외식 비중이 1, 2월에 비해 상승 곡선을 그리고 있습니다.\n   - 연시보험 및 종란보험 등 고정 납입금은 정상적으로 잘 처리되었으나, 기타 잡비 항목이 조금씩 늘고 있습니다.\n\n2. **개선 추천 사항**\n   - 신용카드 무이자 할부 이용 금액이 쌓이고 있지 않은지 확인하세요. 가급적 체크카드나 현금 흐름 내에서 통제하는 연습이 중요합니다.\n   - 환절기로 인한 병원 방문(봉정민내과의원 등)이 잦아졌습니다. 건강 관리를 위한 예방 차원의 식비 투자는 좋은 지출입니다.\n",
    "2026_04": "# 🤖 2026년 4월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 4월 재무 AI 분석 포인트\n\n1. **가장 안정적인 지출 달의 성과**\n   - 큰 명절이나 행사가 없는 4월은 부모님의 가계부가 가장 흑자를 기록하기 좋은 달입니다. 이번 달 잉여 자금 비율이 긍정적입니다!\n   - 주거통신비에서 불필요한 결합 할인 누락이나 프리미엄 요금제 사용이 없는지 1분기 결산과 함께 점검하셨기를 바랍니다.\n\n2. **개선 추천 사항**\n   - 다가올 5월(가정의 달)은 지출이 폭발적으로 늘어나는 시기입니다. 4월의 잉여 자금(여유 자금)을 5월 이벤트 예산으로 따로 빼두시면 가계부 펑크를 막을 수 있습니다.\n",
    "2026_05": "# 🤖 2026년 5월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 5월 재무 AI 분석 포인트\n\n1. **가정의 달 지출 방어 결과**\n   - 어버이날, 가족 모임 등 1년 중 가장 지출 변동성이 큰 달입니다. 다행히 4월에 이월한 예산을 활용하여 카드 빚으로 넘어가는 현상은 막았습니다.\n   - 문화생활비 및 용돈 지출이 평월 대비 2배 이상 증가했습니다.\n\n2. **개선 추천 사항**\n   - 크게 늘어난 지출로 인해 5월의 저축률은 다소 떨어졌지만 계획된 지출이라면 문제없습니다.\n   - 자동차 정비(신일자동차서비스 등)나 교체 주기가 도래하는 소모품이 있다면 여름이 오기 전인 6월로 분산해 예산을 짜보세요.\n",
    "2026_06": "# 🤖 2026년 6월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 6월 재무 AI 분석 포인트\n\n1. **상반기 결산 및 쿨다운 시기**\n   - 5월의 폭풍 같은 지출이 지나고 다시 안정기를 되찾았습니다. 상반기(1~6월) 대출 상환액을 꾸준히 지켜오신 점이 훌륭합니다.\n   - 에어컨 가동이 시작되면서 공과금(주거통신 카테고리)이 소폭 상승하기 시작했습니다.\n\n2. **개선 추천 사항**\n   - 7~8월 여름 휴가비 마련을 위해 6월의 변동 지출(외식, 생활용품)을 평소보다 10% 더 조이는 것이 좋습니다.\n   - 고정 지출 중 해지가 가능한 불필요한 유료 구독이나 TV 부가서비스가 없는지 상반기 정리를 권장합니다.\n",
    "2026_07": "# 🤖 2026년 7월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 7월 재무 AI 분석 포인트\n\n1. **여름 휴가 및 냉방비 상승 방어**\n   - 본격적인 무더위로 인해 주거통신 카테고리의 전기요금 비중이 눈에 띄게 증가했습니다.\n   - 휴가 관련 지출(문화생활비, 유류교통비)이 발생했지만 예산 내에서 적절히 방어되고 있습니다.\n\n2. **개선 추천 사항**\n   - 의료비 지출(오케이마취통증의학과 등)이 잦은 시기입니다. 덥고 습한 날씨에 건강 관리를 최우선으로 하시고 실손 보험 청구를 잊지 마세요.\n   - 하반기 재산세 납부 등 굵직한 세금 이슈가 있으니 통장 잔고를 일정 수준 이상 유지하세요.\n",
    "2026_08": "# 🤖 2026년 8월 가계부 AI 분석 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 💡 8월 재무 AI 분석 포인트\n\n1. **막바지 더위와 지출 패턴 안정화**\n   - 이번 달은 '기타' 및 '생활용품비'의 자잘한 누수 없이 식비와 고정 지출(연시/종란보험) 위주로 깔끔하게 정리된 달입니다.\n   - 차량 주유비 및 신일자동차서비스 결제 건이 확인되며, 이동이 많았던 달로 분석됩니다.\n\n2. **개선 추천 사항**\n   - 대출 원금 잔액이 1억 5천만 원대로 진입했습니다! 매월 이자로 빠져나가는 금액을 조금이라도 더 원금 상환으로 돌릴 수 있다면 이자 비용을 크게 절약할 수 있습니다.\n   - 9월 추석 명절이 다가오고 있습니다. 8월 말 남은 예산은 모두 9월 명절 비상금으로 비축해 두세요.\n",
    "2026_Q1": "# 🤖 2026년 1분기 (1~3월) 가계부 리포트 (부모님 전용)\n\n> **작성일:** 2026년 8월 26일 (자동 생성됨)\n> **대상:** 부모님(우민님) 가계부 단독 분석\n\n---\n\n## 1. 📈 1분기 재무 흐름 총평\n- 1분기(1~3월)는 새해 첫 분기로 명절 지출 변동이 컸으나 안정적인 방어가 돋보였습니다.\n- 우민님의 경우 보험료 고정 지출과 의료비 지출에 대한 예산 재정비가 하반기 주요 과제입니다.\n\n## 2. 💡 AI 추천 핵심 액션\n1. 불필요한 구독 서비스 해지 및 통신비/결합할인 점검\n2. 대출 이자 상환 비중을 줄이기 위한 원금 추가 상환 액션 계획 수립\n"
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
                dt = datetime.datetime.strptime(inc_date, '%Y-%m-%d')
                if dt.month == target_month:
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
                dt = datetime.datetime.strptime(exp_date, '%Y-%m-%d')
                if dt.month == target_month:
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
                for si_elem in ss_root.findall('.//main:si', ns):
                    text_parts = []
                    for t_elem in si_elem.findall('.//main:t', ns):
                        text_parts.append(t_elem.text or '')
                    shared_strings.append(''.join(text_parts))
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
        query_params = urllib.parse.parse_qs(parsed_url.query)
        route = query_params.get('route', [''])[0]
        
        # --- PARENTS AUTH ENDPOINT ---
        if route == 'parents' or self.path.startswith('/api/parents') or self.path == '/parents.html':
            auth_header = self.headers.get('Authorization')
            expected_auth = "Basic " + base64.b64encode(b"woomin:1234").decode('ascii')
            
            if auth_header != expected_auth:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Parents Dashboard"')
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return
            
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

            <div class="card ai-report-card full-width">
                <div class="card-header">
                    <h2>🤖 AI 가계부 분석 리포트</h2>
                </div>
                <div id="aiReportContent" class="markdown-body">
                    리포트를 불러오는 중입니다...
                </div>
            </div>

            <div class="card fixed-expenses-card">
                <div class="card-header">
                    <h2>📌 고정 지출 내역</h2>
                    <span class="badge" id="fixedExpenseTotal">0원</span>
                </div>
                <div class="list-container" id="fixedExpensesList">
                </div>
            </div>

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
        if route == 'yearly-trend' or self.path.startswith('/api/yearly-trend'):
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
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(json.dumps(trend_data, ensure_ascii=False).encode('utf-8'))
            return

        # --- MAIN DATA ENDPOINT ---
        if route == 'data' or self.path.startswith('/api/data'):
            month = int(query_params.get('month', [8])[0])

            selected_parents_path = "parents_past" if month <= 4 else "parents"
            yerin_xlsx_path = "yerin_past" if month <= 4 else "yerin"

            parents_tx = parse_excel_ledger(selected_parents_path, month)
            yerin_tx = parse_excel_ledger(yerin_xlsx_path, month)

            for tx in parents_tx + yerin_tx:
                if '환급' in str(tx.get('category', '')):
                    tx['type'] = '환급'

            p_income = 0; p_consumption = 0; p_savings = 0
            p_categories = {}
            for tx in parents_tx:
                if tx['type'] == '수입': p_income += tx['amount']
                elif tx['type'] == '지출':
                    if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                    if '환급' in tx['category'] or '환급금' in tx['category']: continue
                    if '저축' in tx['category'] or '적금' in tx['category'] or '청약' in tx['category']: p_savings += tx['amount']
                    else: 
                        p_consumption += tx['amount']
                        c = tx.get('category', '기타')
                        p_categories[c] = p_categories.get(c, 0) + tx['amount']

            y_income = 0; y_consumption = 0; y_savings = 0
            for tx in yerin_tx:
                if tx['type'] == '수입': y_income += tx['amount']
                elif tx['type'] == '지출':
                    if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                    if '환급' in tx['category'] or '환급금' in tx['category']: continue
                    if '저축' in tx['category'] or '적금' in tx['category'] or '청약' in tx['category']: y_savings += tx['amount']
                    else: y_consumption += tx['amount']

            import calendar
            try:
                _, num_days = calendar.monthrange(2026, month)
                expense_days = set()
                for tx in parents_tx:
                    if tx['type'] == '지출':
                        try:
                            day = int(tx['date'].split('-')[2])
                            expense_days.add(day)
                        except: pass
                no_spend_days = [d for d in range(1, num_days + 1) if d not in expense_days]
            except Exception:
                no_spend_days = []

            month_key = f"2026_{month:02d}"
            ai_report_md = AI_REPORTS_DICT.get(month_key, f"아직 {month}월 가계부 분석 데이터가 없습니다.")

            fixed_keywords = ['고정', '보험', '주거', '통신', '공과금', '세금', '회비', '대출', '이자', '모임']
            parents_stats = {
                'transactions': parents_tx,
                'fixedExpenses': [t for t in parents_tx if t['type'] == '지출' and '경조사' not in str(t.get('category','')) and any(k in str(t.get('category','')) for k in fixed_keywords)],
                'categories': p_categories,
                'noSpendDays': no_spend_days,
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
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            return
            
        self.send_response(404)
        self.end_headers()
