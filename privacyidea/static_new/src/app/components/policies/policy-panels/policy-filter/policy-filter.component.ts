import { Component, input, output, signal } from "@angular/core";
import { KeywordFilterComponent } from "../../../shared/keyword-filter/keyword-filter.component";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import {
  FilterKeyword,
  KeywordFilterGenericComponent
} from "../../../shared/keyword-filter-generic/keyword-filter-generic.component";
import { FilterValueGeneric } from "../../../../core/models/filter_value_generic/filter_value_generic";

@Component({
  selector: "app-policy-filter",
  standalone: true,
  imports: [MatInputModule, ClearableInputComponent, KeywordFilterGenericComponent],
  templateUrl: "./policy-filter.component.html",
  styleUrl: "./policy-filter.component.scss"
})
export class PolicyFilterComponent {
  filterValueChange = output<FilterValueGeneric>();
  filterValue = input.required<FilterValueGeneric>();

  policyFilters = [
    new FilterKeyword({ key: "priority", label: $localize`Priority` }),
    new FilterKeyword({
      key: "active",
      label: $localize`Active`,
      toggle: (filterValue: FilterValueGeneric) => {
        const value = filterValue.getValueOfKey("active")?.toLowerCase();
        if (value === "true") {
          return filterValue.setValueOfKey("active", "false");
        }
        if (value === "false") {
          return filterValue.removeKey("active");
        }
        return filterValue.toggleKey("active");
      }
    }),
    new FilterKeyword({ key: "policy_name", label: $localize`Policy Name` }),
    new FilterKeyword({ key: "scope", label: $localize`Scope` }),
    new FilterKeyword({ key: "actions", label: $localize`Actions` }),
    new FilterKeyword({ key: "realm", label: $localize`Realm` })
  ];

  clearFilter(): void {
    this.filterValueChange.emit(new FilterValueGeneric());
  }

  onFilterChange(filterChangeEvent: Event): void {
    const filterString = (filterChangeEvent.target as HTMLInputElement)?.value;
    if (filterString === undefined) {
      console.warn("Filter change event did not contain a valid input value.");
      return;
    }
    this.filterValueChange.emit(new FilterValueGeneric({ value: filterString }));
  }
}
