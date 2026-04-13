# User Resolving — Architecture Updates

This document describes a series of targeted refactoring steps applied to
`lib/user.py` and the surrounding user resolution layer. Each step is
independently mergeable and leaves the codebase in a working state.

---

## Background: What Was Wrong

### The `User` class did too much

`lib/user.py::User` acted simultaneously as a value object, a resolver
traversal service, a DB writer, and an authenticator. The four roles were
entangled because the constructor triggered side effects:

```python
def __init__(self, login="", realm="", resolver="", uid=None):
    ...
    if login or uid is not None:
        self._get_user_from_userstore()   # LDAP call on every construction
        self.rtype = get_resolver_type(self.resolver)
        self.realm_id = get_realm_id(self.realm)
```

Constructing `User("alice", "corp")` immediately fired an LDAP query. Code
that only needed `login`/`realm` for policy matching or audit logging paid the
full resolver cost anyway.

### `lib/` imported from `api/lib/`

`user.py` imported `getParam` and `optional` from `api/lib/utils.py`. Thirty+
other `lib/` files did the same. This is an upward layer dependency: library
code depending on API code. The root cause was that `api/lib/utils.py` had
become a grab-bag containing both API-specific helpers (`send_result`,
`prepolicy_helper`) and general-purpose parameter helpers (`get_required`,
`get_optional`) that the whole codebase needed.

### `exist()` was misleading

```python
def exist(self) -> bool:
    # TODO: really check if user exist (ask user store and maybe re-evaluate realm)
    exist = self.uid and self.realm_id
    return exist
```

`exist()` was used for two distinct purposes:

1. "Was this user found during construction?" — checking cached state.
2. "Does this user currently exist in the resolver?" — a live store check.

The implementation only did (1) while the name and the TODO implied (2).
Callers using it for (1) masked any resolver drift silently.

### Resolver traversal logic was scattered

`get_ordered_resolvers()` was a method on `User` that only read `self.realm`
— it didn't actually need a user object at all. One caller in `policy.py`
constructed a full `User` object (triggering an LDAP call) just to call
`get_ordered_resolvers()`. The resolver traversal logic had no home outside
the `User` class, making it hard to call for non-user contexts.

---

## What Was Changed and Why

### Step 1 — Move parameter helpers to `lib/params.py`

**Merged in:** `update-user-resolving`

`get_required`, `get_optional`, `get_optional_one_of`, `get_required_one_of`
moved from `api/lib/utils.py` to `lib/params.py`. The `api/lib/utils.py`
re-exports them for backward compatibility with existing API-layer imports.

`getParam` was fully removed as part of this step — every call site was
migrated to `get_required` or `get_optional`.

**Why it matters:** Every subsequent diff no longer carries a `lib → api`
import violation. The parameter helpers are now in the right layer.

---

### Step 2 — Cheap `User` construction (`_resolved` flag + factory functions)

**Merged in:** `update-user-resolving`

A `_resolved=False` parameter was added to `User.__init__`. When `True`, the
LDAP call is skipped and construction is cheap:

```python
if not _resolved and (login or uid is not None):
    self._get_user_from_userstore()
    self.rtype = get_resolver_type(self.resolver)
    self.realm_id = get_realm_id(self.realm)
```

Two module-level factory functions make construction intent explicit at call
sites:

```python
def user_ref(login, realm, resolver="") -> User:
    """Cheap construction — no LDAP. For policy matching / audit logging."""
    return User(login=login, realm=realm, resolver=resolver, _resolved=True)

def resolve_user(login, realm, resolver="") -> User:
    """Full resolution. Equivalent to the current User() constructor."""
    return User(login=login, realm=realm, resolver=resolver)
```

**Why it matters:** Code that only needs `login`/`realm`/`resolver` for
scoping can now construct a `User` without paying an LDAP roundtrip. The
factory functions also serve as a passive call-site audit: once `user_ref()`
is adopted at all ref-only sites, a grep immediately shows which functions
receive only references and which ones receive resolved users — that data
informs the type hierarchy decision in a later step.

---

### Step 3 — `is_resolved()` and a real `exist()`

**Merged in:** `update-user-resolving`

`is_resolved()` was added as the standard in-memory check:

```python
def is_resolved(self) -> bool:
    """True if uid, resolver, and realm_id were all set during construction."""
    return bool(self.uid) and bool(self.resolver) and self.realm_id is not None
```

`exist()` was fixed to actually perform a live resolver query (resolving the
open TODO):

```python
def exist(self) -> bool:
    """Live store check — asks the resolver if the user is still present."""
    if not self.is_resolved():
        return False
    resolver = get_resolver_object(self.resolver)
    if resolver is None:
        return False
    uid = resolver.getUserId(self.login)
    return uid not in ["", None]
```

All previous callers of `exist()` that were really asking "was the user found
during construction?" were migrated to `is_resolved()`:

| File | Old call | New call |
|---|---|---|
| `lib/user.py` (`get_specific_info`, `available_info_keys`) | `exist()` | `is_resolved()` |
| `lib/policydecorators.py` | `exist()` | `is_resolved()` |
| `lib/eventhandler/base.py` | `exist()` | `is_resolved()` |
| `api/validate.py` | `exist()` | `is_resolved()` |
| `api/auth.py` | `exist()` | `is_resolved()` |
| `api/register.py` | `exist()` | `is_resolved()` |

`cli/pitokenjanitor/findcontainer.py` intentionally **keeps `exist()`** — it
explicitly checks whether users assigned to containers are still present in the
resolver, which is exactly the live-check semantic.

**Why it matters:** The distinction between "found during construction" and
"still in the store now" was previously invisible. Code that checked `exist()`
for the first purpose was silently doing the right thing because `User.__init__`
always ran the LDAP call first — but that relied on implicit coupling. With
`is_resolved()` and `exist()` carrying distinct, documented semantics, the
intent is visible at each call site.

---

### Step 4 — `UserRepository` as the home for resolver traversal

**Merged in:** `add-user-repository`

A new `lib/userrepository.py` was introduced with a `UserRepository` class.
The resolver traversal logic that was embedded in `User` methods was extracted
here.

#### What moved

| Origin | Destination |
|---|---|
| `User.get_ordered_resolvers()` body | `UserRepository.get_ordered_resolvers(realm)` |
| `User._locate_user_in_resolver()` body | `UserRepository.locate_login_in_resolver(login, resolver_name)` |
| `get_user_from_param()` body | `UserRepository.find_from_params(params)` |

The `User` methods are now thin delegates:

```python
def get_ordered_resolvers(self) -> list[str]:
    return user_repository.get_ordered_resolvers(self.realm)

def _locate_user_in_resolver(self, resolvername: str) -> bool:
    uid = user_repository.locate_login_in_resolver(self.login, resolvername)
    if uid is not None:
        self.resolver = resolvername
        self.uid = uid
        return True
    return False
```

`get_user_from_param()` is kept as a backward-compatible shim so that the 28+
existing call sites continue to work without changes:

```python
def get_user_from_param(param, optional_or_required=True) -> User:
    return user_repository.find_from_params(param, optional_or_required)
```

#### What was not moved

`_get_user_from_userstore()` and `_get_resolvers()` remain on `User`. The
`@user_cache(user_init)` decorator in `lib/usercache.py` calls
`self.get_ordered_resolvers()` and `self._locate_user_in_resolver()` on the
`User` object directly — decoupling the cache from `User` is a separate step
that requires refactoring the cache decorator itself. Because `get_ordered_resolvers`
and `_locate_user_in_resolver` now delegate to the repository, the cache gets
the updated logic automatically without any changes to `usercache.py`.

#### The `policy.py` fix

The one external caller of `get_ordered_resolvers()` in `policy.py` was
constructing a full `User` object just to read the resolver order:

```python
# Before — LDAP call for no reason
user_resolvers = User(user, realm=realm).get_ordered_resolvers()

# After — pure config read
user_resolvers = user_repository.get_ordered_resolvers(realm)
```

`get_ordered_resolvers()` only reads realm configuration — it does not search
for the user. The LDAP call in the old code was entirely wasted.

#### The `before_after.py` update

`resolve_logged_in_user()` in `api/before_after.py` now calls
`user_repository.find_from_params()` directly rather than going through the
`get_user_from_param()` shim. This is the primary adoption site for the new
API and demonstrates the migration pattern for other call sites.

**Why it matters:** The resolver traversal logic now has a single, testable
home. Code that needs to locate a user — or just read the resolver order for a
realm — no longer has to construct a `User` object to do so. The repository's
methods are side-effect-free (`locate_login_in_resolver` returns a uid, it does
not mutate a User object), which makes them straightforward to test in
isolation. The `get_user_from_param()` shim means no call sites outside this
change needed to be updated.

---

## Migration Guide for New Code

### Constructing users

| Intent | Old | New |
|---|---|---|
| Need uid (token ops, auth, attributes) | `User(login=l, realm=r)` | `user_repository.find(l, r)` |
| Only need login/realm/resolver (policy, audit) | `User(login=l, realm=r)` | `user_ref(l, r)` |
| From request params | `get_user_from_param(params)` | `user_repository.find_from_params(params)` |
| Reverse lookup | `User(uid=u, resolver=res)` | `user_repository.find_by_uid(u, res)` |

### Checking user state

| Question | Method |
|---|---|
| Was the user found during construction? | `user.is_resolved()` |
| Is the user still present in the store right now? | `user.exist()` |
| Is the User object completely empty? | `user.is_empty()` |

### Getting resolver order for a realm

```python
# Old — constructs a User object unnecessarily
resolvers = User(login, realm=realm).get_ordered_resolvers()

# New — direct, no LDAP
from privacyidea.lib.userrepository import user_repository
resolvers = user_repository.get_ordered_resolvers(realm)
```

---

## What Comes Next

These steps are not yet done but follow naturally from the current state:

- **`user_ref()` adoption at remaining call sites.** Any place that constructs
  `User(login=..., realm=...)` but only reads `login`/`realm`/`resolver` (never
  `uid`) should switch to `user_ref()`. Once this is done, grep over `user_ref`
  vs `resolve_user` call sites gives a clear empirical split between reference-
  only and resolved-user contexts — the data needed to decide whether a
  `UserRef` Protocol is worth introducing.

- **`UserAttributeRepository`.** `User.set_attribute()`, `User.delete_attribute()`,
  and the `attributes` property do direct SQLAlchemy operations on
  `CustomUserAttribute`. Moving these to a repository follows the same pattern
  as Step 4 and removes the last DB dependency from the `User` class.

- **`AuthenticationService`.** `User.check_password()` caches results in
  `self._checked_passwords` — mutable state on what should be a value object.
  Moving password checking to a service, with the cache as an explicit `dict`
  parameter owned by the token check loop, cleans this up.

- **`User` as a dataclass or Pydantic model.** Once `User` has no service
  methods and no `__init__` side effects, converting it to a `@dataclass` or
  `pydantic.BaseModel` is mechanical. This is the prerequisite for caching
  resolved users in Redis.
