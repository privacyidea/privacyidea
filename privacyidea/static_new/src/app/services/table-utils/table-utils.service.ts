import {Injectable} from '@angular/core';

interface FilterPair {
  label: string;
  value: string;
}

@Injectable({
  providedIn: 'root'
})
export class TableUtilsService {
  parseFilterString(filterValue: string, apiFilter: string[]): {
    filterPairs: FilterPair[],
    remainingFilterText: string
  } {
    const lowerFilterValue = filterValue.trim();
    const filterLabels = apiFilter.flatMap(column => {
      if (column === 'infokey & infovalue') {
        return ['infokey:', 'infovalue:'];
      }
      return column.toLowerCase() + ':'
    });
    const filterValueSplit = lowerFilterValue.split(' ');
    const filterPairs: FilterPair[] = [];

    let currentLabel = '';
    let currentValue = '';
    let remainingFilterText = '';

    const findMatchingLabel = (filterValueSplit: string[]): string | null => {
      for (let i = 1; i <= filterValueSplit.length; i++) {
        const possibleLabel = filterValueSplit.slice(0, i).join(' ');
        if (filterLabels.includes(possibleLabel)) {
          return possibleLabel;
        }
      }
      return null;
    };

    let i = 0;
    while (i < filterValueSplit.length) {
      const remainingFilterValues = filterValueSplit.slice(i);
      const matchingLabel = findMatchingLabel(remainingFilterValues);

      if (matchingLabel) {
        if (currentLabel && currentValue) {
          filterPairs.push({label: currentLabel.slice(0, -1), value: currentValue.trim()});
        }
        currentLabel = matchingLabel;
        currentValue = '';
        i += matchingLabel.split(' ').length;
      } else if (currentLabel) {
        currentValue += filterValueSplit[i] + ' ';
        i++;
      } else {
        remainingFilterText += filterValueSplit[i] + ' ';
        i++;
      }
    }
    if (currentLabel) {
      filterPairs.push({
        label: currentLabel.slice(0, -1),
        value: currentValue.trim()
      });
    }

    return {filterPairs, remainingFilterText: remainingFilterText.trim()};
  }

  toggleKeywordInFilter(currentValue: string, keyword: string): string {
    const keywordPattern = new RegExp(`\\b${keyword}:.*?(?=(\\s+\\w+:|$))`, 'i');
    if (keywordPattern.test(currentValue)) {
      return currentValue.replace(keywordPattern, '').trim().replace(/\s{2,}/g, ' ');
    } else {
      if (currentValue.length > 0) {
        return (currentValue + ` ${keyword}: `).replace(/\s{2,}/g, ' ');
      } else {
        return `${keyword}: `;
      }
    }
  }

  isFilterSelected(filter: string, inputValue: string): boolean {
    if (filter === 'infokey & infovalue') {
      const regexKey = new RegExp(`\\binfokey:`, 'i');
      const regexValue = new RegExp(`\\binfovalue:`, 'i');
      return regexKey.test(inputValue) || regexValue.test(inputValue);
    }
    const regex = new RegExp(`\\b${filter}:`, 'i');
    return regex.test(inputValue);
  }

  isLink(columnKey: string) {
    return columnKey === 'username'
      || columnKey === 'container_serial'
      || columnKey === 'user_realm'
      || columnKey === 'users'
      || columnKey === 'user_realm'
      || columnKey === 'realms';
  }

  getClassForColumn(columnKey: string, element: any): string {
    if (columnKey === 'active') {
      if (element['active'] === '') {
        return '';
      }
      if (element['locked']) {
        return 'highlight-false-clickable';
      } else if (element['revoked']) {
        return 'highlight-false-clickable';
      } else if (element['active'] === false) {
        return 'highlight-false-clickable';
      } else {
        return 'highlight-true-clickable';
      }
    } else if (columnKey === 'failcount') {
      if (element['failcount'] === '') {
        return '';
      }
      if (element['failcount'] === 0) {
        return 'highlight-true';
      } else if (element['failcount'] > 0 && element['failcount'] < element['maxfail']) {
        return 'highlight-warning-clickable';
      } else {
        return 'highlight-false-clickable';
      }
    }
    return '';
  }

  getDisplayText(columnKey: string, element: any): string {
    if (columnKey === 'active') {
      if (element['active'] === '') {
        return '';
      }
      if (element['revoked']) {
        return 'revoked';
      } else if (element['locked']) {
        return 'locked';
      } else if (element['active']) {
        return 'active';
      } else {
        return 'deactivated';
      }
    }
    return element[columnKey];
  }

  getSpanClassForKey(key: string, value: any, maxfail: any): string {
    if (key === 'description') {
      return 'details-table-item details-description'
    }
    if (key === 'active') {
      if (value === '') {
        return '';
      }
      return value === true ? 'highlight-true' : 'highlight-false';
    }
    if (key === 'failcount') {
      if (value === '') {
        return '';
      } else if (value === 0) {
        return 'highlight-true';
      } else if (value >= 1 && value < maxfail) {
        return 'highlight-warning';
      } else {
        return 'highlight-false';
      }
    }
    return 'details-table-item';
  }

  getDivClassForKey(key: string) {
    if (key === 'description') {
      return 'details-scrollable-container';
    } else if (
      key === 'maxfail' ||
      key === 'count_window' ||
      key === 'sync_window'
    ) {
      return 'details-value';
    }

    return '';
  }

  getClassForColumnKey(columnKey: string): string {
    if (columnKey === 'description') {
      return 'table-scrollable-container description';
    } else if (columnKey === 'failcount') {
      return 'failcount';
    } else if (columnKey !== 'realms') {
      return 'flex ali-center';
    }
    return 'table-scrollable-container';
  }

  getDisplayTextForKeyAndRevoked(key: string, value: any, revoked: boolean): string {
    if (value === '') {
      return '';
    }
    if (key === 'active') {
      return revoked ? 'revoked' : (value ? 'active' : 'deactivated');
    }
    return value;
  }

  getTdClassForKey(key: string) {
    const classes = ['fix-width-20-padr-0'];
    if (key === 'description') {
      classes.push('height-104');
    } else if (['realms', 'tokengroup'].includes(key)) {
      classes.push('height-78');
    } else {
      classes.push('height-52');
    }
    return classes;
  }

  getSpanClassForState(state: string) {
    if (state === 'active') {
      return 'highlight-true-clickable';
    } else if (state === 'disabled') {
      return 'highlight-false-clickable';
    } else {
      return '';
    }
  }

  getDisplayTextForState(state: string) {
    if (state === 'active') {
      return 'active';
    } else if (state === 'disabled') {
      return 'deactivated';
    } else {
      return state;
    }
  }
}

