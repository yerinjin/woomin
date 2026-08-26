import http.server
import socketserver
import json
import urllib.parse
import os
import zipfile

import urllib.request
import io
import time

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

import xml.etree.ElementTree as ET
import datetime
import unicodedata

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ACCOUNT_BOOK_DIR = "/Users/yerinjin/Desktop/yerincess/1_Yerin's/Account book"

# --- Date conversion helper ---
def excel_date_to_str(excel_date_num):
    try:
        val = float(excel_date_num)
        if val > 60:
            val -= 1
        dt = datetime.date(1899, 12, 30) + datetime.timedelta(days=val)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return str(excel_date_num)

# --- Numbers columns letter helper ---
def get_column_letter(col_idx):
    letter = ""
    while col_idx >= 0:
        letter = chr(col_idx % 26 + 65) + letter
        col_idx = col_idx // 26 - 1
    return letter

# --- Numbers File Parser Adapter ---
def parse_numbers_to_cells_dict(filepath, sheet_name):
    import sys
    user_site = os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages')
    if user_site not in sys.path:
        sys.path.insert(0, user_site)
    
    try:

    data = _parse_excel_ledger_raw(filepath, target_month)
    return data

# --- Unified Excel Parser Router (Raw Logic) ---
def _parse_excel_ledger_raw(file_like, target_month):
    filepath = file_like
    if False:
        import sys
        user_site = os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages')
        if user_site not in sys.path:
            sys.path.insert(0, user_site)
        try:

        if '가계부입력' in sheet_names:
            cells = parse_numbers_to_cells_dict(filepath, '가계부입력')
            return parse_excel_format_b(cells, [], target_month)
        
        target_sheet_name = f"{target_month}월"
        sheet_to_use = None
        if target_sheet_name in sheet_names:
            sheet_to_use = target_sheet_name
        elif f"{target_month}월 결산" in sheet_names:
            sheet_to_use = f"{target_month}월 결산"
            
        if sheet_to_use:
            cells = parse_numbers_to_cells_dict(filepath, sheet_to_use)
            return parse_excel_format_a(cells, [], target_month)
        return []

    try:
        with zipfile.ZipFile(file_like, 'r') as zip_ref:
            # 1. Load shared strings
            shared_strings = []
            try:
                ss_xml = zip_ref.read('xl/sharedStrings.xml')
                ss_root = ET.fromstring(ss_xml)
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for t_elem in ss_root.findall('.//main:t', ns):
                    shared_strings.append(t_elem.text or '')
            except KeyError:
                pass

            # 2. Load workbook relations
            sheets_info = {}
            wb_rels_xml = zip_ref.read('xl/_rels/workbook.xml.rels')
            wb_rels_root = ET.fromstring(wb_rels_xml)
            ns_rel = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            for rel in wb_rels_root.findall('.//rel:Relationship', ns_rel):
                sheets_info[rel.get('Id')] = rel.get('Target')

            # 3. Load sheets list
            workbook_xml = zip_ref.read('xl/workbook.xml')
            wb_root = ET.fromstring(workbook_xml)
            ns_main = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            sheets = {}
            for sheet_elem in wb_root.findall('.//main:sheet', ns_main):
                name = unicodedata.normalize('NFC', sheet_elem.get('name'))
                r_id = sheet_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                sheets[name] = r_id

            # --- ROUTING ---
            if '가계부입력' in sheets:
                r_id = sheets['가계부입력']
                sheet_file = sheets_info.get(r_id, '')
                if not sheet_file.startswith('xl/'):
                    sheet_file = 'xl/' + sheet_file
                cells = get_sheet_cells_dict(zip_ref, sheet_file, shared_strings)
                return parse_excel_format_b(cells, shared_strings, target_month)
            
            target_sheet_name = f"{target_month}월"
            if target_sheet_name in sheets:
                r_id = sheets[target_sheet_name]
                sheet_file = sheets_info.get(r_id, '')
                if not sheet_file.startswith('xl/'):
                    sheet_file = 'xl/' + sheet_file
                cells = get_sheet_cells_dict(zip_ref, sheet_file, shared_strings)
                return parse_excel_format_a(cells, shared_strings, target_month)

            return []

    except Exception as e:
        print(f"Error parsing Excel file {filepath}: {e}")
        return []

# Global Cache for Parents Loan data
LOAN_CACHE = {}

# --- Loan Parser Engine (Cached Wrapper) ---
def parse_parents_loan(sheet_type, month):
    filepath = fetch_google_sheet(sheet_type)
    file_like = filepath
    if not filepath: return None
    try:
        mtime = os.path.getmtime(filepath)
        cache_key = (filepath, month)
        if cache_key in LOAN_CACHE:
            cached = LOAN_CACHE[cache_key]
            if cached['mtime'] == mtime:
                return cached['data']
    except Exception:
        mtime = None

    data = _parse_parents_loan_raw(filepath, month)
    
    if mtime is not None:
        LOAN_CACHE[cache_key] = { 'mtime': mtime, 'data': data }
    return data

def _parse_parents_loan_raw(filepath, month):
    loan_filepath = os.path.join(ACCOUNT_BOOK_DIR, '우민대출금현황.xlsx')
    if os.path.exists(loan_filepath):
        try:
            with zipfile.ZipFile(loan_filepath, 'r') as zip_ref:
                workbook_xml = zip_ref.read('xl/workbook.xml')
                wb_root = ET.fromstring(workbook_xml)
                ns_main = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                sheets = {}
                for sheet_elem in wb_root.findall('.//main:sheet', ns_main):
                    name = sheet_elem.get('name')
                    r_id = sheet_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    sheets[name] = r_id
                
                wb_rels_xml = zip_ref.read('xl/_rels/workbook.xml.rels')
                wb_rels_root = ET.fromstring(wb_rels_xml)
                ns_rel = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                sheets_info = {}
                for rel in wb_rels_root.findall('.//rel:Relationship', ns_rel):
                    sheets_info[rel.get('Id')] = rel.get('Target')
                    
                shared_strings = []
                try:
                    ss_xml = zip_ref.read('xl/sharedStrings.xml')
                    ss_root = ET.fromstring(ss_xml)
                    for si in ss_root.findall('.//main:si', ns_main):
                        t = si.find('.//main:t', ns_main)
                        if t is not None:
                            shared_strings.append(t.text)
                        else:
                            shared_strings.append("")
                except:
                    pass

                sheet_name = list(sheets.keys())[0] # Usually the first sheet
                r_id = sheets[sheet_name]
                sheet_file = sheets_info.get(r_id, '')
                if not sheet_file.startswith('xl/'):
                    sheet_file = 'xl/' + sheet_file
                    
                sheet_xml = zip_ref.read(sheet_file)
                sheet_root = ET.fromstring(sheet_xml)
                
                matched_principal = 0
                matched_interest = 0
                matched_balance = 0
                
                for row in sheet_root.findall('.//main:row', ns_main):
                    row_data = []
                    for c in row.findall('.//main:c', ns_main):
                        t = c.get('t')
                        val_elem = c.find('main:v', ns_main)
                        val = ''
                        if val_elem is not None:
                            val = val_elem.text or ''
                            if t == 's' and val.isdigit():
                                val = shared_strings[int(val)] if int(val) < len(shared_strings) else val
                        row_data.append(val)
                        
                    if len(row_data) > 11 and row_data[1]:
                        try:
                            # Convert Excel date (float) to month
                            excel_date = float(row_data[1])
                            date_obj = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=excel_date)
                            if date_obj.month == month and date_obj.year == 2026:
                                principal = float(row_data[4] or 0)
                                interest = float(row_data[6] or 0)
                                balance = float(row_data[11] or 0)
                                
                                matched_principal += principal
                                matched_interest += interest
                                matched_balance = balance # Keep the latest balance
                        except ValueError:
                            pass
                
                if matched_balance > 0:
                    return {
                        'totalLoan': 217000000.0,
                        'balance': matched_balance,
                        'principal': matched_principal,
                        'interest': matched_interest,
                        'totalPayment': matched_principal + matched_interest
                    }
        except Exception as e:
            print(f"Error parsing loan file: {e}")

    # Fallback default values
    return {
        'totalLoan': 217000000.0,
        'balance': 159222836.0 if month >= 8 else 162461982.0,
        'principal': 144269.0,
        'interest': 598954.0,
        'totalPayment': 743224.0
    }

    try:
        with zipfile.ZipFile(file_like, 'r') as zip_ref:
            workbook_xml = zip_ref.read('xl/workbook.xml')
            wb_root = ET.fromstring(workbook_xml)
            ns_main = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            sheets = {}
            for sheet_elem in wb_root.findall('.//main:sheet', ns_main):
                name = unicodedata.normalize('NFC', sheet_elem.get('name'))
                r_id = sheet_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                sheets[name] = r_id
            
            if '대출1' not in sheets:
                return None
                
            sheets_info = {}
            wb_rels_xml = zip_ref.read('xl/_rels/workbook.xml.rels')
            wb_rels_root = ET.fromstring(wb_rels_xml)
            ns_rel = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            for rel in wb_rels_root.findall('.//rel:Relationship', ns_rel):
                sheets_info[rel.get('Id')] = rel.get('Target')
                
            r_id = sheets['대출1']
            sheet_file = sheets_info.get(r_id, '')
            if not sheet_file.startswith('xl/'):
                sheet_file = 'xl/' + sheet_file
                
            cells = get_sheet_cells_dict(zip_ref, sheet_file, [])
            rows = {}
            for ref, val in cells.items():
                r_idx = int(''.join(filter(str.isdigit, ref)) or 0)
                c_idx = ''.join(filter(str.isalpha, ref))
                if r_idx not in rows:
                    rows[r_idx] = {}
                rows[r_idx][c_idx] = val
                
            for r in sorted(rows.keys()):
                r_data = rows[r]
                b_val = r_data.get('B', '')
                try:
                    b_float = float(b_val)
                    if int(b_float) == month:
                        principal = float(r_data.get('D', '0') or 0)
                        interest = float(r_data.get('E', '0') or 0)
                        total_pay = float(r_data.get('F', '0') or 0)
                        balance = float(r_data.get('H', '0') or 0)
                        return {
                            'totalLoan': 217000000.0,
                            'balance': balance,
                            'principal': principal,
                            'interest': interest,
                            'totalPayment': total_pay or (principal + interest)
                        }
                except ValueError:
                    pass
            
            return {
                'totalLoan': 217000000.0,
                'balance': 159222836.0 if month >= 8 else 162461982.0,
                'principal': 144269.0,
                'interest': 598954.0,
                'totalPayment': 743224.0
            }
    except Exception as e:
        print(f"Error parsing parents loan: {e}")
        return None

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
                    if t == 's':
                        val = shared_strings[int(val)]
                cells[ref] = val
        return cells
    except Exception:
        return {}


# --- Markdown Parser (Format A - Monthly Sheets with Side-by-Side Tables) ---
def parse_markdown_ledger(filepath, target_month):
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        section_header = f"### {target_month}월"
        if section_header not in content:
            return []

        parts = content.split(section_header)
        section_content = parts[1].split('###')[0]

        transactions = []
        for line in section_content.split('\n'):
            line = line.strip()
            if not line.startswith('|') or '◀' in line or '날짜' in line or '---' in line:
                continue

            cols = [c.strip() for c in line.split('|')]
            if len(cols) < 18:
                continue

            inc_date = cols[2]
            if inc_date and '-' in inc_date and cols[3] == '수입':
                try:
                    amount = float(cols[8] or 0)
                    if amount > 0:
                        transactions.append({
                            'date': inc_date.split(' ')[0],
                            'type': '수입',
                            'category': cols[4] or '수입기타',
                            'subcategory': cols[5] or '',
                            'desc': cols[6] or '',
                            'account': '계좌이체',
                            'amount': amount,
                            'detail': ''
                        })
                except Exception:
                    pass

            exp_date = cols[9]
            if exp_date and '-' in exp_date and cols[11] and not cols[11].isdigit():
                try:
                    amount = float(cols[17] or cols[15] or 0)
                    if amount > 0:
                        transactions.append({
                            'date': exp_date.split(' ')[0],
                            'type': '지출',
                            'category': cols[11] or '기타',
                            'subcategory': cols[12] or '',
                            'desc': cols[13] or '',
                            'account': cols[10] or '계좌이체',
                            'amount': amount,
                            'detail': cols[18] or ''
                        })
                except Exception:
                    pass

        return transactions
    except Exception as e:
        print(f"Error parsing Markdown file {filepath}: {e}")
        return []


# --- Cross-Checking Logic ---
def cross_check_transactions(yerin_tx, parents_tx):
    matched = []
    unmatched_yerin = []
    unmatched_parents = []

    yerin_candidates = []
    for tx in yerin_tx:
        desc = tx['desc'].lower()
        cat = tx['category'].lower()
        if tx['type'] == '지출':
            if '부모님' in desc or '용돈' in desc or '엄마' in desc or '아빠' in desc or '대신결제' in desc or '모임' in cat:
                yerin_candidates.append(('yerin_out', tx))
        elif tx['type'] == '수입':
            if '대신결제' in desc or '회수' in desc or '상환' in desc or '아빠' in desc or '엄마' in desc:
                yerin_candidates.append(('yerin_in', tx))

    parents_candidates = []
    for tx in parents_tx:
        desc = tx['desc'].lower()
        cat = tx['category'].lower()
        if tx['type'] == '지출':
            if '예린' in desc or '대리' in desc or '상환' in desc or '용돈' in desc or '딸' in desc:
                parents_candidates.append(('parents_out', tx))
        elif tx['type'] == '수입':
            if '예린' in desc or '생활비' in desc or '용돈' in desc or '딸' in desc:
                parents_candidates.append(('parents_in', tx))

    used_parents = set()

    for idx_y, (direction_y, tx_y) in enumerate(yerin_candidates):
        found = False
        date_y = datetime.datetime.strptime(tx_y['date'], '%Y-%m-%d')
        amount_y = tx_y['amount']

        for idx_p, (direction_p, tx_p) in enumerate(parents_candidates):
            if idx_p in used_parents:
                continue

            match_direction = (
                (direction_y == 'yerin_out' and direction_p == 'parents_in') or
                (direction_y == 'yerin_in' and direction_p == 'parents_out')
            )

            if not match_direction:
                continue

            date_p = datetime.datetime.strptime(tx_p['date'], '%Y-%m-%d')
            amount_p = tx_p['amount']

            date_diff = abs((date_y - date_p).days)
            if date_diff <= 3 and abs(amount_y - amount_p) < 10:
                used_parents.add(idx_p)
                matched.append({
                    'type': '용돈/생활비' if '생활비' in tx_y['desc'] or '용돈' in tx_y['desc'] else '대신결제 정산',
                    'date': tx_y['date'],
                    'amount': amount_y,
                    'yerin': { 'desc': tx_y['desc'], 'type': tx_y['type'], 'account': tx_y['account'] },
                    'parents': { 'desc': tx_p['desc'], 'type': tx_p['type'], 'account': tx_p['account'] }
                })
                found = True
                break

        if not found:
            unmatched_yerin.append(tx_y)

    for idx_p, (direction_p, tx_p) in enumerate(parents_candidates):
        if idx_p not in used_parents:
            unmatched_parents.append(tx_p)

    return {
        'matched': matched,
        'unmatched_yerin': unmatched_yerin,
        'unmatched_parents': unmatched_parents
    }


class handler(http.server.BaseHTTPRequestHandler):
    def translate_path(self, path):
        root = os.path.join(DIRECTORY, 'public')
        if not os.path.exists(root):
            os.makedirs(root)

        parsed = urllib.parse.urlparse(path)
        rel_path = parsed.path.lstrip('/')
        if not rel_path:
            rel_path = 'index.html'

        return os.path.join(root, rel_path)

    
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        # --- NEW API: Yearly Trend Data ---
        if parsed_url.path == '/api/yearly-trend':
            trend_data = []
            for m in range(1, 13):
                # We use the main Google sheet for parents
                txs = parse_excel_ledger("parents", m)
                if not txs and m <= 4:
                    txs = parse_excel_ledger("parents_past", m)
                    
                income = 0
                consumption = 0
                savings = 0
                
                if txs:
                    for tx in txs:
                        if tx['type'] == '수입':
                            income += tx['amount']
                        elif tx['type'] == '지출':
                            if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']:
                                continue
                            if '저축' in tx['category'] or '예적금' in tx['category'] or '청약' in tx['category'] or '적금' in tx['category']:
                                savings += tx['amount']
                            else:
                                consumption += tx['amount']
                                
                trend_data.append({
                    'month': m,
                    'income': income,
                    'consumption': consumption,
                    'savings': savings,
                    'balance': income - consumption - savings
                })
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(trend_data, ensure_ascii=False).encode('utf-8'))

        # --- API: Monthly Data ---
        elif parsed_url.path == '/api/data':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            month = int(query_params.get('month', [8])[0])

            selected_parents_path = "parents"
            if month <= 4:
                selected_parents_path = "parents_past"
                
            yerin_xlsx_path = "yerin"
            if month <= 4:
                yerin_xlsx_path = "yerin_past"

            parents_tx = parse_excel_ledger(selected_parents_path, month)
            yerin_tx = parse_excel_ledger(yerin_xlsx_path, month)

            # --- Extract Summaries ---
            p_income = 0
            p_consumption = 0
            p_savings = 0
            for tx in parents_tx:
                if tx['type'] == '수입': p_income += tx['amount']
                elif tx['type'] == '지출':
                    if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                    if '저축' in tx['category'] or '적금' in tx['category'] or '청약' in tx['category']: p_savings += tx['amount']
                    else: p_consumption += tx['amount']

            y_income = 0
            y_consumption = 0
            y_savings = 0
            for tx in yerin_tx:
                if tx['type'] == '수입': y_income += tx['amount']
                elif tx['type'] == '지출':
                    if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']: continue
                    if '저축' in tx['category'] or '적금' in tx['category'] or '청약' in tx['category']: y_savings += tx['amount']
                    else: y_consumption += tx['amount']

            parents_stats = {
                'transactions': parents_tx,
                'fixedExpenses': [t for t in parents_tx if t['type'] == '지출' and ('고정' in str(t.get('category','')) or '보험' in str(t.get('category','')))],
                'categories': {},
                'noSpendDays': [],
                'summary': { 'income': p_income, 'consumption': p_consumption, 'savings': p_savings, 'balance': p_income - p_consumption - p_savings },
                'loan': parse_parents_loan(selected_parents_path, month)
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
                'ai_report': None,
                'crossCheck': []
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
