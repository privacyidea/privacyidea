import {
  Component,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import {
  FetchDataHandler,
  FilterTable,
  SortDir,
  ProcessDataSource as ProcessDataSource,
  FetchDataResponse,
} from '../../universals/filter-table/filter-table.component';
import {
  OnClickTableColumn,
  SimpleTableColumn,
  TableColumn,
} from '../../../services/table-utils/table-column';
import { KeywordFilter } from '../../../services/keyword_filter';
import { ContainerService } from '../../../services/container/container.service';
import { ContainerData } from '../../../model/container/container-data';

@Component({
  selector: 'app-container-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    FilterTable,
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.scss',
})
export class ContainerTableComponent {
  sortby_sortdir: SortDir;
  @Input() selectedContent!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  showAdvancedFilter = signal(false);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  length = 0;
  pageSize = 10;
  pageIndex = 0;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';

  columns: TableColumn<ContainerData>[] = [
    new OnClickTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (container) => (container.serial ? [container.serial] : []),
      onClick: (container) =>
        container.serial ? this.selectContainer(container.serial) : undefined,
      isCopyable: true,
    }),
    new SimpleTableColumn({
      key: 'type',
      label: 'Type',
      getItems: (container) => (container.type ? [container.type] : []),
    }),
    new OnClickTableColumn({
      key: 'states',
      label: 'Status',
      getItems: (container) => (container.states ? container.states : []),
      onClick: (container) =>
        container.serial ? this.onClickToggleActive(container) : undefined,
      getNgClass: (container) => this.getStatesNgClass(container.states || []),
    }),
    new SimpleTableColumn({
      key: 'description',
      label: 'Description',
      getItems: (container) =>
        container.description ? [container.description] : [],
    }),
    new SimpleTableColumn({
      key: 'users',
      label: 'User',
      getItems: (container) =>
        container.users ? container.users.map((user) => user.user_name) : [],
    }),
    new SimpleTableColumn({
      key: 'user_realm',
      label: 'Realm',
      getItems: (container) =>
        container.user_realm ? [container.user_realm] : [],
    }),
    new SimpleTableColumn({
      key: 'realms',
      label: 'Container Realms',
      getItems: (container) => (container.realms ? [container.realms] : []),
    }),
  ];

  basicFilters: KeywordFilter[] = [
    new KeywordFilter({ key: 'container_serial', label: 'Serial' }),
    new KeywordFilter({ key: 'type', label: 'Type' }),
    new KeywordFilter({ key: 'user', label: 'User' }),
  ];
  advancedFilters: KeywordFilter[] = [
    new KeywordFilter({ key: 'token_serial', label: 'Token Serial' }),
  ];
  containerService: ContainerService;

  constructor(
    containerService: ContainerService,
    protected tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {
    this.containerService = containerService;
  }

  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    filterValue: currentFilter,
  }) =>
    this.containerService.getContainerData(
      pageIndex,
      pageSize,
      sortby_sortdir,
      currentFilter,
    );

  processDataSource: ProcessDataSource<ContainerData> = (
    response: FetchDataResponse,
  ) => [
    response.result.value.containers.length,
    new MatTableDataSource(
      ContainerData.parseList(response.result.value.containers),
    ),
  ];

  getStatesNgClass(states: string[]): string {
    if (states.length === 0) {
      return '';
    }
    const state = states[0];
    switch (state) {
      case 'active':
        return 'highlight-true-clickable';
      case 'disabled':
        return 'highlight-false-clickable';
      default:
        return '';
    }
  }
  onClickToggleActive(element: ContainerData) {
    if (typeof element.serial !== 'string' || !Array.isArray(element.states)) {
      console.error('Failed to toggle active. Missing serial or states.');
      return;
    }
    this.containerService
      .toggleActive(element.serial, element.states)
      .subscribe({
        error: (error) => {
          console.error('Failed to toggle active.', error);
          this.notificationService.openSnackBar('Failed to toggle active.');
        },
      });
  }

  selectContainer(containerSerial: string) {
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }
}
