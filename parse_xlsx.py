import zipfile
import xml.etree.ElementTree as ET
import os
import unicodedata

def get_sheet_cells(zip_ref, sheet_file, shared_strings):
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
                val = ""
                if val_elem is not None:
                    val = val_elem.text or ""
                    if t == 's':
                        val = shared_strings[int(val)]
                cells[ref] = val
        return cells
    except Exception as e:
        return {}

def analyze_july():
    dir_path = "/Users/yerinjin/Desktop/yerincess/1_Yerin's/Account book"
    target_file = ""
    for f in os.listdir(dir_path):
        normalized_name = unicodedata.normalize('NFC', f)
        if "2026" in normalized_name and "가계부" in normalized_name and f.endswith(".xlsx") and "우민" not in normalized_name and "삼성" not in normalized_name and "Talk" not in normalized_name:
            target_file = os.path.join(dir_path, f)
            break
            
    if not target_file:
        print("Target file not found!")
        return
        
    with zipfile.ZipFile(target_file, 'r') as zip_ref:
        shared_strings = []
        try:
            ss_xml = zip_ref.read('xl/sharedStrings.xml')
            ss_root = ET.fromstring(ss_xml)
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for t_elem in ss_root.findall('.//main:t', ns):
                shared_strings.append(t_elem.text or "")
        except KeyError:
            pass

        sheets_info = {}
        try:
            wb_rels_xml = zip_ref.read('xl/_rels/workbook.xml.rels')
            wb_rels_root = ET.fromstring(wb_rels_xml)
            ns_rel = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            for rel in wb_rels_root.findall('.//rel:Relationship', ns_rel):
                sheets_info[rel.get('Id')] = rel.get('Target')
        except Exception as e:
            pass

        workbook_xml = zip_ref.read('xl/workbook.xml')
        wb_root = ET.fromstring(workbook_xml)
        ns_main = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        sheet_file = ""
        for sheet_elem in wb_root.findall('.//main:sheet', ns_main):
            name = unicodedata.normalize('NFC', sheet_elem.get('name'))
            if name == '7월':
                r_id = sheet_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                sheet_file = sheets_info.get(r_id, '')
                break
                
        if not sheet_file:
            print("7월 sheet not found")
            return
            
        if not sheet_file.startswith('xl/'):
            sheet_file = 'xl/' + sheet_file
            
        cells = get_sheet_cells(zip_ref, sheet_file, shared_strings)
        print("=== July Cells ===")
        
        rows = {}
        for ref, val in cells.items():
            r_idx = int(''.join(filter(str.isdigit, ref)) or 0)
            c_idx = ''.join(filter(str.isalpha, ref))
            if r_idx not in rows:
                rows[r_idx] = {}
            rows[r_idx][c_idx] = val
            
        for r in sorted(rows.keys()):
            r_data = rows[r]
            # print all cells in row if it's in the transaction section
            # Let's check rows that have values in columns like H, I, J, K, etc.
            row_str = " | ".join([f"{col}:{val}" for col, val in sorted(r_data.items()) if val])
            # Print rows related to transactions (e.g. from row 100 onwards or if it has date)
            # Let's filter to rows that contain a description
            if len(r_data) >= 3:
                print(f"Row {r:3d}: {row_str}")

analyze_july()
