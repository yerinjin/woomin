import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import os
import zipfile
import xml.etree.ElementTree as ET
import datetime
import unicodedata
import io
import time
import base64

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


PORTFOLIO_CACHE = {'time': 0, 'data': None}

def fetch_live_portfolio():
    global PORTFOLIO_CACHE
    now = time.time()
    if PORTFOLIO_CACHE['data'] and (now - PORTFOLIO_CACHE['time'] < 60):
        return PORTFOLIO_CACHE['data']

    kr_codes = ["042660", "466920", "009830", "360750", "133690", "453850", "219480", "449180", "086960", "255220", "025340"]
    kr_quotes = {}
    try:
        code_str = ",".join(kr_codes)
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code_str}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res_bytes = urllib.request.urlopen(req, timeout=3).read()
        text = res_bytes.decode("euc-kr", errors="ignore")
        data = json.loads(text)
        for item in data.get("result", {}).get("areas", [])[0].get("datas", []):
            cd = item.get("cd")
            nv = float(item.get("nv", 0) or 0)
            cr = float(item.get("cr", 0) or 0)
            kr_quotes[cd] = {"price": nv, "changeRate": cr}
    except Exception as e:
        print(f"Naver error: {e}")

    us_symbols = ["USDKRW=X", "NVDA", "INTC", "RZLV", "SDGR", "BBAI", "LAES", "FLNC", "ARBE", "QSI", "RXRX", "QQQ", "MSFT", "MCD", "TSLA"]
    us_quotes = {}
    for sym in us_symbols:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            res = urllib.request.urlopen(req, timeout=2).read()
            data = json.loads(res)
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0
            us_quotes[sym] = {"price": price, "change": change, "changePercent": round(change_pct, 2)}
        except Exception as e:
            us_quotes[sym] = {"price": None, "error": str(e)}

    rate = us_quotes.get("USDKRW=X", {}).get("price") or 1335.98

    # Pension
    p_busan_val = 2906010; p_busan_cost = 2870059
    p_ace_sp_shares = 190; p_ace_sp_cost = 2598250
    p_ace_sp_price = kr_quotes.get("453850", {}).get("price")
    if not p_ace_sp_price or p_ace_sp_price < 10000: p_ace_sp_price = 13695.0
    p_ace_sp_val = p_ace_sp_shares * p_ace_sp_price

    p_kodex_sp_shares = 87; p_kodex_sp_cost = 1468125
    p_kodex_sp_price = kr_quotes.get("449180", {}).get("price") or 17150.0
    p_kodex_sp_val = p_kodex_sp_shares * p_kodex_sp_price

    p_ace_nas_shares = 75; p_ace_nas_cost = 1108125
    p_ace_nas_price = 14840.0
    p_ace_nas_val = p_ace_nas_shares * p_ace_nas_price

    p_cash_val = 1447580; p_cash_cost = 1446699

    pension_total_val = p_busan_val + p_ace_sp_val + p_kodex_sp_val + p_ace_nas_val + p_cash_val
    pension_total_cost = p_busan_cost + p_ace_sp_cost + p_kodex_sp_cost + p_ace_nas_cost + p_cash_cost
    pension_profit = pension_total_val - pension_total_cost
    pension_return_pct = round((pension_profit / pension_total_cost * 100), 2)

    # Kakao
    k_nas_price = kr_quotes.get("133690", {}).get("price") or 26165.0
    if k_nas_price > 50000: k_nas_price = 26165.0
    k_nas_val = 26 * k_nas_price; k_nas_cost = 610340

    nvda_usd = us_quotes.get("NVDA", {}).get("price") or 225.73
    k_nvda_val = 1.5 * nvda_usd * rate; k_nvda_cost = 391312

    sol_price = kr_quotes.get("466920", {}).get("price") or 28350.0
    k_sol_val = 4 * sol_price; k_sol_cost = 141900

    qqq_usd = us_quotes.get("QQQ", {}).get("price") or 718.36
    msft_usd = us_quotes.get("MSFT", {}).get("price") or 493.95
    mcd_usd = us_quotes.get("MCD", {}).get("price") or 255.81
    tsla_usd = us_quotes.get("TSLA", {}).get("price") or 368.16
    k_fractional_val = (0.072 * qqq_usd + 0.025 * msft_usd + 0.008 * mcd_usd + 0.0042 * tsla_usd) * rate
    k_fractional_cost = 85000

    kakao_val = k_nas_val + k_nvda_val + k_sol_val + k_fractional_val
    kakao_cost = k_nas_cost + k_nvda_cost + k_sol_cost + k_fractional_cost

    # Toss US
    intc_usd = us_quotes.get("INTC", {}).get("price") or 104.47
    t_intc_val = 2 * intc_usd * rate; t_intc_cost = 114934

    rzlv_usd = us_quotes.get("RZLV", {}).get("price") or 2.31
    t_rzlv_val = 53 * rzlv_usd * rate; t_rzlv_cost = 328046

    sdgr_usd = us_quotes.get("SDGR", {}).get("price") or 20.03
    t_sdgr_val = 2 * sdgr_usd * rate; t_sdgr_cost = 57560

    bbai_usd = us_quotes.get("BBAI", {}).get("price") or 2.92
    laes_usd = us_quotes.get("LAES", {}).get("price") or 2.45
    flnc_usd = us_quotes.get("FLNC", {}).get("price") or 11.04
    arbe_usd = us_quotes.get("ARBE", {}).get("price") or 0.7431
    qsi_usd = us_quotes.get("QSI", {}).get("price") or 0.76
    rxrx_usd = us_quotes.get("RXRX", {}).get("price") or 3.44
    t_sm_val = (12 * bbai_usd + 10 * laes_usd + 2 * flnc_usd + 24 * arbe_usd + 20 * qsi_usd + 4 * rxrx_usd) * rate
    t_sm_cost = 160882

    toss_us_val = t_intc_val + t_rzlv_val + t_sdgr_val + t_sm_val
    toss_us_cost = t_intc_cost + t_rzlv_cost + t_sdgr_cost + t_sm_cost

    # Toss KR
    h_ocean_price = kr_quotes.get("042660", {}).get("price") or 88100.0
    t_ocean_val = 1 * h_ocean_price; t_ocean_cost = 78000
    t_sol_val = 2 * sol_price; t_sol_cost = 59400
    h_sol_price = kr_quotes.get("009830", {}).get("price") or 30800.0
    t_hsol_val = 1 * h_sol_price; t_hsol_cost = 30700
    sp500_price = kr_quotes.get("360750", {}).get("price") or 25460.0
    t_sp500_val = 1 * sp500_price; t_sp500_cost = 22400
    t_others_val = 39659; t_others_cost = 48880

    toss_kr_val = t_ocean_val + t_sol_val + t_hsol_val + t_sp500_val + t_others_val
    toss_kr_cost = t_ocean_cost + t_sol_cost + t_hsol_cost + t_sp500_cost + t_others_cost

    total_stocks_val = kakao_val + toss_us_val + toss_kr_val
    total_stocks_cost = kakao_cost + toss_us_cost + toss_kr_cost

    payload = {
        "rate": rate,
        "updated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "pension": {
            "total_val": round(pension_total_val),
            "total_cost": round(pension_total_cost),
            "profit": round(pension_profit),
            "return_pct": pension_return_pct,
            "items": [
                {"name": "부산은행 정기예금 (1년) 2건", "val": p_busan_val, "cost": p_busan_cost, "return_pct": 1.25},
                {"name": "한국투자 ACE S&P500 미국채혼합 (190주)", "val": round(p_ace_sp_val), "cost": p_ace_sp_cost, "price": p_ace_sp_price, "return_pct": round((p_ace_sp_val - p_ace_sp_cost)/p_ace_sp_cost*100, 2)},
                {"name": "삼성 KODEX 미국S&P500 (H) (87주)", "val": round(p_kodex_sp_val), "cost": p_kodex_sp_cost, "price": p_kodex_sp_price, "return_pct": round((p_kodex_sp_val - p_kodex_sp_cost)/p_kodex_sp_cost*100, 2)},
                {"name": "한국투자 ACE 나스닥100 미국채혼합 (75주)", "val": round(p_ace_nas_val), "cost": p_ace_nas_cost, "price": p_ace_nas_price, "return_pct": round((p_ace_nas_val - p_ace_nas_cost)/p_ace_nas_cost*100, 2)},
                {"name": "현금성자산 기업적립금", "val": p_cash_val, "cost": p_cash_cost, "return_pct": 0.06}
            ]
        },
        "stocks": {
            "total_val": round(total_stocks_val),
            "total_cost": round(total_stocks_cost),
            "profit": round(total_stocks_val - total_stocks_cost),
            "return_pct": round((total_stocks_val - total_stocks_cost)/total_stocks_cost*100, 2),
            "brokerage": "미래에셋증권 (통합)",
            "items": [
                {"name": "KODEX 미국나스닥100", "shares": "26주", "val": round(k_nas_val), "price": k_nas_price, "cost": k_nas_cost, "return_pct": round((k_nas_val - k_nas_cost)/k_nas_cost*100, 2), "cat": "미국 대표 지수 ETF"},
                {"name": "엔비디아 (NVDA)", "shares": "1.5주", "val": round(k_nvda_val), "price_usd": nvda_usd, "cost": k_nvda_cost, "return_pct": round((k_nvda_val - k_nvda_cost)/k_nvda_cost*100, 2), "cat": "미국 글로벌 AI 대장주"},
                {"name": "인텔 (INTC)", "shares": "2주", "val": round(t_intc_val), "price_usd": intc_usd, "cost": t_intc_cost, "return_pct": round((t_intc_val - t_intc_cost)/t_intc_cost*100, 2), "cat": "미국 반도체 (대박 수익)"},
                {"name": "SOL 조선TOP3플러스", "shares": "6주", "val": round(k_sol_val + t_sol_val), "price": sol_price, "cost": k_sol_cost + t_sol_cost, "return_pct": round(((k_sol_val + t_sol_val) - (k_sol_cost + t_sol_cost))/(k_sol_cost + t_sol_cost)*100, 2), "cat": "국내 조선 대표 ETF"},
                {"name": "한화오션", "shares": "1주", "val": round(t_ocean_val), "price": h_ocean_price, "cost": t_ocean_cost, "return_pct": round((t_ocean_val - t_ocean_cost)/t_ocean_cost*100, 2), "cat": "국내 조선·방산"},
                {"name": "리졸브 AI (RZLV)", "shares": "53주", "val": round(t_rzlv_val), "price_usd": rzlv_usd, "cost": t_rzlv_cost, "return_pct": round((t_rzlv_val - t_rzlv_cost)/t_rzlv_cost*100, 2), "cat": "미국 AI 이커머스"},
                {"name": "슈뢰딩거 (SDGR)", "shares": "2주", "val": round(t_sdgr_val), "price_usd": sdgr_usd, "cost": t_sdgr_cost, "return_pct": round((t_sdgr_val - t_sdgr_cost)/t_sdgr_cost*100, 2), "cat": "미국 AI 바이오"},
                {"name": "TIGER 미국S&P500", "shares": "1주", "val": round(t_sp500_val), "price": sp500_price, "cost": t_sp500_cost, "return_pct": round((t_sp500_val - t_sp500_cost)/t_sp500_cost*100, 2), "cat": "미국 S&P500 ETF"},
                {"name": "한화솔루션", "shares": "1주", "val": round(t_hsol_val), "price": h_sol_price, "cost": t_hsol_cost, "return_pct": round((t_hsol_val - t_hsol_cost)/t_hsol_cost*100, 2), "cat": "국내 친환경"},
                {"name": "QQQ / MSFT / MCD / TSLA", "shares": "소수점", "val": round(k_fractional_val), "cost": k_fractional_cost, "return_pct": round((k_fractional_val - k_fractional_cost)/k_fractional_cost*100, 2), "cat": "미국 우량주 분산"},
                {"name": "빅베어 AI / 실SQ / 플루언스 등", "shares": "성장 6종", "val": round(t_sm_val), "cost": t_sm_cost, "return_pct": round((t_sm_val - t_sm_cost)/t_sm_cost*100, 2), "cat": "미국 AI·로보틱스"}
            ],
            "kakao": {
                "val": round(kakao_val),
                "items": [
                    {"name": "KODEX 미국나스닥100", "shares": 26, "val": round(k_nas_val), "price": k_nas_price, "cost": k_nas_cost, "return_pct": round((k_nas_val - k_nas_cost)/k_nas_cost*100, 2)},
                    {"name": "엔비디아 (NVDA)", "shares": 1.5, "val": round(k_nvda_val), "price_usd": nvda_usd, "cost": k_nvda_cost, "return_pct": round((k_nvda_val - k_nvda_cost)/k_nvda_cost*100, 2)},
                    {"name": "SOL 조선TOP3플러스", "shares": 4, "val": round(k_sol_val), "price": sol_price, "cost": k_sol_cost, "return_pct": round((k_sol_val - k_sol_cost)/k_sol_cost*100, 2)},
                    {"name": "QQQ / MSFT / MCD / TSLA", "shares": "소수점", "val": round(k_fractional_val), "cost": k_fractional_cost, "return_pct": round((k_fractional_val - k_fractional_cost)/k_fractional_cost*100, 2)}
                ]
            },
            "toss_us": {
                "val": round(toss_us_val),
                "items": [
                    {"name": "인텔 (INTC)", "shares": 2, "val": round(t_intc_val), "price_usd": intc_usd, "cost": t_intc_cost, "return_pct": round((t_intc_val - t_intc_cost)/t_intc_cost*100, 2)},
                    {"name": "리졸브 AI (RZLV)", "shares": 53, "val": round(t_rzlv_val), "price_usd": rzlv_usd, "cost": t_rzlv_cost, "return_pct": round((t_rzlv_val - t_rzlv_cost)/t_rzlv_cost*100, 2)},
                    {"name": "슈뢰딩거 (SDGR)", "shares": 2, "val": round(t_sdgr_val), "price_usd": sdgr_usd, "cost": t_sdgr_cost, "return_pct": round((t_sdgr_val - t_sdgr_cost)/t_sdgr_cost*100, 2)},
                    {"name": "빅베어 AI / 실SQ / 플루언스 / 아베 / 퀀텀 / 리커젼", "shares": "소형 6종", "val": round(t_sm_val), "cost": t_sm_cost, "return_pct": round((t_sm_val - t_sm_cost)/t_sm_cost*100, 2)}
                ]
            },
            "toss_kr": {
                "val": round(toss_kr_val),
                "items": [
                    {"name": "한화오션", "shares": 1, "val": round(t_ocean_val), "price": h_ocean_price, "cost": t_ocean_cost, "return_pct": round((t_ocean_val - t_ocean_cost)/t_ocean_cost*100, 2)},
                    {"name": "SOL 조선TOP3플러스", "shares": 2, "val": round(t_sol_val), "price": sol_price, "cost": t_sol_cost, "return_pct": round((t_sol_val - t_sol_cost)/t_sol_cost*100, 2)},
                    {"name": "한화솔루션", "shares": 1, "val": round(t_hsol_val), "price": h_sol_price, "cost": t_hsol_cost, "return_pct": round((t_hsol_val - t_hsol_cost)/t_hsol_cost*100, 2)},
                    {"name": "TIGER 미국S&P500", "shares": 1, "val": round(t_sp500_val), "price": sp500_price, "cost": t_sp500_cost, "return_pct": round((t_sp500_val - t_sp500_cost)/t_sp500_cost*100, 2)},
                    {"name": "셀바스AI / SG / 오리엔탈정공", "shares": "3종", "val": round(t_others_val), "cost": t_others_cost, "return_pct": round((t_others_val - t_others_cost)/t_others_cost*100, 2)}
                ]
            },
            "mirae_items": [
                {"name": "KODEX 미국나스닥100", "shares": "26주", "val": round(k_nas_val), "price": k_nas_price, "cost": k_nas_cost, "return_pct": round((k_nas_val - k_nas_cost)/k_nas_cost*100, 2), "cat": "미국 대표 지수 ETF"},
                {"name": "엔비디아 (NVDA)", "shares": "1.5주", "val": round(k_nvda_val), "price_usd": nvda_usd, "cost": k_nvda_cost, "return_pct": round((k_nvda_val - k_nvda_cost)/k_nvda_cost*100, 2), "cat": "미국 글로벌 AI 대장주"},
                {"name": "인텔 (INTC)", "shares": "2주", "val": round(t_intc_val), "price_usd": intc_usd, "cost": t_intc_cost, "return_pct": round((t_intc_val - t_intc_cost)/t_intc_cost*100, 2), "cat": "미국 반도체 (대박 수익)"},
                {"name": "SOL 조선TOP3플러스", "shares": "6주", "val": round(k_sol_val + t_sol_val), "price": sol_price, "cost": k_sol_cost + t_sol_cost, "return_pct": round(((k_sol_val + t_sol_val) - (k_sol_cost + t_sol_cost))/(k_sol_cost + t_sol_cost)*100, 2), "cat": "국내 조선 대표 ETF"},
                {"name": "한화오션", "shares": "1주", "val": round(t_ocean_val), "price": h_ocean_price, "cost": t_ocean_cost, "return_pct": round((t_ocean_val - t_ocean_cost)/t_ocean_cost*100, 2), "cat": "국내 조선·방산"},
                {"name": "리졸브 AI (RZLV)", "shares": "53주", "val": round(t_rzlv_val), "price_usd": rzlv_usd, "cost": t_rzlv_cost, "return_pct": round((t_rzlv_val - t_rzlv_cost)/t_rzlv_cost*100, 2), "cat": "미국 AI 이커머스"},
                {"name": "슈뢰딩거 (SDGR)", "shares": "2주", "val": round(t_sdgr_val), "price_usd": sdgr_usd, "cost": t_sdgr_cost, "return_pct": round((t_sdgr_val - t_sdgr_cost)/t_sdgr_cost*100, 2), "cat": "미국 AI 바이오"},
                {"name": "TIGER 미국S&P500", "shares": "1주", "val": round(t_sp500_val), "price": sp500_price, "cost": t_sp500_cost, "return_pct": round((t_sp500_val - t_sp500_cost)/t_sp500_cost*100, 2), "cat": "미국 S&P500 ETF"},
                {"name": "한화솔루션", "shares": "1주", "val": round(t_hsol_val), "price": h_sol_price, "cost": t_hsol_cost, "return_pct": round((t_hsol_val - t_hsol_cost)/t_hsol_cost*100, 2), "cat": "국내 친환경"},
                {"name": "QQQ / MSFT / MCD / TSLA", "shares": "소수점", "val": round(k_fractional_val), "cost": k_fractional_cost, "return_pct": round((k_fractional_val - k_fractional_cost)/k_fractional_cost*100, 2), "cat": "미국 우량주 분산"},
                {"name": "빅베어 AI / 실SQ / 플루언스 등", "shares": "성장 6종", "val": round(t_sm_val), "cost": t_sm_cost, "return_pct": round((t_sm_val - t_sm_cost)/t_sm_cost*100, 2), "cat": "미국 AI·로보틱스"}
            ]
        }
    }
    PORTFOLIO_CACHE['time'] = now
    PORTFOLIO_CACHE['data'] = payload
    return payload

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

        # --- PORTFOLIO & STOCK LIVE ENDPOINT ---
        if parsed_url.path in ['/api/portfolio', '/api/stock']:
            p_data = fetch_live_portfolio()
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(p_data, ensure_ascii=False).encode('utf-8'))
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
            if os.path.exists(selected_yerin_path):
                yerin_tx = parse_excel_ledger(selected_yerin_path, month)

            if not yerin_tx and os.path.exists(yerin_md_path) and month == 8:
                print(f"Parsing Yerin's MD ledger for month {month}")
                yerin_tx = parse_markdown_ledger(yerin_md_path, month)

            
            if not yerin_tx:
                try:
                    print(f"Fetching Yerin Google Sheet for month {month}...")
                    url = "https://docs.google.com/spreadsheets/d/1Yfj22nvl0bfZhljjxl3YYbedkVW0Vi6OTli6xaSuaPo/export?format=xlsx"
                    req = urllib.request.Request(url)
                    sheet_data = urllib.request.urlopen(req, timeout=5).read()
                    
                    with zipfile.ZipFile(io.BytesIO(sheet_data), 'r') as zip_ref:
                        wb_root = ET.fromstring(zip_ref.read('xl/workbook.xml'))
                        ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                        wb_rels = ET.fromstring(zip_ref.read('xl/_rels/workbook.xml.rels'))
                        ns_rel = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                        sheets_info = {r.get('Id'): r.get('Target') for r in wb_rels.findall('.//rel:Relationship', ns_rel)}
                        
                        ss_xml = zip_ref.read('xl/sharedStrings.xml')
                        ss_root = ET.fromstring(ss_xml)
                        shared_strings = [''.join([t.text or '' for t in si.findall('.//main:t', ns)]) for si in ss_root.findall('.//main:si', ns)]
                        
                        for s in wb_root.findall('.//main:sheet', ns):
                            if s.get('name') == f"{month}월":
                                r_id = s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                                sheet_file = 'xl/' + sheets_info[r_id] if not sheets_info[r_id].startswith('xl/') else sheets_info[r_id]
                                cells = get_sheet_cells_dict(zip_ref, sheet_file, shared_strings)
                                
                                rows = {}
                                for ref, val in cells.items():
                                    r_idx = int(''.join(filter(str.isdigit, ref)) or 0)
                                    c_idx = ''.join(filter(str.isalpha, ref))
                                    if r_idx not in rows: rows[r_idx] = {}
                                    rows[r_idx][c_idx] = val
                                
                                for r in sorted(rows.keys()):
                                    if r <= 30: continue
                                    r_data = rows[r]
                                    
                                    # Income
                                    inc_date = excel_date_to_str(r_data.get('B', ''))
                                    if inc_date and '-' in inc_date and r_data.get('C') == '수입':
                                        val_i = str(r_data.get('I', '')).strip()
                                        val_h = str(r_data.get('H', '')).strip()
                                        amt_str = val_i if val_i else val_h
                                        amt = float(amt_str.replace(',', '') or 0)
                                        if amt > 0:
                                            yerin_tx.append({
                                                'date': inc_date, 'type': '수입',
                                                'category': r_data.get('D', '').strip() or '급여',
                                                'subcategory': '', 'desc': r_data.get('E', '').strip(),
                                                'account': '계좌이체', 'amount': amt, 'detail': ''
                                            })
                                    
                                    # Expense
                                    exp_date = excel_date_to_str(r_data.get('J', ''))
                                    if exp_date and '-' in exp_date and r_data.get('L'):
                                        amt_str = str(r_data.get('R', r_data.get('P', '0'))).strip()
                                        amt = float(amt_str.replace(',', '') or 0)
                                        if amt > 0:
                                            yerin_tx.append({
                                                'date': exp_date, 'type': '지출',
                                                'category': r_data.get('L', '').strip() or '기타',
                                                'subcategory': r_data.get('M', '').strip(),
                                                'desc': r_data.get('N', '').strip(),
                                                'account': r_data.get('K', '').strip() or '계좌이체',
                                                'amount': amt, 'detail': r_data.get('S', '').strip()
                                            })
                except Exception as ex:
                    print(f"Error fetching Yerin Google Sheet in server: {ex}")

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
