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
  @Input() tableUtilsService!: TableUtilsService;
  @Input() filterValue!: WritableSignal<string>;
  @Input() keywordClick!: WritableSignal<string>;
  showAdvancedFilter = signal(false);

  onKeywordClick(filterKeyword: string): void {
    this.keywordClick.set(filterKeyword);
  }

  onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.set(!this.showAdvancedFilter());
  }

  isFilterSelected(filter: string, inputValue: string): boolean {
    if (filter === 'infokey & infovalue') {
      const regexKey = new RegExp(`\\binfokey:`, 'i');
      const regexValue = new RegExp(`\\binfovalue:`, 'i');
      return regexKey.test(inputValue) || regexValue.test(inputValue);
    }
    if (filter === 'machineid & resolver') {
      const regexKey = new RegExp(`\\bmachineid:`, 'i');
      const regexValue = new RegExp(`\\bresolver:`, 'i');
      return regexKey.test(inputValue) || regexValue.test(inputValue);
    }
    const regex = new RegExp(`\\b${filter}:`, 'i');
    return regex.test(inputValue);
  }

  public getFilterIconName(keyword: string, currentValue: string): string {
    if (keyword === 'active') {
      const activeMatch = currentValue.match(/active:\s*(\S+)/i);
      if (!activeMatch) {
        return 'add_circle';
      }

      const activeValue = activeMatch[1].toLowerCase();
      if (activeValue === 'true') {
        return 'change_circle';
      } else if (activeValue === 'false') {
        return 'remove_circle';
      } else {
        return 'add_circle';
      }
    } else {
      const isSelected = this.isFilterSelected(keyword, currentValue);
      return isSelected ? 'remove_circle' : 'add_circle';
    }
  }
}
