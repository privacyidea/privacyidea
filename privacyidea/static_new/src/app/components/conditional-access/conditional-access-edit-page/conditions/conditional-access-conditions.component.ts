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

import { Component, computed, inject, input, output, signal } from "@angular/core";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionOperatorMeta,
  KnownConditionOperator,
  KnownConditionType,
  ConditionalAccessPolicyCondition
} from "@services/conditional-access/conditional-access-policy.service";

// The wording for one condition type that the API cannot supply: what its values are called, how its
// operator control is announced, and what the selection does under each operator. Keyed by type and
// looked up per rendered row - the rows themselves come from /conditiontypes (see rows), so a type
// added to the backend registry appears without a WebUI change and gets the generic wording from
// genericCopy() until an entry is written here.
interface ConditionRowCopy {
  // Label of the multi-select, naming what is being picked rather than repeating the condition type.
  valuesLabel: string;
  // Names the operator control for assistive technology: the leading label is a plain span and is
  // not otherwise tied to the toggle group, so without this a screen-reader user hears "is one of"
  // with no indication of which row it belongs to.
  operatorAriaLabel: string;
  // What the selection does, per operator: the same list means "only these" under IN and "everything
  // but these" under NOT_IN, so the hint follows the toggle rather than restating the label. Always
  // shown - what an empty selection means is said once for both rows in the section text above.
  hints: Record<KnownConditionOperator, string>;
  // Names the clear button. ClearButtonComponent uses this for both the tooltip and the aria-label, so
  // it cannot be dropped without leaving the button nameless (its mat-icon is aria-hidden). Per row
  // rather than a shared "Clear", so the buttons on the page are told apart out of context.
  clearToolTip: string;
  // Friendly labels for a closed vocabulary. Absent for realms: those are admin-chosen names and
  // must be shown verbatim, or the admin cannot match what they see here against their realm config.
  valueLabels?: Record<string, string>;
}

// One rendered row: a condition type, the label the backend serves for it, and the wording above.
export interface ConditionRowSpec extends ConditionRowCopy {
  type: string;
  // Shown ahead of the operator, so the row reads as a sentence.
  label: string;
}

const CONDITION_COPY: Partial<Record<KnownConditionType, ConditionRowCopy>> = {
  USER_REALM: {
    valuesLabel: $localize`Realms`,
    operatorAriaLabel: $localize`How to compare the user realm`,
    hints: {
      IN: $localize`Restrict the realms this policy is applied to.`,
      NOT_IN: $localize`Exclude realms from this policy.`
    },
    clearToolTip: $localize`Remove all selected realms`
  },
  USER_ROLE: {
    valuesLabel: $localize`Roles`,
    operatorAriaLabel: $localize`How to compare the user role`,
    hints: {
      IN: $localize`Restrict the roles this policy is applied to.`,
      NOT_IN: $localize`Exclude roles from this policy.`
    },
    clearToolTip: $localize`Remove all selected roles`,
    valueLabels: {
      user: $localize`User`,
      "admin-internal": $localize`Administrator (internal)`,
      "admin-external": $localize`Administrator (external)`
    }
  }
};

// The hand-written copy for a served condition type, or undefined for one this WebUI has none for.
// The lookup is by plain string because the served type is one; keying the table on
// KnownConditionType is what still catches a mistyped key in CONDITION_COPY itself.
function conditionCopy(type: string): ConditionRowCopy | undefined {
  return (CONDITION_COPY as Partial<Record<string, ConditionRowCopy>>)[type];
}

// Wording for a condition type this WebUI does not know yet, derived from the label the backend
// serves for it. Plainer than the hand-written copy, but it makes a new registry entry usable rather
// than absent.
function genericCopy(label: string): ConditionRowCopy {
  return {
    valuesLabel: label,
    operatorAriaLabel: $localize`How to compare ${label}`,
    hints: {
      IN: $localize`Restrict the values this policy is applied to.`,
      NOT_IN: $localize`Exclude these values from this policy.`
    },
    clearToolTip: $localize`Remove all selected values`
  };
}

// Fallback operator labels, used until /conditiontypes has loaded. They mirror the backend's own
// labels (OPERATORS in privacyidea.lib.conditional_access.conditions) so nothing visibly changes
// once the real ones arrive.
const OPERATOR_FALLBACK: ConditionOperatorMeta[] = [
  { name: "IN", label: $localize`is one of` },
  { name: "NOT_IN", label: $localize`is not one of` }
];

// Which operator a row starts on before anything is picked. The registry's first operator is the
// membership one, and restricting reads as the less surprising default than exempting.
const DEFAULT_OPERATOR: KnownConditionOperator = "IN";

// Shown when the selected operator is one this WebUI has no wording for - a backend registry that has
// grown an operator the client does not know. Says what the selection is for without claiming a
// direction that would be wrong for half the possible operators.
const UNKNOWN_OPERATOR_HINT = $localize`The values this condition compares against.`;

// The selection of a row that carries no condition (see selectedValues).
const NO_VALUES: string[] = [];

@Component({
  selector: "app-conditional-access-conditions",
  standalone: true,
  imports: [ClearButtonComponent, MatButtonToggleModule, MatFormFieldModule, MatIconModule, MatSelectModule],
  templateUrl: "./conditional-access-conditions.component.html",
  styleUrl: "./conditional-access-conditions.component.scss"
})
export class ConditionalAccessConditionsComponent {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);

  readonly conditions = input.required<ConditionalAccessPolicyCondition[]>();
  readonly conditionsChange = output<ConditionalAccessPolicyCondition[]>();

  // Built from /conditiontypes rather than a local list, so a type added to the backend registry shows
  // up here without a WebUI change - which is what that registry is designed for. Two rules decide
  // what gets a row:
  // * a type whose values cannot be enumerated (choices null) is skipped: a multi-select cannot
  //   represent an open value space, and one offering nothing is worse than none.
  // * a type the policy already carries always gets a row, even if the endpoint has not answered yet
  //   or no longer offers that type, so a stored condition is never invisible while still being saved
  //   with the policy.
  readonly rows = computed<ConditionRowSpec[]>(() => {
    const meta = this.policyService.conditionTypes();
    const offered = Object.keys(meta).filter((type) => meta[type].choices !== null);
    const carried = this.conditions().map((condition) => condition.condition_type);
    const types = [...offered, ...carried.filter((type) => !offered.includes(type))];
    return types.map((type) => {
      const label = meta[type]?.label ?? type;
      return { type, label, ...(conditionCopy(type) ?? genericCopy(label)) };
    });
  });

  // The operator picked for a type that currently carries no condition. Without this the choice
  // would be lost: a row with nothing selected emits no condition at all, so there is nowhere in the
  // policy to keep it, and picking "is not one of" before picking values would silently snap back.
  // Only ever consulted as a fallback (see selectedOperator).
  private readonly pendingOperators = signal<Record<string, string>>({});

  // Values referenced by a condition that no longer exist, by type - the message goes under the
  // control that carries them.
  private readonly staleByType = computed<Record<string, string[]>>(() =>
    Object.fromEntries(
      this.policyService.staleConditionValues(this.conditions()).map((stale) => [stale.condition_type, stale.values])
    )
  );

  conditionFor(type: string): ConditionalAccessPolicyCondition | undefined {
    return this.conditions().find((condition) => condition.condition_type === type);
  }

  // Each of a row's two controls has a selected*/*Options pair: what the policy currently says, and
  // what the admin may pick. The selected* accessors read the policy, the *Options ones the backend
  // vocabulary, so the two halves never share a source.

  // The empty case is one shared array, not a fresh one per call: this feeds a mat-select's [value],
  // whose setter compares by reference and marks the view dirty, scheduling another change-detection
  // pass - which would build another array, for a loop that never settles (see editConditions in the
  // edit page, and what an unsettled app does to an open overlay's position).
  selectedValues(type: string): string[] {
    return this.conditionFor(type)?.value ?? NO_VALUES;
  }

  // The stored condition wins over the remembered choice: were it the other way round, loading a
  // policy into an instance where an operator had been picked for a type with no values would show an
  // operator the policy does not have.
  selectedOperator(type: string): string {
    return this.conditionFor(type)?.operator ?? this.pendingOperators()[type] ?? DEFAULT_OPERATOR;
  }

  // The operators offered by the toggle group, backend-supplied so their labels and the set itself
  // stay in step with the registry; the local fallback only covers the paint before /conditiontypes
  // answers.
  operatorOptions(type: string): ConditionOperatorMeta[] {
    const fromBackend = this.policyService.operatorsForConditionType(type);
    return fromBackend.length ? fromBackend : OPERATOR_FALLBACK;
  }

  // The options offered by the multi-select: the currently valid values plus any the policy already
  // references that are no longer valid. The stale ones must be listed, or mat-select would render a
  // blank trigger for a value it has no option for - and the admin needs to see what the policy
  // actually says before deciding what to do about it.
  valueOptions(type: string): string[] {
    const choices = this.policyService.choicesForConditionType(type);
    const selected = this.selectedValues(type);
    if (choices === null) {
      return selected;
    }
    return [...choices, ...selected.filter((value) => !choices.includes(value))];
  }

  isStaleValue(type: string, value: string): boolean {
    return (this.staleByType()[type] ?? []).includes(value);
  }

  staleValuesFor(type: string): string[] {
    return this.staleByType()[type] ?? [];
  }

  valueLabel(row: ConditionRowSpec, value: string): string {
    return row.valueLabels?.[value] ?? value;
  }

  // Widened for the lookup because the selected operator is whatever the backend served: an operator
  // this WebUI has no wording for gets the neutral hint instead of rendering blank, which is what the
  // old union-typed index did silently.
  hintFor(row: ConditionRowSpec): string {
    const hints: Partial<Record<string, string>> = row.hints;
    return hints[this.selectedOperator(row.type)] ?? UNKNOWN_OPERATOR_HINT;
  }

  onOperatorChange(type: string, operator: string): void {
    this.pendingOperators.set({ ...this.pendingOperators(), [type]: operator });
    const existing = this.conditionFor(type);
    if (existing) {
      this.emitUpsert(type, { ...existing, operator });
    }
  }

  // An empty selection removes the condition rather than storing an empty value list: the backend
  // rejects an empty list, and "restrict to nothing" has no useful reading anyway - under IN it
  // would make the policy dead, under NOT_IN it is the same as no condition at all.
  onValuesChange(type: string, values: string[]): void {
    if (values.length === 0) {
      this.conditionsChange.emit(this.conditions().filter((condition) => condition.condition_type !== type));
      return;
    }
    this.emitUpsert(type, {
      condition_type: type,
      operator: this.selectedOperator(type),
      value: values
    });
  }

  // Emitted in condition_type order, the same canonical order the backend serves them in. They are
  // ANDed, so order carries no meaning - but without a fixed one, removing and re-adding a condition
  // would reorder the array and the edit page's JSON diff would report a change that is not one.
  private emitUpsert(type: string, condition: ConditionalAccessPolicyCondition): void {
    const others = this.conditions().filter((existing) => existing.condition_type !== type);
    this.conditionsChange.emit([...others, condition].sort((a, b) => a.condition_type.localeCompare(b.condition_type)));
  }
}
