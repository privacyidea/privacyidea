import { Injectable } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';

interface FilterPair {
  key: string;
  value: string;
}

@Injectable({
  providedIn: 'root',
})
export class TableUtilsService {
  emptyDataSource<T>(
    pageSize: number,
    columnsKeyMap: { key: string; label: string }[],
  ): MatTableDataSource<T> {
    return new MatTableDataSource(
      Array.from({ length: pageSize }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    );
  }

  parseFilterString(
    filterValue: string,
    apiFilter: string[],
  ): {
    filterPairs: FilterPair[];
    remainingFilterText: string;
  } {
    const lowerFilterValue = filterValue.trim().toLowerCase();
    const filterLabels = apiFilter.flatMap((column) => {
      if (column === 'infokey & infovalue') {
        return ['infokey:', 'infovalue:'];
      }
      if (column === 'machineid & resolver') {
        return ['machineid:', 'resolver:'];
      }
      return column.toLowerCase() + ':';
    });
    const filterValueSplit = lowerFilterValue.split(' ');
    const filterPairs: FilterPair[] = [];

    let currentLabel = '';
    let currentValue = '';
    let remainingFilterText = '';

    const findMatchingLabel = (parts: string[]): string | null => {
      for (let i = 1; i <= parts.length; i++) {
        const possibleLabel = parts.slice(0, i).join(' ');
        if (filterLabels.includes(possibleLabel)) {
          return possibleLabel;
        }
      }
      return null;
    };

    let i = 0;
    while (i < filterValueSplit.length) {
      const parts = filterValueSplit.slice(i);
      let matchingLabel = findMatchingLabel(parts);

      if (!matchingLabel) {
        const token = parts[0];
        for (const label of filterLabels) {
          if (token.startsWith(label)) {
            matchingLabel = label;
            if (currentLabel && currentValue) {
              filterPairs.push({
                key: currentLabel.slice(0, -1),
                value: currentValue.trim(),
              });
            }
            currentLabel = matchingLabel;
            currentValue = token.slice(label.length) + ' ';
            i += 1;
            break;
          }
        }
        if (matchingLabel === currentLabel) {
          continue;
        }
      }

      if (matchingLabel) {
        if (currentLabel && currentValue) {
          filterPairs.push({
            key: currentLabel.slice(0, -1),
            value: currentValue.trim(),
          });
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
        key: currentLabel.slice(0, -1),
        value: currentValue.trim(),
      });
    }

    return { filterPairs, remainingFilterText: remainingFilterText.trim() };
  }

  toggleKeywordInFilter(currentValue: string, keyword: string): string {
    if (keyword.includes('&')) {
      const keywords = keyword.split('&').map((k) => k.trim());
      let newValue = currentValue;
      for (const key of keywords) {
        newValue = this.toggleKeywordInFilter(newValue, key);
      }
      return newValue;
    }
    const keywordPattern = new RegExp(
      `\\b${keyword}:.*?(?=(\\s+\\w+:|$))`,
      'i',
    );
    if (keywordPattern.test(currentValue)) {
      return currentValue
        .replace(keywordPattern, ' ')
        .trimStart()
        .replace(/\s{2,}/g, ' ');
    } else {
      if (currentValue.length > 0) {
        return (currentValue + ` ${keyword}: `).replace(/\s{2,}/g, ' ');
      } else {
        return `${keyword}: `;
      }
    }
  }

  public toggleBooleanInFilter(args: {
    keyword: string;
    currentValue: string;
  }): string {
    const { keyword, currentValue } = args;
    console.debug(
      `Toggling boolean for keyword: ${keyword}, currentValue: ${currentValue}`,
    );
    const regex = new RegExp(
      `\\b${keyword}:\\s?([\\w\\d]*)(?![\\w\\d]*:)`,
      'i',
    );
    const match = currentValue.match(regex);

    if (!match) {
      return (currentValue.trim() + ` ${keyword}: true`).trim();
    } else {
      const existingValue = match[1].toLowerCase();

      if (existingValue === 'true') {
        return currentValue.replace(regex, keyword + ': false');
      } else if (existingValue === 'false') {
        const removed = currentValue.replace(regex, '').trim();
        return removed.replace(/\s{2,}/g, ' ');
      } else {
        return currentValue.replace(regex, keyword + ': true');
      }
    }
  }

  public recordsFromText(textValue: string): Record<string, string> {
    const mapValue = {} as Record<string, string>;
    const regex = /(\w+):\s*([^:]*?)(?=\s+\w+:|$)/g;
    let match;
    while ((match = regex.exec(textValue)) !== null) {
      const key = match[1].trim();
      const value = match[2].trim();
      if (key) {
        mapValue[key] = value;
      }
    }
    return mapValue;
  }

  isLink(columnKey: string) {
    return (
      columnKey === 'username' ||
      columnKey === 'container_serial' ||
      columnKey === 'user_realm' ||
      columnKey === 'users' ||
      columnKey === 'user_realm' ||
      columnKey === 'realms'
    );
  }

  getClassForColumn(columnKey: string, element: any): string {
    if (element['locked'] || element['revoked']) {
      return 'highlight-disabled';
    }
    if (columnKey === 'active') {
      if (element['active'] === '') {
        return '';
      }
      if (element['active'] === false) {
        return 'highlight-false-clickable';
      } else if (element['active']) {
        return 'highlight-true-clickable';
      }
    } else if (columnKey === 'failcount') {
      if (element['failcount'] === '') {
        return '';
      }
      if (element['failcount'] === 0) {
        return 'highlight-true';
      } else if (
        element['failcount'] > 0 &&
        element['failcount'] < element['maxfail']
      ) {
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
      } else if (element['active'] === false) {
        return 'deactivated';
      }
    }
    return element[columnKey];
  }

  getSpanClassForKey(key: string, value: any, maxfail: any): string {
    if (key === 'description') {
      return 'details-table-item details-description';
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
      return 'flex-center';
    }
    return 'table-scrollable-container';
  }

  getDisplayTextForKeyAndRevoked(
    key: string,
    value: any,
    revoked: boolean,
  ): string {
    if (value === '') {
      return '';
    }
    if (key === 'active') {
      return revoked ? 'revoked' : value ? 'active' : 'deactivated';
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

  getSpanClassForState(state: string, clickable: boolean): string {
    switch (clickable) {
      case false:
        if (state === 'active') {
          return 'highlight-true';
        } else if (state === 'disabled') {
          return 'highlight-false';
        } else {
          return '';
        }
      case true:
        if (state === 'active') {
          return 'highlight-true-clickable';
        } else if (state === 'disabled') {
          return 'highlight-false-clickable';
        } else {
          return '';
        }
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
