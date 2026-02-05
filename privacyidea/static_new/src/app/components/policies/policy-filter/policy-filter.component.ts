import { Component, ElementRef, inject, input, model, output, viewChild } from "@angular/core";
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
  readonly inputElement = viewChild.required<ElementRef<HTMLInputElement>>("filterHTMLInputElement");

  // TODO: FILTER WHEN THE INPUT CHANGES RATHER THAN ON ENTER PRESS or from model change

  constructor() {
    this.filter.subscribe((newFilter) => {
      const filteredPolicies = newFilter.filterItems(this.unfilteredPolicies());
      this.filteredPoliciesChange.emit(filteredPolicies);
    });
  }

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

  focusInput(): void {
    this.inputElement().nativeElement.focus();
  }
}
