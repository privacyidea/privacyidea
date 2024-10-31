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
    const lowerFilterValue = filterValue.trim().toLowerCase(); // TODO lower case doesn't work for container
    const filterLabels = apiFilter.map(column => column.toLowerCase() + ':');
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
    if (currentLabel && currentValue) {
      filterPairs.push({label: currentLabel.slice(0, -1), value: currentValue.trim()});
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
    const regex = new RegExp(`\\b${filter}:`, 'i');
    return regex.test(inputValue);
  }
}
