# (c) NetKnights GmbH 2026,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Aggregate reads over the authentication log: how attempts *ended*, and what conditional access *did*.

Two summaries live here, both answer a question about one time window cut into equal buckets, both hand that window
and those buckets back in the same shape, and both are built from the same machinery -- :func:`_bin_edges`,
:func:`_bin_column` and the window normalization around them. Splitting them apart would duplicate that machinery;
keeping them beside the listing and the write path left one module carrying five unrelated concerns.

The bucketing is deliberately a ``SUM(CASE ...)`` column per bin rather than a per-dialect date function, so one
portable statement serves every supported database. :data:`MAX_STATISTICS_BINS` therefore bounds the *width* of the
generated statement rather than the rows it reads.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.sql import ColumnElement

from privacyidea.models import AuthenticationLog, ConditionalAccessOutcome
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, outcome_of
from privacyidea.lib.conditional_access.authentication_log import (AuthenticationLogVisibilityScope,
                                                                   filter_conditions, match_condition, naive_utc,
                                                                   visibility_condition)
from privacyidea.lib.conditional_access.session import get_ca_session
from privacyidea.lib.error import ParameterError

# Bins the statistics query splits its window into. Each bin becomes one SUM(CASE ...) column, so the cap bounds the
# width of the generated statement rather than the rows it reads.
DEFAULT_STATISTICS_BINS = 48
MAX_STATISTICS_BINS = 100


def _utc_iso(value: datetime) -> str:
    """Render a naive-UTC datetime as an ISO-8601 string with its timezone, like :meth:`AuthenticationLog.to_dict`."""
    return value.replace(tzinfo=timezone.utc).isoformat()


@dataclass
class AuthenticationEventSeries:
    """
    One classification of an attempt-level statistics result: how many authentication *attempts* ended a given way,
    bucketed over the window's bins.

    *event_type* is the :class:`AuthEventType` of the event that classified the attempt -- its representative, see
    :func:`get_authentication_log_statistics` -- so it names how these attempts *ended*, not an event they merely
    passed through on the way there.

    *outcome* is the :class:`AuthEventOutcome` of *event_type* (``success``, ``failure`` or ``pending``), or ``None``
    if the stored value is not a known :class:`AuthEventType`. It is resolved here so that grouping the series by
    result does not mean re-deriving the mapping.

    *counts* holds one attempt count per bin, in bin order, always as many entries as the result has bins: a bucket
    where nothing happened is a ``0`` rather than a gap, so the series can be charted without being re-aligned. The
    bins' start times are not repeated here -- every series shares them, so they live on the enclosing
    :class:`AuthenticationLogStatistics`.
    """
    event_type: str
    outcome: str | None
    counts: list[int]

    @property
    def total(self) -> int:
        """How many attempts this classification holds across the whole window."""
        return sum(self.counts)

    def to_dict(self) -> dict:
        """Serialize the series for the API response, including the window total a caller would otherwise re-sum."""
        return {"event_type": self.event_type, "outcome": self.outcome, "counts": self.counts, "total": self.total}


@dataclass
class AuthenticationLogStatistics:
    """
    Attempt-level statistics over one time window: one :class:`AuthenticationEventSeries` per classification, all
    sharing the same bins.

    *start_time* and *end_time* are the window the result covers, normalized to naive UTC like the ``timestamp``
    column and inclusive at both ends, so a caller that passed timezone-aware values gets back the instants that were
    actually queried.

    *bin_starts* holds the inclusive start of each bucket, one entry per bin and in the same order as every series'
    *counts*, so the two zip together. The buckets are of equal width and cover the window exactly; only the last one
    closes inclusively, on *end_time*.

    *events* holds one series per classification **present in the window**: a classification no attempt ended with
    has no series at all rather than an all-zero one, so a missing entry reads as zero. They are ordered by descending
    window total, ties broken by event type, so a caller wanting the top few can slice. Every classification is
    offered, :data:`CA_ENFORCEMENT_EVENT_TYPES` included; which of them to show is the view's decision (see
    :func:`get_authentication_log_statistics` for why they are reduced *with* and dropped only afterwards).
    """
    start_time: datetime
    end_time: datetime
    bin_starts: list[datetime]
    events: list[AuthenticationEventSeries]

    @property
    def total(self) -> int:
        """How many attempts the window holds across all classifications."""
        return sum(series.total for series in self.events)

    def to_dict(self) -> dict:
        """
        Serialize the statistics for the API response, timestamps as ISO-8601 UTC strings like
        :meth:`AuthenticationLog.to_dict`.

        The series sit under their own ``events`` key so a second section -- aggregating what conditional access *did*,
        from ``conditional_access_outcome``, rather than how attempts *ended* -- can be added later without breaking
        the response.
        """
        return {
            "window": {"start_time": _utc_iso(self.start_time), "end_time": _utc_iso(self.end_time),
                       "total": self.total},
            "bins": {"count": len(self.bin_starts), "starts": [_utc_iso(start) for start in self.bin_starts]},
            "events": [series.to_dict() for series in self.events],
        }


@dataclass
class ConditionalAccessOutcomeSeries:
    """
    One action type of an outcome-history result: how many times conditional access did that thing, bucketed over the
    window's bins.

    *action_type* is a :class:`~privacyidea.lib.conditional_access.engine.ConditionalAccessAction` value -- the action
    the engine executed (``LOCK_USER``, ``BLOCK_IP``, ``EMAIL_ADMIN``, ...) or the ``DENY`` decision.

    *counts* holds one count per bin, in bin order, always as many entries as the result has bins: a bucket where
    nothing happened is a ``0`` rather than a gap, so the series can be charted without being re-aligned. The bins'
    start times are not repeated here -- every series shares them, so they live on the enclosing
    :class:`ConditionalAccessOutcomeStatistics`.
    """
    action_type: str
    counts: list[int]

    @property
    def total(self) -> int:
        """How many outcomes of this action type the window holds."""
        return sum(self.counts)

    def to_dict(self) -> dict:
        """Serialize the series for the API response, including the window total a caller would otherwise re-sum."""
        return {"action_type": self.action_type, "counts": self.counts, "total": self.total}


@dataclass
class ConditionalAccessOutcomeStatistics:
    """
    The history of what conditional access did over one time window: one :class:`ConditionalAccessOutcomeSeries` per
    action type, all sharing the same bins.

    The window and the bins mean exactly what they do on :class:`AuthenticationLogStatistics` -- normalized to naive
    UTC, inclusive at both ends, one *bin_starts* entry per bucket in the same order as every series' counts -- so a
    caller charting both reads them the same way.

    *outcomes* holds one series per action type **present in the window**, ordered by descending window total with
    ties broken by action type. An action nothing triggered has no series at all rather than an all-zero one, so a
    missing entry reads as zero.
    """
    start_time: datetime
    end_time: datetime
    bin_starts: list[datetime]
    outcomes: list[ConditionalAccessOutcomeSeries]

    @property
    def total(self) -> int:
        """How many outcomes the window holds across all action types."""
        return sum(series.total for series in self.outcomes)

    def to_dict(self) -> dict:
        """
        Serialize the statistics for the API response, timestamps as ISO-8601 UTC strings like
        :meth:`AuthenticationLog.to_dict`.

        ``window`` and ``bins`` are shaped exactly as :meth:`AuthenticationLogStatistics.to_dict` shapes them, so a
        client charting either can share the code that reads them; only the series key differs, naming what these
        series are grouped by.
        """
        return {
            "window": {"start_time": _utc_iso(self.start_time), "end_time": _utc_iso(self.end_time),
                       "total": self.total},
            "bins": {"count": len(self.bin_starts), "starts": [_utc_iso(start) for start in self.bin_starts]},
            "outcomes": [series.to_dict() for series in self.outcomes],
        }


def _bin_edges(start_time: datetime, end_time: datetime, bins: int) -> list[datetime]:
    """Return the *bins* + 1 boundaries of equal-width buckets spanning ``[start_time, end_time]``."""
    span = end_time - start_time
    return [start_time + span * (index / bins) for index in range(bins + 1)]


def _bin_column(edges: list[datetime], index: int) -> ColumnElement[int]:
    """
    Build the ``SUM(CASE ...)`` column counting the representatives falling into bucket *index*.

    Bucketing this way rather than with a per-dialect date function (``date_trunc`` / ``DATE_FORMAT`` / ``strftime`` /
    ``TRUNC``) keeps the statistics query to one portable statement on every supported backend. The final bucket
    closes inclusively, so a representative sitting exactly on ``end_time`` is counted rather than dropped, like every
    other timestamp filter on the log.
    """
    upper = (AuthenticationLog.timestamp <= edges[index + 1] if index == len(edges) - 2
             else AuthenticationLog.timestamp < edges[index + 1])
    return func.sum(case((and_(AuthenticationLog.timestamp >= edges[index], upper), 1), else_=0))


def get_authentication_log_statistics(start_time: datetime,
                                      end_time: datetime,
                                      bins: int = DEFAULT_STATISTICS_BINS,
                                      resolvers: list[str] | None = None,
                                      uids: list[str] | None = None,
                                      realms: list[str] | None = None,
                                      usernames: list[str] | None = None,
                                      user_roles: list[str] | None = None,
                                      event_types: list[str] | None = None,
                                      reasons: list[str] | None = None,
                                      source_ips: list[str] | None = None,
                                      serials: list[str] | None = None,
                                      transaction_ids: list[str] | None = None,
                                      attempt_ids: list[str] | None = None,
                                      client_labels: list[str] | None = None,
                                      endpoints: list[str] | None = None,
                                      visibility_scopes: list[AuthenticationLogVisibilityScope] | None = None,
                                      case_insensitive: bool = False) -> AuthenticationLogStatistics:
    """
    Summarize the authentication log over ``[start_time, end_time]`` as **attempts**, bucketed into *bins* equal-width
    buckets and grouped by the event type that classifies each attempt.

    Counting *rows* here would be wrong twice over: a challenge-response login writes both a
    :attr:`AuthEventType.CHALLENGE_TRIGGERED` and a :attr:`AuthEventType.LOGIN_SUCCESS` row, so one successful login
    would be counted as both a pending and a successful event. The rows sharing an ``attempt_id`` are therefore
    reduced to one representative each, by the same rule as
    :func:`~privacyidea.lib.conditional_access.engine._count_matching_attempts`: the ``LOGIN_SUCCESS`` row if the
    attempt ever logged in, otherwise the latest row by ``id``. Insertion order, not an event-type ranking, is what
    distinguishes a wrong answer *then* a continue (in progress) from a continue *then* a wrong answer (failed).

    The reduction deliberately **diverges from the engine's in two ways**, because the engine feeds a threshold while
    this feeds a human:

    * The engine drops :data:`CA_ENFORCEMENT_EVENT_TYPES` rows *before* reducing, so a rejection cannot replace a
      tracked failure and stall an escalation. Dropping them first here would classify an attempt of
      ``[CHALLENGE_TRIGGERED, USER_LOCKED]`` as *pending*, inventing an in-flight attempt out of one that was turned
      away. They are reduced *with* instead, and every classification is returned; a caller that does not want them
      drops those series, which is filtering rather than misreporting.
    * The engine groups rows by ``attempt_id`` in a dict, so rows without one collapse under a single ``None`` key.
      Harmless for one subject's handful of rows, and badly wrong when aggregating every subject in a deployment, so
      a row without an ``attempt_id`` counts as its own attempt here.

    Every filter except the window applies to the **representative** row, not to the rows feeding the reduction:
    dropping rows from the inner query would reduce an attempt from a subset of its own rows, which misclassifies it
    rather than excluding it (the same trap :func:`~privacyidea.lib.conditional_access.engine._count_attempts`
    documents). Which *attempts* are reduced is narrowed, though - to those holding at least one matching row, an
    attempt without one having no matching representative either - so a filtered or visibility-scoped summary does
    not group every row the window holds across the deployment before answering about a few.
    ``event_types`` therefore reads as "attempts that *ended* like this", which is the only meaning it can have once
    rows are collapsed, and ``reasons`` as "ended for one of these reasons" - it matches the representative's reason
    rows, not those of the earlier rows the attempt is reduced from. Each filter takes a list, matching an attempt
    whose representative equals any of its values or matches any value carrying a ``*`` wildcard
    (see :func:`match_condition`). An attempt straddling ``start_time`` is reduced from its in-window rows alone and
    may be classified by them; this is the same window-edge approximation the engine's sliding window accepts.

    :param start_time: start of the window, inclusive (naive values are read as UTC)
    :param end_time: end of the window, inclusive
    :param bins: how many equal-width buckets to split the window into, at most :data:`MAX_STATISTICS_BINS`
    :param visibility_scopes: restrict the counted attempts to those whose representative matches any of these scopes
        (see :func:`visibility_condition`); ``None`` means no restriction
    :param case_insensitive: if set, plain (non-wildcard) filter values match case-insensitively
    :return: an :class:`AuthenticationLogStatistics` holding one series per classification
    :raises ParameterError: if the window does not end after it starts, or *bins* is out of range
    """
    window_start = naive_utc(start_time)
    window_end = naive_utc(end_time)
    if window_end <= window_start:
        raise ParameterError("The statistics window must end after it starts.")
    if not 1 <= bins <= MAX_STATISTICS_BINS:
        raise ParameterError(f"The number of bins must be between 1 and {MAX_STATISTICS_BINS}.")
    edges = _bin_edges(window_start, window_end, bins)

    window = (AuthenticationLog.timestamp >= window_start, AuthenticationLog.timestamp <= window_end)
    conditions = filter_conditions(resolvers=resolvers, uids=uids, realms=realms, usernames=usernames,
                                    user_roles=user_roles, event_types=event_types, reasons=reasons,
                                    source_ips=source_ips, serials=serials, transaction_ids=transaction_ids,
                                    attempt_ids=attempt_ids, client_labels=client_labels, endpoints=endpoints,
                                    case_insensitive=case_insensitive)
    if visibility_scopes is not None:
        conditions.append(visibility_condition(visibility_scopes))

    reduced = [*window]
    if conditions:
        # Narrow *which attempts* are reduced to those with at least one matching row, while still reducing each of
        # them from all of its rows. Without this the reduction groups every row of the window in the deployment
        # before the caller's filters and the visibility scope are applied to the representatives, so a self-service
        # user reading their own 30 days makes the database group everyone's.
        #
        # This cannot change a single count. The representative is one of the attempt's own rows, so an attempt with
        # no matching row has no matching representative either and the outer filter would drop it anyway; every
        # attempt that survives still contributes all of its rows, which is what keeps the reduction from
        # reclassifying one (see the note on the representative filters below). A row without an attempt_id *is* its
        # own representative, so for those the filters apply directly.
        matching_attempts = select(AuthenticationLog.attempt_id).where(*window,
                                                                       AuthenticationLog.attempt_id.is_not(None),
                                                                       *conditions)
        reduced.append(or_(AuthenticationLog.attempt_id.in_(matching_attempts),
                           and_(AuthenticationLog.attempt_id.is_(None), *conditions)))
    # Rows carrying an attempt_id group by it; rows without group by their own id and so count individually. A
    # COALESCE of the two would have to cast the id to a string and mix collations, which MySQL rejects outright.
    attempts = (select(func.max(case((AuthenticationLog.event_type == str(AuthEventType.LOGIN_SUCCESS),
                                      AuthenticationLog.id))).label("success_id"),
                       func.max(AuthenticationLog.id).label("latest_id"))
                .where(*reduced)
                .group_by(AuthenticationLog.attempt_id,
                          case((AuthenticationLog.attempt_id.is_(None), AuthenticationLog.id)))
                .subquery())

    stmt = (select(AuthenticationLog.event_type,
                   *[_bin_column(edges, index).label(f"bin_{index}") for index in range(bins)])
            .select_from(attempts)
            .join(AuthenticationLog,
                  AuthenticationLog.id == func.coalesce(attempts.c.success_id, attempts.c.latest_id))
            .where(*conditions)
            .group_by(AuthenticationLog.event_type))

    known_outcomes = {str(event): str(outcome_of(event)) for event in AuthEventType}
    series = [AuthenticationEventSeries(event_type=row[0],
                                        outcome=known_outcomes.get(row[0]),
                                        counts=[int(count or 0) for count in row[1:]])
              for row in get_ca_session().execute(stmt).all()]
    series.sort(key=lambda item: (-item.total, item.event_type))
    return AuthenticationLogStatistics(start_time=window_start, end_time=window_end, bin_starts=edges[:-1],
                                       events=series)


def get_conditional_access_outcome_statistics(start_time: datetime,
                                              end_time: datetime,
                                              bins: int = DEFAULT_STATISTICS_BINS,
                                              action_types: str | list[str] | None = None,
                                              policy_names: str | list[str] | None = None,
                                              dry_run: bool | None = None,
                                              visibility_scopes: list[AuthenticationLogVisibilityScope] | None = None,
                                              case_insensitive: bool = False
                                              ) -> ConditionalAccessOutcomeStatistics:
    """
    Summarize what conditional access **did** over ``[start_time, end_time]``, as counts of recorded outcomes bucketed
    into *bins* equal-width buckets and grouped by action type.

    This answers "when were users locked and IPs blocked", which no other table can: ``user_lock_state`` and
    ``block_list`` hold the restriction currently in force and forget it once it lapses, while
    :class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome` keeps one row per action the
    engine executed. A lock that has since expired, been reset or been purged from the live state is still counted
    here.

    **Counted per outcome, not per request or per attempt**, which is what makes the numbers mean what they say:
    one row is one restriction imposed. A request that locked the user *and* blocked the source IP created two
    restrictions and contributes to both series, once each. This is the opposite of the listing's filter, which uses
    an ``EXISTS`` precisely to avoid multiplying an entry by its outcomes (see :func:`_outcome_condition`); here the
    multiplication *is* the count.

    Not to be confused with the enforcement event types of
    :func:`get_authentication_log_statistics`: :attr:`AuthEventType.USER_LOCKED` is a request *turned away* by a lock
    already in force, so counting those would count retries against one lock rather than the lock. The lock itself is
    a :attr:`ConditionalAccessAction.LOCK_USER` outcome, which is what this counts.

    The window is filtered on the parent row's ``timestamp``, since an outcome deliberately does not repeat it, and
    the parent is joined for that. Filtering by *action_types* is what makes the query cheap: it is served by
    ``ix_ca_outcome_action`` and highly selective, so the work scales with how many restrictions were imposed rather
    than with how many requests the window holds.

    *visibility_scopes* likewise applies to the parent row, an outcome carrying no subject of its own. Omitting it
    would let a realm-scoped admin count every realm's locks, so it is threaded through exactly as the two log
    endpoints do.

    :param start_time: start of the window, inclusive (naive values are read as UTC)
    :param end_time: end of the window, inclusive
    :param bins: how many equal-width buckets to split the window into, at most :data:`MAX_STATISTICS_BINS`
    :param action_types: only outcomes of these ``ConditionalAccessAction`` values; takes a list and a ``*`` wildcard
        like every other filter on the log, so ``"*"`` reads as "everything conditional access did"
    :param policy_names: only outcomes recorded for these policy names (the denormalized copy, so a deleted policy is
        still matchable)
    :param dry_run: ``False`` for only enforced outcomes, ``True`` for only the dry-run rows recording what *would*
        have happened, ``None`` for both -- note that counting both together charts restrictions that never existed
    :param visibility_scopes: restrict the counted outcomes to those whose request matches any of these scopes
        (see :func:`visibility_condition`); ``None`` means no restriction
    :param case_insensitive: if set, plain (non-wildcard) filter values match case-insensitively
    :return: a :class:`ConditionalAccessOutcomeStatistics` holding one series per action type
    :raises ParameterError: if the window does not end after it starts, or *bins* is out of range
    """
    window_start = naive_utc(start_time)
    window_end = naive_utc(end_time)
    if window_end <= window_start:
        raise ParameterError("The statistics window must end after it starts.")
    if not 1 <= bins <= MAX_STATISTICS_BINS:
        raise ParameterError(f"The number of bins must be between 1 and {MAX_STATISTICS_BINS}.")
    edges = _bin_edges(window_start, window_end, bins)

    conditions = [AuthenticationLog.timestamp >= window_start, AuthenticationLog.timestamp <= window_end]
    conditions += [condition for column, value in ((ConditionalAccessOutcome.action_type, action_types),
                                                   (ConditionalAccessOutcome.policy_name, policy_names))
                   if (condition := match_condition(column, value, case_insensitive)) is not None]
    if dry_run is not None:
        conditions.append(ConditionalAccessOutcome.dry_run.is_(dry_run))
    if visibility_scopes is not None:
        conditions.append(visibility_condition(visibility_scopes))

    stmt = (select(ConditionalAccessOutcome.action_type,
                   *[_bin_column(edges, index).label(f"bin_{index}") for index in range(bins)])
            .select_from(ConditionalAccessOutcome)
            .join(AuthenticationLog, AuthenticationLog.id == ConditionalAccessOutcome.auth_log_id)
            .where(*conditions)
            .group_by(ConditionalAccessOutcome.action_type))

    series = [ConditionalAccessOutcomeSeries(action_type=row[0], counts=[int(count or 0) for count in row[1:]])
              for row in get_ca_session().execute(stmt).all()]
    series.sort(key=lambda item: (-item.total, item.action_type))
    return ConditionalAccessOutcomeStatistics(start_time=window_start, end_time=window_end, bin_starts=edges[:-1],
                                              outcomes=series)

