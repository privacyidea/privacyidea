import {Component, Input, signal, ViewChild, WritableSignal} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule} from '@angular/material/sort';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {NgClass} from '@angular/common';
import {ContainerService} from '../../../services/container/container.service';
import {MatIcon} from '@angular/material/icon';
import {MatFabButton} from '@angular/material/button';
import {TableUtilsService} from '../../../services/table-utils/table-utils.service';

const columnsKeyMap = [
  {key: 'serial', label: 'Serial'},
  {key: 'type', label: 'Type'},
  {key: 'states', label: 'Status'},
  {key: 'description', label: 'Description'},
  {key: 'users', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'realms', label: 'Container Realms'},
];

@Component({
  selector: 'app-container-table',
  standalone: true,
  imports: [
    MatTableModule, MatFormFieldModule, MatInputModule, MatPaginatorModule,
    MatSortModule, NgClass, MatIcon, MatFabButton
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.scss'
})
export class ContainerTableComponent {
  displayedColumns: string[] = columnsKeyMap.map(column => column.key);
  length = 0;
  pageSize = 10;
  pageIndex = 0;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';
  apiFilter = this.containerService.apiFilter;
  advancedApiFilter = this.containerService.advancedApiFilter;
  sortby_sortdir: { active: string; direction: "asc" | "desc" | "" } | undefined;
  @Input() containerIsSelected!: WritableSignal<boolean>;
  @Input() containerSerial!: WritableSignal<string>;
  dataSource = signal(new MatTableDataSource(
    Array.from({length: this.pageSize}, () => {
      const emptyRow: any = {};
      columnsKeyMap.forEach(column => {
        emptyRow[column.key] = '';
      });
      return emptyRow;
    })));
  showAdvancedFilter = signal(false);
  @ViewChild(MatPaginator) paginator: MatPaginator | null = null;
  @ViewChild(MatSort) sort: MatSort | null = null;
  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(private router: Router,
              private authService: AuthService,
              private containerService: ContainerService,
              protected tableUtilsService: TableUtilsService) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.warn('Redirected to login page', r));
    } else {
      this.fetchContainerData();
    }
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  handlePageEvent(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.fetchContainerData();
  }

  handleSortEvent() {
    this.sortby_sortdir = this.sort ? {
      active: this.sort.active,
      direction: this.sort.direction
    } : undefined;
    this.pageIndex = 0;
    this.fetchContainerData();
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.pageIndex = 0;
    this.fetchContainerData();
  }

  toggleKeywordInFilter(keyword: string, inputElement: HTMLInputElement): void {
    inputElement.value = this.tableUtilsService.toggleKeywordInFilter(inputElement.value.trim(), keyword);
    this.handleFilterInput({target: inputElement} as unknown as KeyboardEvent);
    inputElement.focus();
  }

  handleStateClick(element: any) {
    this.containerService.toggleActive(element.serial, element.states).subscribe({
      next: () => {
        this.fetchContainerData();
      },
      error: error => {
        console.error('Failed to toggle active', error);
      }
    });
  }

  containerSelected(containerSerial: string) {
    this.containerSerial.set(containerSerial);
    this.containerIsSelected.set(true)
  }

  private fetchContainerData() {
    this.containerService.getContainerData(
      this.pageIndex + 1, this.pageSize, this.sortby_sortdir, this.filterValue).subscribe({
      next: response => {
        this.length = response.result.value.count;
        this.processDataSource(response.result.value.containers);
      },
      error: error => {
        console.error('Failed to get container data', error);
      }
    });
  }

  private processDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      users: item.users && item.users.length > 0 ? item.users[0]["user_name"] : '',
      user_realm: item.users && item.users.length > 0 ? item.users[0]["user_realm"] : '',
    }));
    this.dataSource.set(new MatTableDataSource(processedData));
  }
}
