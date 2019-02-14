import sys

collect_ignore = []
if sys.version_info[0] > 2:
    collect_ignore.extend([
        'test_api_periodictask.py',
        'test_api_policy.py',
        'test_api_register.py',
        'test_api_roles.py',
        'test_api_smtpserver.py',
        'test_api_subscriptions.py',
        'test_api_system.py',
        'test_api_token.py',
        'test_api_users.py',
        'test_api_validate.py',
        'test_lib_smsprovider.py',
        'test_mod_apache.py',
    ])
