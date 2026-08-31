/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { DatePipe } from "@angular/common";
import { Component, computed, input, linkedSignal } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthenticationLogEntry } from "@services/authentication-log/authentication-log.service";

// OutcomeView deliberately allow-lists an outcome's fields, since a log column only needs to answer which policy did
// what - so a new backend column cannot leak into the UI by accident. Only `action` and `dryRun` show up front (what
// happened); the rest explains why and sits behind the expand toggle, since this table has eleven other columns and a
// four-line cell would push them off-screen.
export interface OutcomeView {
  // Identifies this outcome for the expand toggle and the aria-controls of its details. The row's own id when the
  // backend sent one; otherwise the entry and the position, which is unique within the rendered page.
  key: string;
  policy: string;
  // Set only while a policy of that name exists (and the caller may read the policy list): the outcome names its policy
  // and stores no id, so a link is a *lookup*, not a stored reference.
  policyLink?: string;
  // Marked in the column because it is the exception: a dry-run outcome describes what *would* have happened.
  dryRun: boolean;
  action: string;
  // When the action created a timed restriction: the ISO-8601 timestamp it lapses at - the only remaining record of how
  // long a lock/block lasted once the state row expires, and its absence is how a PERMANENT_* action (or one that
  // restricts nothing) is recognized. The one field read out of `info`.
  expiresAt?: string;
  stage?: string;
  // The triggered stage's failure threshold: shown next to the name because it is what identifies the stage when the
  // admin did not name one (with the policy it is the stage's natural key, see the model).
  threshold?: number;
}

/**
 * The authentication log's Conditional access cell: what conditional access did to one request.
 *
 * One line per executed action - or per action a dry-run policy would have run - with the rest of the outcome behind an
 * expand toggle.
 *
 * Deliberately not the Info cell's renderer: that one walks arbitrary JSON, while an outcome has one known shape, so
 * mapping it explicitly is both simpler and safer. The two share their looks (../info-list), not their rendering.
 */
@Component({
  selector: "app-conditional-access-cell",
  standalone: true,
  imports: [DatePipe, MatIcon, MatTooltipModule, RouterLink],
  templateUrl: "./conditional-access-cell.html",
  styleUrl: "./conditional-access-cell.scss"
})
export class ConditionalAccessCell {
  // The entry's raw conditional_access_outcomes exactly as the backend sent them - not OutcomeView, which this cell
  // derives from them (key, policy link, validated expiry). The type stays a plain record because the API returns every
  // column of the row, and picking which to display is this cell's job, so a new column needs no change above.
  readonly outcomes = input<AuthenticationLogEntry["conditional_access_outcomes"]>(null);
  // Only used to build a key for outcomes the backend sent without an id.
  readonly entryId = input<number | undefined>(undefined);
  // The current id of each existing policy, by name: an outcome stores the policy's name and no id (a deleted policy's
  // id could be reused by another policy), so this turns a name into a link only while one still exists under it. An
  // empty map (e.g. without conditional_access_policy_read) means link nothing, and the name still reads as plain text.
  readonly policyIdsByName = input<ReadonlyMap<string, number>>(new Map<string, number>());

  // Anything that is not a list yields nothing. The guard is not redundant with the input's type: the table's skeleton
  // rows are built by key and set *every* column to "", so the declared type is a promise the loading state breaks.
  readonly views = computed<OutcomeView[]>(() => {
    const outcomes = this.outcomes();
    if (!Array.isArray(outcomes)) return [];
    return outcomes.map((outcome, index) => {
      const policy = String(outcome["policy_name"] ?? "");
      const policyId = this.policyIdsByName().get(policy);
      const stage = outcome["stage_name"];
      const threshold = outcome["threshold"];
      const id = outcome["id"];
      return {
        key: typeof id === "number" ? String(id) : `${this.entryId()}-${index}`,
        policy,
        policyLink:
          policyId === undefined ? undefined : `${ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS}${policyId}`,
        dryRun: !!outcome["dry_run"],
        action: String(outcome["action_type"] ?? ""),
        stage: typeof stage === "string" && stage ? stage : undefined,
        threshold: typeof threshold === "number" ? threshold : undefined,
        expiresAt: this.expiry(outcome["info"])
      };
    });
  });

  // Which outcomes show their details, by OutcomeView.key; collapses again whenever the cell is handed different
  // outcomes, since a table row is reused across pages and silently keeping its height would be the more surprising
  // behavior.
  private readonly expanded = linkedSignal<AuthenticationLogEntry["conditional_access_outcomes"], Set<string>>({
    source: () => this.outcomes(),
    computation: () => new Set<string>()
  });

  isExpanded(key: string): boolean {
    return this.expanded().has(key);
  }

  toggle(key: string): void {
    const expanded = new Set(this.expanded());
    if (!expanded.delete(key)) {
      expanded.add(key);
    }
    this.expanded.set(expanded);
  }

  // The toggle carries no visible text, so its accessible name has to say both what it does and which outcome it
  // belongs to - there is one button per outcome, and "expand" alone would leave them indistinguishable.
  toggleLabel(outcome: OutcomeView): string {
    return this.isExpanded(outcome.key)
      ? $localize`Hide the details of ${outcome.action}`
      : $localize`Show the details of ${outcome.action}`;
  }

  // The expiry an action recorded in its `info`, or undefined when it created no timed restriction; validated here
  // rather than in the template, since the date pipe throws on an unparsable value and `info` is a free-form JSON
  // column whose only rule is what the writer puts in it.
  private expiry(info: unknown): string | undefined {
    if (typeof info !== "object" || info === null || Array.isArray(info)) return undefined;
    const expiresAt = (info as Record<string, unknown>)["expires_at"];
    if (typeof expiresAt !== "string" || Number.isNaN(new Date(expiresAt).getTime())) return undefined;
    return expiresAt;
  }
}
