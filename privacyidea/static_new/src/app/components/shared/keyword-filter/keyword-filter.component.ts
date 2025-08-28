import { NgClass } from "@angular/common";
import { Component, inject, Input, signal, WritableSignal } from "@angular/core";
import { MatFabButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { FilterValue } from "../../../core/models/filter_value";

@Component({
  selector: "app-keyword-filter",
  standalone: true,
  imports: [NgClass, MatIcon, MatFabButton],
  templateUrl: "./keyword-filter.component.html",
  styleUrl: "./keyword-filter.component.scss"
})
export class KeywordFilterComponent {
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  @Input() apiFilter: string[] = [];
  @Input() advancedApiFilter: string[] = [];
  @Input() filterHTMLInputElement!: HTMLInputElement;
  @Input() filterValue!: WritableSignal<FilterValue>;
  showAdvancedFilter = signal(false);

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword, this.filterHTMLInputElement);
  }

  onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.update((b) => !b);
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    if (filter === "infokey & infovalue") {
      return inputValue.hasKey("infokey") || inputValue.hasKey("infovalue");
    }
    if (filter === "machineid & resolver") {
      return inputValue.hasKey("machineid") || inputValue.hasKey("resolver");
    }
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string, currentValue: FilterValue): string {
    if (keyword === "active" || keyword === "assigned" || keyword === "success") {
      const value = currentValue.getValueOfKey(keyword)?.toLowerCase();
      if (!value) {
        return "add_circle";
      }
      return value === "true" ? "change_circle" : value === "false" ? "remove_circle" : "add_circle";
    } else {
      const isSelected = this.isFilterSelected(keyword, currentValue);
      return isSelected ? "remove_circle" : "add_circle";
    }
  }

  toggleFilter(filterKeyword: string, inputElement: HTMLInputElement): void {
    let newValue;
    var textValue = inputElement.value.trim();
    if (filterKeyword === "active" || filterKeyword === "assigned" || filterKeyword === "success") {
      newValue = this.tableUtilsService.toggleBooleanInFilter({
        keyword: filterKeyword,
        currentValue: textValue
      });
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter(textValue, filterKeyword);
    }
    inputElement.value = newValue;
    this.filterValue.set(new FilterValue({ value: newValue }));
    inputElement.focus();
  }

  filterIsEmpty(): boolean {
    const inputText = this.filterHTMLInputElement?.value.trim() ?? "";
    const current = this.filterValue?.() ?? {};
    return inputText === "" && Object.keys(current).length === 0;
  }
}
