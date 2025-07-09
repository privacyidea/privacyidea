import { Component, Input, signal, WritableSignal } from '@angular/core';
import { NgClass } from '@angular/common';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton } from '@angular/material/button';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';

@Component({
  selector: 'app-keyword-filter',
  standalone: true,
  imports: [NgClass, MatIcon, MatFabButton],
  templateUrl: './keyword-filter.component.html',
  styleUrl: './keyword-filter.component.scss',
})
export class KeywordFilterComponent {
  @Input() apiFilter!: string[];
  @Input() advancedApiFilter!: string[];
  @Input() filterHTMLInputElement!: HTMLInputElement;
  @Input() filterValue!: WritableSignal<Record<string, string>>;
  showAdvancedFilter = signal(false);

  constructor(private tableUtilsService: TableUtilsService) {}

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword, this.filterHTMLInputElement);
  }

  onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.update((b) => !b);
  }

  isFilterSelected(
    filter: string,
    inputValue: Record<string, string>,
  ): boolean {
    if (filter === 'infokey & infovalue') {
      return 'infokey' in inputValue || 'infovalue' in inputValue;
    }
    if (filter === 'machineid & resolver') {
      return 'machineid' in inputValue || 'resolver' in inputValue;
    }
    return filter in inputValue;
  }

  getFilterIconName(
    keyword: string,
    currentValue: Record<string, string>,
  ): string {
    if (
      keyword === 'active' ||
      keyword === 'assigned' ||
      keyword === 'success'
    ) {
      const value = currentValue[keyword]?.toLowerCase();
      if (!value) {
        return 'add_circle';
      }
      return value === 'true'
        ? 'change_circle'
        : value === 'false'
          ? 'remove_circle'
          : 'add_circle';
    } else {
      const isSelected = this.isFilterSelected(keyword, currentValue);
      return isSelected ? 'remove_circle' : 'add_circle';
    }
  }

  toggleFilter(filterKeyword: string, inputElement: HTMLInputElement): void {
    let newValue;
    var textValue = inputElement.value.trim();
    if (
      filterKeyword === 'active' ||
      filterKeyword === 'assigned' ||
      filterKeyword === 'success'
    ) {
      newValue = this.tableUtilsService.toggleBooleanInFilter({
        keyword: filterKeyword,
        currentValue: textValue,
      });
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter(
        textValue,
        filterKeyword,
      );
    }
    inputElement.value = newValue;
    const recordsFromText = this.tableUtilsService.recordsFromText(newValue);
    const recordValueFromText: Record<string, string> = { ...recordsFromText };

    this.filterValue.set(recordValueFromText);
    inputElement.focus();
  }

  filterIsEmpty(): boolean {
    const inputText = this.filterHTMLInputElement?.value.trim() ?? '';
    const current = this.filterValue?.() ?? {};
    return inputText === '' && Object.keys(current).length === 0;
  }
}
