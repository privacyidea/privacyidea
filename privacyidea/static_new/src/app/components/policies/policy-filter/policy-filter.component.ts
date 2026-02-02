import { Component, input, model, output } from "@angular/core";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { FilterValueGeneric } from "../../../core/models/filter_value_generic/filter_value_generic";
import { PolicyDetail } from "../../../services/policies/policies.service";

@Component({
  selector: "app-policy-filter",
  standalone: true,
  imports: [MatInputModule, ClearableInputComponent],
  templateUrl: "./policy-filter.component.html",
  styleUrl: "./policy-filter.component.scss"
})
export class PolicyFilterComponent {
  filter = model.required<FilterValueGeneric<PolicyDetail>>();
  unfilteredPolicies = input.required<PolicyDetail[]>();
  filteredPoliciesChange = output<PolicyDetail[]>();

  clearFilter(): void {
    this.filter.set(this.filter().clear());
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
