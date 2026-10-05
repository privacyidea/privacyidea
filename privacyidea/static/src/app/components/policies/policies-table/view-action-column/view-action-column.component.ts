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

import { Component, computed, inject, input, output } from "@angular/core";
import { MatTooltipModule } from "@angular/material/tooltip";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";
import { actionNameWithoutExclusion, actionValueIsInvalid, isExcludedActionName } from "@utils/policy-action.utils";
import { POLICY_VOCABULARY_ACTIONS, valueDisplayLabel } from "@utils/value-label.utils";

@Component({
  selector: "app-view-action-column",
  standalone: true,
  imports: [FilterValueButtonComponent, HighlightPipe, MatTooltipModule],
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
  readonly filterAction = output<string>();

  /**
   * Pre-calculates the display list including the boolean check
   * to avoid expensive template function calls.
   *
   * When a filter term is active, entries matching it are floated to the top so the highlight is
   * visible without scrolling a tall (overflowing) actions cell. The alphabetical order is otherwise
   * preserved within both the matched and the unmatched group.
   */
  readonly actionsList = computed(() => {
    const list = Object.entries(this.actions()).map(([name, value]) => {
      const isExcluded = isExcludedActionName(name);
      const detail = this.policyService.getDetailsOfAction(actionNameWithoutExclusion(name), this.scope());
      const isBoolean = detail?.type === "bool";
      // An invalid value is shown and marked, also the one of a boolean action: it does not enable the action, which
      // still acts as enabled until saving the policy in the WebUI removes it.
      const invalidValue = !isExcluded && !!detail && actionValueIsInvalid(detail, value);
      return {
        name,
        value,
        displayValue: valueDisplayLabel(value, detail?.value, { vocabulary: POLICY_VOCABULARY_ACTIONS.has(name) }),
        isBoolean,
        invalidValue,
        // The value of an excluded action has no effect
        showValue: !isExcluded && (!isBoolean || invalidValue)
      };
    });

    const terms = this.highlightTerms()
      .map((term) => term.toLowerCase())
      .filter((term) => term.length > 0);
    if (terms.length === 0) return list;

    // Match the name always and the value only when shown, against both the raw value and the
    // display label it may be mapped to (e.g. "1" shown as "On").
    const matchesTerm = (entry: (typeof list)[number]): boolean => {
      if (terms.some((term) => entry.name.toLowerCase().includes(term))) return true;
      if (!entry.showValue) return false;
      const haystack = [String(entry.value).toLowerCase(), entry.displayValue.toLowerCase()];
      return terms.some((term) => haystack.some((text) => text.includes(term)));
    };

    const matched: typeof list = [];
    const rest: typeof list = [];
    for (const entry of list) {
      (matchesTerm(entry) ? matched : rest).push(entry);
    }
    return [...matched, ...rest];
  });
}
