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
  LockoutPolicyCondition
} from "@services/conditional-access/conditional-access-policy.service";

// Hand-written wording for one condition type that the API does not supply -- its value label,
// operator announcement, and per-operator hint -- keyed by type and looked up per row; rows
// themselves come from /conditiontypes (see rows), so a newly registered type still renders using
// genericCopy() until an entry is written here.
interface ConditionRowCopy {
  // Label of the multi-select, naming what is being picked rather than repeating the condition type.
  valuesLabel: string;
  // Names the operator control for assistive technology; the leading label is a plain span not tied
  // to the toggle group, so without this a screen-reader announces "is one of" with no indication
  // of which row it belongs to.
  operatorAriaLabel: string;
  // What the selection does per operator: the same list means "only these" under IN and "everything
  // but these" under NOT_IN, so the hint follows the toggle instead of restating the label; always
  // shown, since what an empty selection means is said once in the section text above.
  hints: Record<KnownConditionOperator, string>;
  // Names the clear button for both its tooltip and aria-label (ClearButtonComponent uses this for
  // both, and its mat-icon is aria-hidden); kept per row rather than a shared "Clear" so the buttons
  // are distinguishable out of context.
  clearToolTip: string;
  // Friendly labels for a closed vocabulary; absent for realms, whose admin-chosen names must be
  // shown verbatim so the admin can match them against their realm config.
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

// Hand-written copy for a served condition type, or undefined if this WebUI has none; the lookup
// uses a plain string because the served type is one, while CONDITION_COPY itself is keyed on
// KnownConditionType so a mistyped key there is still caught.
function conditionCopy(type: string): ConditionRowCopy | undefined {
  return (CONDITION_COPY as Partial<Record<string, ConditionRowCopy>>)[type];
}

// Wording for a condition type this WebUI has no hand-written copy for, derived from the backend's
// label; plainer, but it makes a new registry entry usable rather than absent.
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

// Fallback operator labels used until /conditiontypes has loaded, mirroring the backend's own labels
// (OPERATORS in privacyidea.lib.conditional_access.conditions) so nothing visibly changes once the
// real ones arrive.
const OPERATOR_FALLBACK: ConditionOperatorMeta[] = [
  { name: "IN", label: $localize`is one of` },
  { name: "NOT_IN", label: $localize`is not one of` }
];

// Operator a row starts on before anything is picked: the registry's first operator is the
// membership one, and restricting reads as the less surprising default than exempting.
const DEFAULT_OPERATOR: KnownConditionOperator = "IN";

// Shown when the selected operator is one this WebUI has no wording for, i.e. the backend registry
// has grown an operator the client does not know; states what the selection is for without claiming
// a direction that would be wrong for half the possible operators.
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

  readonly conditions = input.required<LockoutPolicyCondition[]>();
  readonly conditionsChange = output<LockoutPolicyCondition[]>();

  // Rows come from /conditiontypes rather than a local list, so a type added to the backend registry
  // appears here without a WebUI change. Two rules decide what gets a row:
  // * a type whose values cannot be enumerated (choices null) is skipped, since a multi-select
  //   cannot represent an open value space.
  // * a type the policy already carries always gets a row, even if the endpoint has not answered yet
  //   or no longer offers that type, so a stored condition is never invisible.
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

  // Operator picked for a type that currently carries no condition -- since a row with no selection
  // emits no condition, this is the only place the choice can live, so without it picking "is not
  // one of" before picking values would silently snap back; consulted only as selectedOperator's
  // fallback.
  private readonly pendingOperators = signal<Record<string, string>>({});

  // Values referenced by a condition that no longer exist, keyed by type so the message can be
  // placed under the control that carries them.
  private readonly staleByType = computed<Record<string, string[]>>(() =>
    Object.fromEntries(
      this.policyService.staleConditionValues(this.conditions()).map((stale) => [stale.condition_type, stale.values])
    )
  );

  conditionFor(type: string): LockoutPolicyCondition | undefined {
    return this.conditions().find((condition) => condition.condition_type === type);
  }

  // --- a row's two controls: selected* reads the policy, *Options reads the backend vocabulary ---
  // The two halves never share a source, so what the policy says and what the admin may pick stay distinct.

  // The empty case returns one shared array, not a fresh one per call: this feeds a mat-select's
  // [value], whose setter compares by reference and marks the view dirty on any new array, which
  // would never let change detection settle (see editConditions in the edit page).
  selectedValues(type: string): string[] {
    return this.conditionFor(type)?.value ?? NO_VALUES;
  }

  // The stored condition wins over the remembered choice; otherwise loading a policy into an instance
  // where an operator had been picked for an empty type would show an operator the policy does not
  // actually have.
  selectedOperator(type: string): string {
    return this.conditionFor(type)?.operator ?? this.pendingOperators()[type] ?? DEFAULT_OPERATOR;
  }

  // Operators offered by the toggle group, backend-supplied so their labels and the set stay in step
  // with the registry; the local fallback only covers the first paint before /conditiontypes
  // answers.
  operatorOptions(type: string): ConditionOperatorMeta[] {
    const fromBackend = this.policyService.operatorsForConditionType(type);
    return fromBackend.length ? fromBackend : OPERATOR_FALLBACK;
  }

  // Options offered by the multi-select: currently valid values plus any the policy already
  // references that are no longer valid; the stale ones must be listed, or mat-select would render a
  // blank trigger for a value it has no option for.
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
  // this WebUI has no wording for gets the neutral hint instead of rendering blank.
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
  // rejects an empty list, and "restrict to nothing" has no useful reading -- dead under IN,
  // equivalent to no condition under NOT_IN.
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

  // Emitted in condition_type order, the backend's canonical order; conditions are ANDed so order
  // carries no meaning, but without a fixed one, removing and re-adding a condition would make the
  // edit page's JSON diff report a change that is not one.
  private emitUpsert(type: string, condition: LockoutPolicyCondition): void {
    const others = this.conditions().filter((existing) => existing.condition_type !== type);
    this.conditionsChange.emit([...others, condition].sort((a, b) => a.condition_type.localeCompare(b.condition_type)));
  }
}
