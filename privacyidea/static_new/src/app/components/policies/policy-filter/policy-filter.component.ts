import { Component, computed, effect, input, output, signal } from "@angular/core";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import {
  FilterOption as FilterOption,
  KeywordFilterGenericComponent
} from "../../shared/keyword-filter-generic/keyword-filter-generic.component";
import { FilterValueGeneric as GenericFilter } from "../../../core/models/filter_value_generic/filter_value_generic";
import { PolicyDetail } from "../../../services/policies/policies.service";

@Component({
  selector: "app-policy-filter",
  standalone: true,
  imports: [MatInputModule, ClearableInputComponent, KeywordFilterGenericComponent],
  templateUrl: "./policy-filter.component.html",
  styleUrl: "./policy-filter.component.scss"
})
export class PolicyFilterComponent {
  policyFilterOptions = [
    new FilterOption<PolicyDetail>({
      key: "priority",
      label: $localize`Priority`,
      hint: $localize`Filter by priority. Use operators like >, <, =, !=, >=, <= or range (e.g., 3-5). When no operator is specified, exact match is used.`,
      matches: (item: PolicyDetail, filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("priority");
        if (!value) return true;
        const priority = item.priority;
        try {
          if (value.startsWith(">=")) {
            const num = parseInt(value.substring(2), 10);
            return priority >= num;
          } else if (value.startsWith("<=")) {
            const num = parseInt(value.substring(2), 10);
            return priority <= num;
          } else if (value.startsWith(">")) {
            const num = parseInt(value.substring(1), 10);
            return priority > num;
          } else if (value.startsWith("<")) {
            const num = parseInt(value.substring(1), 10);
            return priority < num;
          } else if (value.startsWith("!=")) {
            const num = parseInt(value.substring(2), 10);
            return priority !== num;
          } else if (value.startsWith("=")) {
            const num = parseInt(value.substring(1), 10);
            return priority === num;
          } else if (value.includes("-")) {
            const [minStr, maxStr] = value.split("-");
            const min = parseInt(minStr, 10);
            const max = parseInt(maxStr, 10);
            return priority >= min && priority <= max;
          } else {
            const num = parseInt(value, 10);
            return priority === num;
          }
        } catch {
          return false;
        }
      }
    }),
    new FilterOption({
      key: "active",
      label: $localize`Active`,
      hint: $localize`Filter by active status.`,
      toggle: (filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("active")?.toLowerCase();
        if (value === "true") return filter.setValueOfKey("active", "false");
        if (value === "false") return filter.removeKey("active");
        return filter.setValueOfKey("active", "true");
      },
      iconName: (filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("active")?.toLowerCase();
        if (value === "true") return "change_circle";
        if (value === "false") return "remove_circle";
        return "add_circle";
      },
      matches: (item: PolicyDetail, filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("active")?.toLowerCase();
        if (value === "true") return item.active === true;
        if (value === "false") return item.active === false;
        return true;
      }
    }),
    new FilterOption({
      key: "policy_name",
      label: $localize`Policy Name`,
      hint: $localize`Filter by policy name.`,
      matches: (item: PolicyDetail, filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("policy_name");
        if (!value) return true;
        return item.name.includes(value);
      }
    }),
    new FilterOption({
      key: "scope",
      label: $localize`Scope`,
      hint: $localize`Filter by scope.`,
      matches: (item: PolicyDetail, filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("scope");
        if (!value) return true;
        return item.scope.includes(value);
      }
    }),
    new FilterOption({
      key: "actions",
      label: $localize`Actions`,
      hint: $localize`Filter by action names.`,
      matches: (item: PolicyDetail, filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("actions");
        if (!value) return true;
        return Object.keys(item.action || {}).some((actionName) => actionName.includes(value));
      }
    }),
    new FilterOption({
      key: "realm",
      label: $localize`Realm`,
      hint: $localize`Filter by realm.`,
      matches: (item: PolicyDetail, filter: GenericFilter<PolicyDetail>) => {
        const value = filter.getValueOfKey("realm");
        if (!value) return true;
        return item.realm.includes(value);
      }
    })
  ];

  filter = signal<GenericFilter<PolicyDetail>>(new GenericFilter({ availableFilters: this.policyFilterOptions }));
  unfilteredPolicies = input.required<PolicyDetail[]>();

  filteredPolicies = computed(() => this.filterData(this.unfilteredPolicies(), this.filter()));

  filteredPoliciesChange = output<PolicyDetail[]>();

  constructor() {
    effect(() => this.filteredPoliciesChange.emit(this.filteredPolicies()));
  }

  filterData(unfilteredPolicies: PolicyDetail[], filter: GenericFilter<PolicyDetail>): PolicyDetail[] {
    return filter.filterItems(unfilteredPolicies);
  }

  clearFilter(): void {
    this.filter.set(new GenericFilter({ availableFilters: this.policyFilterOptions }));
  }

  onFilterChange(filterChangeEvent: Event): void {
    const filterString = (filterChangeEvent.target as HTMLInputElement)?.value;
    if (filterString === undefined) {
      console.warn("Filter change event did not contain a valid input value.");
      return;
    }
    const oldFilter = this.filter();
    const updatedFilter = oldFilter.setByString(filterString);
    this.filter.set(updatedFilter);
  }
}
