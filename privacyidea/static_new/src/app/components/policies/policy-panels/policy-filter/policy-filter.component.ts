import { Component, effect, input, output, signal } from "@angular/core";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import {
  FilterKeyword,
  KeywordFilterGenericComponent
} from "../../../shared/keyword-filter-generic/keyword-filter-generic.component";
import { FilterValueGeneric } from "../../../../core/models/filter_value_generic/filter_value_generic";
import { PolicyDetail } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-policy-filter",
  standalone: true,
  imports: [MatInputModule, ClearableInputComponent, KeywordFilterGenericComponent],
  templateUrl: "./policy-filter.component.html",
  styleUrl: "./policy-filter.component.scss"
})
export class PolicyFilterComponent {
  filterValue = signal<FilterValueGeneric>(new FilterValueGeneric());
  filteredPoliciesChange = output<PolicyDetail[]>();
  unfilteredPolicies = input.required<PolicyDetail[]>();

  constructor() {
    effect(() => {
      const currentFilter = this.filterValue();
      // Logic to fetch/filter policies...
      const results = this.filterData(currentFilter);
      this.filteredPoliciesChange.emit(results);
    });
  }
  filterData(currentFilter: FilterValueGeneric): PolicyDetail[] {
    const unfilteredPolicies = this.unfilteredPolicies();
    if (!currentFilter || currentFilter.isEmpty) {
      return unfilteredPolicies;
    }
    const filteredPolicies: PolicyDetail[] = [];
    for (const policy of unfilteredPolicies) {
      const activeString = currentFilter.getValueOfKey("active");
      if (activeString) {
        const isActive = activeString.toLowerCase() === "true";
        if (policy.active !== isActive) {
          continue;
        }
      }
      const priorityString = currentFilter.getValueOfKey("priority");
      if (priorityString) {
      }
    }
    return filteredPolicies;
  }

  policyFilters = [
    new FilterKeyword<PolicyDetail>({
      key: "priority",
      label: $localize`Priority`,
      matches: (item: PolicyDetail, filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("priority");
        // Example of priority filter ">5" or "<5" or "=5" or "!=5" or "3-5" or ">=5" or "<=5"
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
    new FilterKeyword({
      key: "active",
      label: $localize`Active`,
      toggle: (filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("active")?.toLowerCase();
        if (value === "true") return filterValue.setValueOfKey("active", "false");
        if (value === "false") return filterValue.removeKey("active");
        return filterValue.setValueOfKey("active", "true");
      },
      iconName: (filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("active")?.toLowerCase();
        if (value === "true") return "change_circle";
        if (value === "false") return "remove_circle";
        return "add_circle";
      },
      matches: (item: PolicyDetail, filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("active")?.toLowerCase();
        if (value === "true") return item.active === true;
        if (value === "false") return item.active === false;
        return true;
      }
    }),
    new FilterKeyword({
      key: "policy_name",
      label: $localize`Policy Name`,
      matches: (item: PolicyDetail, filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("policy_name");
        if (!value) return true;
        return item.name.includes(value);
      }
    }),
    new FilterKeyword({
      key: "scope",
      label: $localize`Scope`,
      matches: (item: PolicyDetail, filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("scope");
        if (!value) return true;
        return item.scope.includes(value);
      }
    }),
    new FilterKeyword({
      key: "actions",
      label: $localize`Actions`,
      matches: (item: PolicyDetail, filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("actions");
        if (!value) return true;
        return Object.keys(item.action || {}).some((actionName) => actionName.includes(value));
      }
    }),
    new FilterKeyword({
      key: "realm",
      label: $localize`Realm`,
      matches: (item: PolicyDetail, filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("realm");
        if (!value) return true;
        return item.realm.includes(value);
      }
    })
  ];

  clearFilter(): void {
    this.filterValue.set(new FilterValueGeneric());
  }

  onFilterChange(filterChangeEvent: Event): void {
    const filterString = (filterChangeEvent.target as HTMLInputElement)?.value;
    if (filterString === undefined) {
      console.warn("Filter change event did not contain a valid input value.");
      return;
    }
    this.filterValue.set(new FilterValueGeneric({ value: filterString }));
  }
}
