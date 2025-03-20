import {
  Component,
  effect,
  ElementRef,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { AuthService } from '../../../services/auth/auth.service';
import { Router } from '@angular/router';
import { NgClass } from '@angular/common';
import { ContainerService } from '../../../services/container/container.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { TokenSelectedContent } from '../token.component';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';

const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'type', label: 'Type' },
  { key: 'states', label: 'Status' },
  { key: 'description', label: 'Description' },
  { key: 'users', label: 'User' },
  { key: 'user_realm', label: 'Realm' },
  { key: 'realms', label: 'Container Realms' },
];

@Component({
  selector: 'app-container-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    KeywordFilterComponent,
    CopyButtonComponent,
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.scss',
})
export class ContainerTableComponent {
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() containerSerial!: WritableSignal<string>;
  sortby_sortdir: WritableSignal<Sort> = signal({
    active: 'serial',
    direction: 'asc',
  });
  length = signal(0);
  pageSize = signal(10);
  pageIndex = signal(0);
  filterValue = signal('');
  dataSource = signal(
    new MatTableDataSource(
      Array.from({ length: this.pageSize() }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    ),
  );
  clickedKeyword = signal<string>('');
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.containerService.apiFilter;
  advancedApiFilter = this.containerService.advancedApiFilter;
  columnsKeyMap = columnsKeyMap;
  @ViewChild('filterInput') inputElement!: ElementRef<HTMLInputElement>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  constructor(
    private router: Router,
    private authService: AuthService,
    private containerService: ContainerService,
    private notificationService: NotificationService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      this.filterValue();
      this.fetchContainerData();
    });
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  handleStateClick(element: any) {
    this.containerService
      .toggleActive(element.serial, element.states)
      .subscribe({
        next: () => {
          this.fetchContainerData();
        },
        error: (error) => {
          console.error('Failed to toggle active.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to toggle active. ' + message,
          );
        },
      });
  }

  containerSelected(containerSerial: string) {
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  protected fetchContainerData = () => {
    this.containerService
      .getContainerData({
        page: this.pageIndex() + 1,
        pageSize: this.pageSize(),
        sort: this.sortby_sortdir(),
        filterValue: this.filterValue(),
      })
      .subscribe({
        next: (response) => {
          this.length.set(response.result.value.count);
          this.processDataSource(response.result.value.containers);
        },
      });
  };

  private processDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      users:
        item.users && item.users.length > 0 ? item.users[0]['user_name'] : '',
      user_realm:
        item.users && item.users.length > 0 ? item.users[0]['user_realm'] : '',
    }));
    this.dataSource.set(new MatTableDataSource(processedData));
  }
}
