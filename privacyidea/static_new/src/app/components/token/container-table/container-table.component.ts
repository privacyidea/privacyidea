import {
  animate,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';
import { NgClass } from '@angular/common';
import {
  Component,
  effect,
  inject,
  Input,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  ContainerDetailData,
  ContainerService,
  ContainerServiceInterface,
} from '../../../services/container/container.service';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  TableUtilsService,
  TableUtilsServiceInterface,
} from '../../../services/table-utils/table-utils.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../services/token/token.service';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { TokenSelectedContentKey } from '../token.component';

const columnsKeyMap = [
  { key: 'select', label: '' },
  { key: 'serial', label: 'Serial' },
  { key: 'type', label: 'Type' },
  { key: 'states', label: 'Status' },
  { key: 'description', label: 'Description' },
  { key: 'user_name', label: 'User' },
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
    MatCheckboxModule,
    FormsModule,
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.scss',
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0' })),
      state('expanded', style({ height: '*' })),
      transition(
        'expanded <=> collapsed',
        animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)'),
      ),
    ]),
  ],
})
export class ContainerTableComponent {
  protected readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface =
    inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);

  readonly columnsKeyMap = columnsKeyMap;
  readonly columnKeys: string[] = columnsKeyMap.map((column) => column.key);
  readonly apiFilter = this.containerService.apiFilter;
  readonly advancedApiFilter = this.containerService.advancedApiFilter;
  containerSelection = this.containerService.containerSelection;
  filterValue = this.containerService.filterValue;
  filterValueString: WritableSignal<string> = linkedSignal(() =>
    Object.entries(this.filterValue())
      .map(([key, value]) => `${key}: ${value}`)
      .join(' '),
  );
  pageSize = this.containerService.pageSize;
  pageIndex = this.containerService.pageIndex;
  sort = this.containerService.sort;
  containerResource = this.containerService.containerResource;

  emptyResource: WritableSignal<ContainerDetailData[]> = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => {
        return {
          serial: '',
          type: '',
          states: [],
          description: '',
          users: [],
          user_realm: '',
          realms: [],
          tokens: [],
          info: {},
          internal_info_keys: [],
          last_authentication: null,
          last_synchronization: null,
        } as ContainerDetailData;
      }),
  });

  containerDataSource: WritableSignal<MatTableDataSource<ContainerDetailData>> =
    linkedSignal({
      source: this.containerResource.value,
      computation: (containerResource, previous) => {
        if (containerResource) {
          const processedData =
            containerResource.result?.value?.containers.map((item) => ({
              ...item,
              user_name:
                item.users && item.users.length > 0
                  ? item.users[0].user_name
                  : '',
              user_realm:
                item.users && item.users.length > 0
                  ? item.users[0].user_realm
                  : '',
            })) ?? [];
          return new MatTableDataSource<ContainerDetailData>(processedData);
        }
        return previous?.value ?? new MatTableDataSource(this.emptyResource());
      },
    });

  total: WritableSignal<number> = linkedSignal({
    source: this.containerResource.value,
    computation: (containerResource, previous) => {
      if (containerResource) {
        return containerResource.result?.value?.count ?? 0;
      }
      return previous?.value ?? 0;
    },
  });

  pageSizeOptions = linkedSignal({
    source: this.total,
    computation: (total) =>
      [5, 10, 15].includes(total) || total > 50
        ? [5, 10, 15]
        : [5, 10, 15, total],
  });

  @ViewChild('filterHTMLInputElement', { static: true })
  filterInput!: HTMLInputElement;
  @Input() selectedContent!: WritableSignal<TokenSelectedContentKey>;
  expandedElement: ContainerDetailData | null = null;

  constructor() {
    effect(() => {
      const filterValueString = this.filterValueString();
      if (this.filterInput) {
        this.filterInput.value = filterValueString;
      }
      const recordsFromText =
        this.tableUtilsService.recordsFromText(filterValueString);
      if (
        JSON.stringify(this.filterValue()) !== JSON.stringify(recordsFromText)
      ) {
        this.filterValue.set(recordsFromText);
      }
      this.pageIndex.set(0);
    });
  }

  isAllSelected() {
    return (
      this.containerSelection().length ===
      this.containerDataSource().data.length
    );
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.containerSelection.set([]);
    } else {
      this.containerSelection.set([...this.containerDataSource().data]);
    }
  }

  toggleRow(row: ContainerDetailData): void {
    const current = this.containerSelection();
    if (current.includes(row)) {
      this.containerSelection.set(current.filter((r) => r !== row));
    } else {
      this.containerSelection.set([...current, row]);
    }
  }

  handleStateClick(element: ContainerDetailData) {
    this.containerService
      .toggleActive(element.serial, element.states)
      .subscribe({
        next: () => {
          this.containerResource.reload();
        },
        error: (error) => {
          console.error('Failed to toggle active.', error);
        },
      });
  }

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.containerService.eventPageSize = event.pageSize;
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    this.sort.set($event);
  }
}
