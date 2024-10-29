import {Injectable} from '@angular/core';
import {Sort} from '@angular/material/sort';

@Injectable({
  providedIn: 'root'
})
export class TableUtilsService {

  applyFilter(data: any[], filterValue: string, columns: { key: string, label: string }[]): any[] {
    const lowerFilterValue = filterValue.trim().toLowerCase();
    const filterLabels = columns.map(column => column.label.toLowerCase() + ':');

    const filterValueSplit = lowerFilterValue.split(' ');
    const filterPairs = [] as { label: string; value: string }[];

    let currentLabel = '';
    let currentValue = '';
    let remainingFilterText = '';

    const findMatchingLabel = (tokens: string[]): string | null => {
      for (let i = 1; i <= tokens.length; i++) {
        const possibleLabel = tokens.slice(0, i).join(' ');
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
          filterPairs.push({ label: currentLabel.slice(0, -1), value: currentValue.trim() });
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
    if (currentLabel && currentValue) {
      filterPairs.push({ label: currentLabel.slice(0, -1), value: currentValue.trim() });
    }
    remainingFilterText = remainingFilterText.trim();

    return data.filter(item => {
      const filteredByLabelValues = filterPairs.every(({ label, value }) => {
        const column = columns.find(col => col.label.toLowerCase() === label);
        if (!column) {
          return false;
        }
        const itemValue = String(item[column.key]).trim().toLowerCase();
        return itemValue.includes(value);
      });

      if (!filteredByLabelValues) {
        return false;
      }

      if (remainingFilterText) {
        return columns.some(column => {
          const itemValue = String(item[column.key]).trim().toLowerCase();
          return itemValue.includes(remainingFilterText);
        });
      }

      return true;
    });
  }

  sortData(data: any[], sort: Sort, columns: { key: string }[]): any[] {
    if (!sort.active || sort.direction === '') return data;

    const isAsc = sort.direction === 'asc';
    const key = columns.find(column => column.key === sort.active)?.key;

    if (!key) return data;

    return data.slice().sort((a, b) => {
      const valueA = a[key];
      const valueB = b[key];
      return (valueA < valueB ? -1 : 1) * (isAsc ? 1 : -1);
    });
  }

  paginateData(data: any[], pageIndex: number, pageSize: number): any[] {
    const startIndex = pageIndex * pageSize;
    const endIndex = startIndex + pageSize;
    return data.slice(startIndex, endIndex);
  }
}
