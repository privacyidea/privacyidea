import sys

collect_ignore = []
if sys.version_info[0] > 2:
    collect_ignore.append("test_mod_apache.py")
    collect_ignore.append("test_lib_smsprovider.py")

