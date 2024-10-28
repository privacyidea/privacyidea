import {Injectable} from '@angular/core';
import {Sort} from '@angular/material/sort';

@Injectable({
  providedIn: 'root'
})
export class TableUtilsService {

  applyFilter(data: any[], filterValue: string, columns: { key: string }[]): any[] {
    const lowerFilterValue = filterValue.trim().toLowerCase();
    const filterKeys = columns.map(column => column.key);

    return data.filter(item =>
      filterKeys.some(key => {
        const value = String(item[key]).trim().toLowerCase();
        return lowerFilterValue === 'false' && item[key] === false // special case for boolean value 'false'
          ? true
          : value.includes(lowerFilterValue);
      })
    );
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
}
