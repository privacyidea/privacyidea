import sys

collect_ignore = []
if sys.version_info[0] > 2:
    collect_ignore.extend([
        'test_lib_smsprovider.py',
        'test_mod_apache.py',
    ])
