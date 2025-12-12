import { Component, input, output, signal } from "@angular/core";
import { KeywordFilterComponent } from "../../../shared/keyword-filter/keyword-filter.component";
import { FilterValue } from "../../../../core/models/filter_value";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-policy-filter",
  standalone: true,
  imports: [KeywordFilterComponent, MatInputModule, ClearableInputComponent],
  templateUrl: "./policy-filter.component.html",
  styleUrl: "./policy-filter.component.scss"
})
export class PolicyFilterComponent {
  filterValueChange = output<FilterValue>();
  filterValue = input.required<FilterValue>();

  clearFilter(): void {
    this.filterValueChange.emit(new FilterValue());
  }

  onFilterChange(filterChangeEvent: Event): void {
    const filterString = (filterChangeEvent.target as HTMLInputElement)?.value;
    if (filterString === undefined) {
      console.warn("Filter change event did not contain a valid input value.");
      return;
    }
    this.filterValueChange.emit(new FilterValue({ value: filterString }));
  }
}
