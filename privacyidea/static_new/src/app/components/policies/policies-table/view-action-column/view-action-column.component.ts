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

import { Component, computed, inject, input } from "@angular/core";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";

@Component({
  selector: "app-view-action-column",
  standalone: true,
  imports: [HighlightPipe],
  templateUrl: "./view-action-column.component.html",
  styleUrl: "./view-action-column.component.scss"
})
export class ViewActionColumnComponent {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);

  /**
   * Input received from the policy table row.
   */
  readonly actions = input.required<Record<string, string | boolean>>();
  readonly scope = input<string | undefined>(undefined);
  readonly highlightTerms = input<string[]>([]);

  /**
   * Pre-calculates the display list including the boolean check
   * to avoid expensive template function calls.
   *
   * When a filter term is active, entries matching it are floated to the top so the highlight is
   * visible without scrolling a tall (overflowing) actions cell. The alphabetical order is otherwise
   * preserved within both the matched and the unmatched group.
   */
  readonly actionsList = computed(() => {
    const list = Object.entries(this.actions()).map(([name, value]) => ({
      name,
      value,
      isBoolean: this.policyService.getDetailsOfAction(name, this.scope())?.type === "bool"
    }));

    const terms = this.highlightTerms()
      .map((term) => term.toLowerCase())
      .filter((term) => term.length > 0);
    if (terms.length === 0) return list;

    // Match only the text that is actually rendered: the name always, the value only when shown.
    const matchesTerm = (entry: (typeof list)[number]): boolean => {
      if (terms.some((term) => entry.name.toLowerCase().includes(term))) return true;
      return !entry.isBoolean && terms.some((term) => String(entry.value).toLowerCase().includes(term));
    };

    const matched: typeof list = [];
    const rest: typeof list = [];
    for (const entry of list) {
      (matchesTerm(entry) ? matched : rest).push(entry);
    }
    return [...matched, ...rest];
  });
}
