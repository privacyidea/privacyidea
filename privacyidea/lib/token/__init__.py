# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
This package contains all top level token functions.
It depends on the models, lib.user and lib.tokenclass (which depends on the
tokenclass implementations like lib.tokens.hotptoken)

This is the middleware/glue between the HTTP API and the database.

The implementation is split across submodules (query, otp, attributes,
lifecycle, auth, tokengroups, importexport, misc); every public name is
re-exported here so ``from privacyidea.lib.token import X`` keeps working.
"""
import logging

from privacyidea.lib.token.const import ENCODING, PI_TOKEN_SERIAL_RANDOM, B32_ALPHABET  # noqa: F401
# Historically re-exported through privacyidea.lib.token; kept for backwards compatibility.
from privacyidea.lib.config import get_token_types  # noqa: F401
from privacyidea.lib.token.query import (  # noqa: F401
    create_tokenclass_object,
    _create_token_query,
    get_tokens_paginated_generator,
    convert_token_objects_to_dicts,
    get_tokens,
    get_tokens_paginate,
    get_one_token,
    get_tokens_from_serial_or_user,
    get_token_type,
    check_serial,
    get_num_tokens_in_realm,
    get_realms_of_token,
    token_exist,
    get_token_owner,
    is_token_owner,
    get_tokens_in_resolver,
    get_tokenclass_info,
)
from privacyidea.lib.token.otp import (  # noqa: F401
    get_otp,
    get_multi_otp,
    get_token_by_otp,
    get_serial_by_otp,
    get_serial_by_otp_list,
)
from privacyidea.lib.token.attributes import (  # noqa: F401
    set_realms,
    set_defaults,
    assign_token,
    unassign_token,
    resync_token,
    reset_token,
    set_pin,
    set_pin_user,
    set_pin_so,
    revoke_token,
    enable_token,
    is_token_active,
    set_otplen,
    set_hashlib,
    set_count_auth,
    get_tokeninfo,
    add_tokeninfo,
    delete_tokeninfo,
    set_validity_period_start,
    set_validity_period_end,
    set_sync_window,
    set_count_window,
    set_description,
    set_failcounter,
    set_max_failcount,
)
from privacyidea.lib.token.lifecycle import (  # noqa: F401
    gen_serial,
    import_token,
    init_token,
    remove_token,
    copy_token_pin,
    copy_token_user,
    copy_token_realms,
    lost_token,
)
from privacyidea.lib.token.auth import (  # noqa: F401
    check_realm_pass,
    check_serial_pass,
    check_otp,
    check_user_pass,
    create_challenges_from_tokens,
    weigh_token_type,
    check_token_list,
    challenge_text_replace,
)
from privacyidea.lib.token.tokengroups import (  # noqa: F401
    set_tokengroups,
    assign_tokengroup,
    unassign_tokengroup,
    list_tokengroups,
)
from privacyidea.lib.token.importexport import (  # noqa: F401
    TokenImportResult,
    TokenExportResult,
    export_tokens,
    import_tokens,
)
from privacyidea.lib.token.misc import (  # noqa: F401
    get_dynamic_policy_definitions,
    regenerate_enroll_url,
)

# Parent logger of all submodule loggers (privacyidea.lib.token.*); kept so that
# setting its level or attaching a handler affects the whole package via propagation.
log = logging.getLogger(__name__)

__all__ = [
    "ENCODING",
    "PI_TOKEN_SERIAL_RANDOM",
    "B32_ALPHABET",
    "get_token_types",
    "create_tokenclass_object",
    "_create_token_query",
    "get_tokens_paginated_generator",
    "convert_token_objects_to_dicts",
    "get_tokens",
    "get_tokens_paginate",
    "get_one_token",
    "get_tokens_from_serial_or_user",
    "get_token_type",
    "check_serial",
    "get_num_tokens_in_realm",
    "get_realms_of_token",
    "token_exist",
    "get_token_owner",
    "is_token_owner",
    "get_tokens_in_resolver",
    "get_tokenclass_info",
    "get_otp",
    "get_multi_otp",
    "get_token_by_otp",
    "get_serial_by_otp",
    "get_serial_by_otp_list",
    "set_realms",
    "set_defaults",
    "assign_token",
    "unassign_token",
    "resync_token",
    "reset_token",
    "set_pin",
    "set_pin_user",
    "set_pin_so",
    "revoke_token",
    "enable_token",
    "is_token_active",
    "set_otplen",
    "set_hashlib",
    "set_count_auth",
    "get_tokeninfo",
    "add_tokeninfo",
    "delete_tokeninfo",
    "set_validity_period_start",
    "set_validity_period_end",
    "set_sync_window",
    "set_count_window",
    "set_description",
    "set_failcounter",
    "set_max_failcount",
    "gen_serial",
    "import_token",
    "init_token",
    "remove_token",
    "copy_token_pin",
    "copy_token_user",
    "copy_token_realms",
    "lost_token",
    "check_realm_pass",
    "check_serial_pass",
    "check_otp",
    "check_user_pass",
    "create_challenges_from_tokens",
    "weigh_token_type",
    "check_token_list",
    "challenge_text_replace",
    "set_tokengroups",
    "assign_tokengroup",
    "unassign_tokengroup",
    "list_tokengroups",
    "TokenImportResult",
    "TokenExportResult",
    "export_tokens",
    "import_tokens",
    "get_dynamic_policy_definitions",
    "regenerate_enroll_url",
]
