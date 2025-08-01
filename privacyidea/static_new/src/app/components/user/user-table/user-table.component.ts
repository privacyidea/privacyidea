import {
  Component,
  effect,
  inject,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource,
} from '@angular/material/table';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { ContentService } from '../../../services/content/content.service';
import { UserData, UserService } from '../../../services/user/user.service';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';

const columnKeysMap = [
  { key: 'username', label: 'Username' },
  { key: 'userid', label: 'User ID' },
  { key: 'givenname', label: 'Given Name' },
  { key: 'surname', label: 'Surname' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'mobile', label: 'Mobile' },
  { key: 'description', label: 'Description' },
  { key: 'resolver', label: 'Resolver' },
];

@Component({
  selector: 'app-user-table',
  imports: [
    FormsModule,
    KeywordFilterComponent,
    MatCell,
    MatCellDef,
    MatFormField,
    MatLabel,
    MatInput,
    MatPaginator,
    MatTable,
    MatSortModule,
    MatHeaderCell,
    MatColumnDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatRow,
    MatNoDataRow,
    MatHeaderCellDef,
    RouterLink,
  ],
  templateUrl: './user-table.component.html',
  styleUrl: './user-table.component.scss',
})
export class UserTableComponent {
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map(
    (column) => column.key,
  );
  private tableUtilsService = inject(TableUtilsService);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  protected contentService = inject(ContentService);
  protected userService = inject(UserService);
  filterValueString: WritableSignal<string> = linkedSignal(() =>
    Object.entries(this.userService.filterValue())
      .map(([key, value]) => `${key}: ${value}`)
      .join(' '),
  );
  totalLength: WritableSignal<number> = linkedSignal({
    source: this.userService.usersResource.value,
    computation: (userResource, previous) => {
      if (userResource) {
        return userResource.result?.value?.length ?? 0;
      }
      return previous?.value ?? 0;
    },
  });
  emptyResource: WritableSignal<UserData[]> = linkedSignal({
    source: this.userService.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () =>
        Object.fromEntries(
          this.columnKeysMap.map((c) => [{ key: c.key, username: '' }]),
        ),
      ),
  });
  usersDataSource: WritableSignal<MatTableDataSource<UserData>> = linkedSignal({
    source: this.userService.usersResource.value,
    computation: (userResource, previous) => {
      if (userResource) {
        const dataSource = new MatTableDataSource(userResource.result?.value);
        dataSource.paginator = this.paginator;
        dataSource.sort = this.sort;
        return dataSource;
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    },
  });

  constructor() {
    effect(() => {
      const recordsFromText = this.tableUtilsService.recordsFromText(
        this.filterValueString(),
      );
      this.userService.filterValue.set(recordsFromText);
      this.userService.pageIndex.set(0);
    });
  }
}
