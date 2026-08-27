import http.server
import socketserver
import json
import urllib.parse
import os
import zipfile
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
        import numbers_parser
    except ImportError:
        print("numbers-parser library is not installed.")
        return {}

    try:
        doc = numbers_parser.Document(filepath)
        target_sheet = None
        for s in doc.sheets:
            if unicodedata.normalize('NFC', s.name) == unicodedata.normalize('NFC', sheet_name):
                target_sheet = s
                break
        if not target_sheet:
            return {}

        table = target_sheet.tables[0]
        cells = {}
        for r_idx, row_values in enumerate(table.iter_rows(values_only=True)):
            for c_idx, val in enumerate(row_values):
                if val is not None:
                    if isinstance(val, (datetime.datetime, datetime.date)):
                        val = val.strftime('%Y-%m-%d')
                    elif isinstance(val, float):
                        if val.is_integer():
                            val = int(val)
                    
                    col_letter = get_column_letter(c_idx)
                    cells[f"{col_letter}{r_idx+1}"] = val
        return cells
    except Exception as e:
        print(f"Error parsing Numbers file {filepath}: {e}")
        return {}

# --- Excel Parser (Format B - Flat 가계부입력 Sheet) ---
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
        if r <= 7: # Header is at row 7
            continue
        r_data = rows[r]
        date_val = r_data.get('B', '')
        date_str = excel_date_to_str(date_val)
        if not date_str or '-' not in date_str:
            continue

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

# --- Excel Parser (Format A - Monthly Sheets with Side-by-Side Tables) ---
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
        if r <= 30: # Skip calendar visual grid
            continue
        r_data = rows[r]

        # 1. Parse Income side (Cols B-H)
        inc_date_val = r_data.get('B', '')
        inc_date = excel_date_to_str(inc_date_val)
        if inc_date and '-' in inc_date and r_data.get('C') == '수입':
            try:
                amount = float(r_data.get('H', '0') or 0)
                if amount > 0:
                    subcategory = r_data.get('E', '').strip()
                    desc = r_data.get('F', '').strip()
                    # UI filtering for calendar arrows
                    if subcategory in ['◀', '▶']:
                        subcategory = ''
                        
                    transactions.append({
                        'date': inc_date,
                        'type': '수입',
                        'category': r_data.get('D', '').strip() or '수입기타',
                        'subcategory': subcategory,
                        'desc': desc,
                        'account': '계좌이체',
                        'amount': amount,
                        'detail': ''
                    })
            except Exception:
                pass

        # 2. Parse Expense side (Cols J-S)
        exp_date_val = r_data.get('J', '')
        exp_date = excel_date_to_str(exp_date_val)
        if exp_date and '-' in exp_date and r_data.get('L'):
            try:
                amount = float(r_data.get('R', r_data.get('P', '0')) or 0)
                if amount > 0:
                    subcategory = r_data.get('M', '').strip()
                    desc = r_data.get('N', '').strip()
                    # UI filtering for calendar arrows
                    if subcategory in ['◀', '▶']:
                        subcategory = ''
                    if desc in ['◀', '▶']:
                        desc = ''
                        
                    transactions.append({
                        'date': exp_date,
                        'type': '지출',
                        'category': r_data.get('L', '').strip() or '기타',
                        'subcategory': subcategory,
                        'desc': desc,
                        'account': r_data.get('K', '').strip() or '계좌이체',
                        'amount': amount,
                        'detail': r_data.get('S', '').strip()
                    })
            except Exception:
                pass

    return transactions

# Global Cache for Parsed Ledgers to prevent slow snappy/protobuf load on every request
LEDGER_CACHE = {}

# --- Unified Excel Parser Router (Cached Wrapper) ---
def parse_excel_ledger(filepath, target_month):
    if not os.path.exists(filepath):
        return []
    try:
        mtime = os.path.getmtime(filepath)
        cache_key = (filepath, target_month)
        if cache_key in LEDGER_CACHE:
            cached = LEDGER_CACHE[cache_key]
            if cached['mtime'] == mtime:
                return cached['data']
    except Exception:
        mtime = None

    data = _parse_excel_ledger_raw(filepath, target_month)
    
    if mtime is not None:
        LEDGER_CACHE[cache_key] = { 'mtime': mtime, 'data': data }
    return data

# --- Unified Excel Parser Router (Raw Logic) ---
def _parse_excel_ledger_raw(filepath, target_month):
    if not os.path.exists(filepath):
        return []

    if filepath.endswith('.numbers'):
        import sys
        user_site = os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages')
        if user_site not in sys.path:
            sys.path.insert(0, user_site)
        try:
            import numbers_parser
            doc = numbers_parser.Document(filepath)
            sheet_names = [unicodedata.normalize('NFC', s.name) for s in doc.sheets]
        except Exception as e:
            print(f"Error inspecting Numbers file {filepath}: {e}")
            return []

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
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            # 1. Load shared strings
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
def parse_parents_loan(filepath, month):
    if not os.path.exists(filepath):
        return None
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
                        text_parts = []
                        for t in si.findall('.//main:t', ns_main):
                            text_parts.append(t.text or '')
                        shared_strings.append(''.join(text_parts))
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
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
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


class DashboardAPIHandler(http.server.SimpleHTTPRequestHandler):
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
        
        # --- Authentication Logic ---
        if self.path.startswith('/parents.html'):
            import base64
            auth_header = self.headers.get('Authorization')
            # Base64 encode for "woomin:1234"
            expected_auth = "Basic " + base64.b64encode(b"woomin:1234").decode('utf-8')
            
            if auth_header != expected_auth:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Parents Dashboard Authentication Required"')
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"Unauthorized. ID and Password required.")
                return

        # --- NEW API: Yearly Trend Data ---
        if parsed_url.path == '/api/yearly-trend':
            new_parents_path = os.path.join(ACCOUNT_BOOK_DIR, "2026 우민 가계부.numbers")
            parents_xlsx_path = os.path.join(ACCOUNT_BOOK_DIR, "2026년 우민 가계부_삼성.xlsx")
            
            for f in os.listdir(ACCOUNT_BOOK_DIR):
                normalized_name = unicodedata.normalize('NFC', f)
                if "우민" in normalized_name and "가계부" in normalized_name:
                    if f.endswith(".xlsx") or f.endswith(".numbers"):
                        if "삼성" not in normalized_name:
                            new_parents_path = os.path.join(ACCOUNT_BOOK_DIR, f)
                        else:
                            parents_xlsx_path = os.path.join(ACCOUNT_BOOK_DIR, f)
            
            selected_parents_path = new_parents_path if os.path.exists(new_parents_path) else parents_xlsx_path
            
            trend_data = []
            for m in range(1, 13):
                txs = parse_excel_ledger(selected_parents_path, m)
                if not txs and m <= 4 and parents_xlsx_path and os.path.exists(parents_xlsx_path):
                    txs = parse_excel_ledger(parents_xlsx_path, m)
                    
                income = 0
                consumption = 0
                savings = 0
                
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

            # 1. Load Yerin's data
            yerin_md_path = os.path.join(ACCOUNT_BOOK_DIR, "2026_진예린 8월 중순가계부_전체.md")
            yerin_xlsx_path = os.path.join(ACCOUNT_BOOK_DIR, "2026년 진예린 가계부_삼성.xlsx")
            new_yerin_path = os.path.join(ACCOUNT_BOOK_DIR, "2026 진예린 가계부.xlsx")
            
            for f in os.listdir(ACCOUNT_BOOK_DIR):
                normalized_name = unicodedata.normalize('NFC', f)
                if "진예린" in normalized_name and "가계부" in normalized_name:
                    if f.endswith(".md") and "8월" in normalized_name:
                        yerin_md_path = os.path.join(ACCOUNT_BOOK_DIR, f)
                    elif f.endswith(".xlsx") or f.endswith(".numbers"):
                        if "삼성" not in normalized_name:
                            new_yerin_path = os.path.join(ACCOUNT_BOOK_DIR, f)
                        else:
                            yerin_xlsx_path = os.path.join(ACCOUNT_BOOK_DIR, f)
                            
            selected_yerin_path = new_yerin_path if os.path.exists(new_yerin_path) else yerin_xlsx_path
            
            yerin_tx = []
            if os.path.exists(yerin_md_path):
                print(f"Parsing Yerin's MD ledger for month {month}")
                yerin_tx = parse_markdown_ledger(yerin_md_path, month)
            
            if not yerin_tx and os.path.exists(selected_yerin_path):
                print(f"Parsing Yerin's Excel ledger: {os.path.basename(selected_yerin_path)} for month {month}")
                yerin_tx = parse_excel_ledger(selected_yerin_path, month)
                
            if not yerin_tx and month <= 4 and yerin_xlsx_path and os.path.exists(yerin_xlsx_path):
                print(f"Parsing Yerin's Legacy ledger: {os.path.basename(yerin_xlsx_path)} for month {month}")
                yerin_tx = parse_excel_ledger(yerin_xlsx_path, month)

            # 2. Load Parents' data
            parents_xlsx_path = os.path.join(ACCOUNT_BOOK_DIR, "2026년 우민 가계부_삼성.xlsx")
            new_parents_path = os.path.join(ACCOUNT_BOOK_DIR, "2026 우민 가계부.numbers")
            
            for f in os.listdir(ACCOUNT_BOOK_DIR):
                normalized_name = unicodedata.normalize('NFC', f)
                if "우민" in normalized_name and "가계부" in normalized_name:
                    if f.endswith(".xlsx") or f.endswith(".numbers"):
                        if "삼성" not in normalized_name:
                            new_parents_path = os.path.join(ACCOUNT_BOOK_DIR, f)
                        else:
                            parents_xlsx_path = os.path.join(ACCOUNT_BOOK_DIR, f)

            selected_parents_path = new_parents_path if os.path.exists(new_parents_path) else parents_xlsx_path
            print(f"Parsing Parents' Excel ledger: {os.path.basename(selected_parents_path)} for month {month}")
            parents_tx = parse_excel_ledger(selected_parents_path, month)

            # Process stats helper
            def calculate_stats(txs):
                income = 0
                consumption = 0
                savings = 0
                
                categories = {
                    '식비': 0, '교통/차량': 0, '주거/통신': 0, '건강/의료': 0, 
                    '쇼핑': 0, '여가/취미': 0, '모임': 0, '경조사/선물': 0, 
                    '저축': 0, '기타': 0
                }
                
                fixed_keywords = ['보험', '대출', '통신', '가스', '전기', '관리비', '정수기', '인터넷', '구독', '할부']
                fixed_expenses = []

                if not txs:
                    return {
                        'summary': {'income': 0, 'consumption': 0, 'savings': 0, 'balance': 0, 'savingsRate': 0},
                        'categories': categories,
                        'noSpendDays': [],
                        'transactions': [],
                        'fixedExpenses': []
                    }

                days_in_month = 31 # Approximation
                no_spend_days = set(range(1, days_in_month + 1))

                for tx in txs:
                    try:
                        date_obj = datetime.datetime.strptime(tx['date'], '%Y-%m-%d')
                        day = date_obj.day
                    except ValueError:
                        day = int(tx['date'].split('-')[-1]) if '-' in tx['date'] else 1

                    amount = tx['amount']
                    desc = tx['desc']
                    category = tx['category']
                    subcategory = tx.get('subcategory', '')
                    
                    if tx['type'] == '수입':
                        income += amount
                    elif tx['type'] == '지출':
                        # Check for fixed expense
                        combined_text = f"{category} {subcategory} {desc}".strip()
                        if any(kw in combined_text for kw in fixed_keywords):
                            fixed_expenses.append(tx)
                            
                        if '카드대금' in tx['category'] or '카드값' in tx['desc'] or '전월카드값' in tx['desc']:
                            continue

                        if '저축' in tx['category'] or '예적금' in tx['category'] or '청약' in tx['category'] or '적금' in tx['category']:
                            savings += amount
                        else:
                            consumption += amount
                            cat = tx['category']
                            mapped = False
                            for c_key in categories.keys():
                                if c_key in cat or cat in c_key:
                                    categories[c_key] += amount
                                    mapped = True
                                    break
                            if not mapped:
                                categories['기타'] += amount
                            
                            if day in no_spend_days:
                                no_spend_days.remove(day)

                balance = income - consumption - savings
                savings_rate = (savings / income * 100) if income > 0 else 0

                return {
                    'summary': {
                        'income': income,
                        'consumption': consumption,
                        'savings': savings,
                        'balance': balance,
                        'savingsRate': round(savings_rate, 1)
                    },
                    'categories': categories,
                    'noSpendDays': sorted(list(no_spend_days)),
                    'transactions': txs,
                    'fixedExpenses': fixed_expenses
                }

            yerin_stats = calculate_stats(yerin_tx)
            
            # Handle fallback
            is_fallback = False
            fallback_month = month
            if not parents_tx:
                fallback_tx = parse_excel_ledger(selected_parents_path, 3)
                if fallback_tx:
                    parents_stats = calculate_stats(fallback_tx)
                    is_fallback = True
                    fallback_month = 3
                else:
                    parents_stats = calculate_stats([])
            else:
                parents_stats = calculate_stats(parents_tx)

            parents_stats['isFallback'] = is_fallback
            parents_stats['fallbackMonth'] = fallback_month

            # Cross check
            parent_tx_for_cc = parents_tx if parents_tx else (parse_excel_ledger(selected_parents_path, fallback_month) if is_fallback else [])
            cross_check_results = cross_check_transactions(yerin_tx, parent_tx_for_cc)

            # Load parents' loan details
            parents_stats['loan'] = parse_parents_loan(selected_parents_path, fallback_month if is_fallback else month)

            # Load AI Report for the month if exists
            ai_report = None
            ai_report_path = os.path.join(ACCOUNT_BOOK_DIR, "AI_Reports", f"2026_{month:02d}_Monthly_Analysis.md")
            if os.path.exists(ai_report_path):
                with open(ai_report_path, 'r', encoding='utf-8') as f:
                    ai_report = f.read()

            response_data = {
                'month': month,
                'yerin': yerin_stats,
                'parents': parents_stats,
                'ai_report': ai_report,
                'crossCheck': cross_check_results
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def run():
    print(f"Starting Antigravity Household Account Dashboard at http://localhost:{PORT}")
    server_address = ('', PORT)
    httpd = ThreadingSimpleServer(server_address, DashboardAPIHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run()
