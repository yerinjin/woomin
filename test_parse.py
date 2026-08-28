import sys
sys.path.append('.')
from api.index import parse_parents_accounts

accounts = parse_parents_accounts('parents')
print("Parsed accounts:", accounts)
