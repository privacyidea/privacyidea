import { Injectable, WritableSignal } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Sort } from '@angular/material/sort';

interface FilterPair {
  key: string;
  value: string;
}

@Injectable({
  providedIn: 'root',
})
export class TableUtilsService {
  parseFilterString(
    filterValue: string,
    apiFilter: string[],
  ): {
    filterPairs: FilterPair[];
    remainingFilterText: string;
  } {
    const lowerFilterValue = filterValue.trim();
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
        .replace(keywordPattern, '')
        .trim()
        .replace(/\s{2,}/g, ' ');
    } else {
      if (currentValue.length > 0) {
        return (currentValue + ` ${keyword}: `).replace(/\s{2,}/g, ' ');
      } else {
        return `${keyword}: `;
      }
    }
  }

  public toggleActiveInFilter(currentValue: string): string {
    const activeRegex = /active:\s*(\S+)/i;
    const match = currentValue.match(activeRegex);

    if (!match) {
      return (currentValue.trim() + ' active: true').trim();
    } else {
      const existingValue = match[1].toLowerCase();

      if (existingValue === 'true') {
        return currentValue.replace(activeRegex, 'active: false');
      } else if (existingValue === 'false') {
        const removed = currentValue.replace(activeRegex, '').trim();
        return removed.replace(/\s{2,}/g, ' ');
      } else {
        return currentValue.replace(activeRegex, 'active: true');
      }
    }
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
    if (columnKey === 'active') {
      if (element['active'] === '') {
        return '';
      }
      if (element['locked'] || element['revoked']) {
        return 'highlight-false';
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
      } else if (
        element['failcount'] > 0 &&
        element['failcount'] < element['maxfail']
      ) {
        if (element['locked'] || element['revoked']) {
          return 'highlight-warning';
        } else {
          return 'highlight-warning-clickable';
        }
      } else {
        if (element['locked'] || element['revoked']) {
          return 'highlight-false';
        } else {
          return 'highlight-false-clickable';
        }
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
      return 'flex ali-center';
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

  handlePageEvent(
    event: PageEvent,
    pageIndex: WritableSignal<number>,
    pageSize: WritableSignal<number>,
  ) {
    pageSize.set(event.pageSize);
    pageIndex.set(event.pageIndex);
  }

  handleSortEvent(
    sort: Sort,
    pageIndex: WritableSignal<number>,
    sortby_sortdir: WritableSignal<Sort>,
    fetchData: () => void,
  ) {
    let { active, direction } = sort;
    if (!direction) {
      active = '';
      direction = '';
    } else if (active === 'active') {
      direction = direction === 'asc' ? 'desc' : 'asc';
    }

    sortby_sortdir.set({ active, direction });
    pageIndex.set(0);
    fetchData();
  }
}
