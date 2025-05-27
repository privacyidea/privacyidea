import {
  Component,
  Input,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSortModule, Sort } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import {
  ContainerDetailToken,
  ContainerService,
} from '../../../services/container/container.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../services/token/token.service';
import { TokenSelectedContent } from '../token.component';
import { ContentService } from '../../../services/content/content.service';
import {
  animate,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';

const columnsKeyMap = [
  { key: 'select', label: '' },
  { key: 'serial', label: 'Serial' },
  { key: 'type', label: 'Type' },
  { key: 'states', label: 'Status' },
  { key: 'description', label: 'Description' },
  { key: 'users', label: 'User' },
  { key: 'user_realm', label: 'Realm' },
  { key: 'realms', label: 'Container Realms' },
];

interface ContainerRow {
  users: string;
  user_realm: string;
  type: string;
  tokens: Array<ContainerDetailToken>;
  states: string[];
  description: string;
  select: string;
  serial: string;
  realms: string[];
}

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
  readonly columnsKeyMap = columnsKeyMap;
  readonly columnKeys: string[] = columnsKeyMap.map((column) => column.key);
  readonly apiFilter = this.containerService.apiFilter;
  readonly advancedApiFilter = this.containerService.advancedApiFilter;
  containerSelection = this.containerService.containerSelection;
  filterValue = this.containerService.filterValue;
  pageSize = this.containerService.pageSize;
  pageIndex = this.containerService.pageIndex;
  sort = this.containerService.sort;
  containerResource = this.containerService.containerResource;

  emptyResource = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
  });

  containerDataSource: WritableSignal<MatTableDataSource<ContainerRow>> =
    linkedSignal({
      source: this.containerResource.value,
      computation: (containerResource, previous) => {
        if (containerResource) {
          const processedData =
            containerResource?.result.value?.containers.map((item) => ({
              ...item,
              users:
                item.users && item.users.length > 0
                  ? item.users[0]['user_name']
                  : '',
              user_realm:
                item.users && item.users.length > 0
                  ? item.users[0]['user_realm']
                  : '',
            })) ?? [];
          return new MatTableDataSource(processedData);
        }
        return previous?.value ?? new MatTableDataSource(this.emptyResource());
      },
    });

  total: WritableSignal<number> = linkedSignal({
    source: this.containerResource.value,
    computation: (containerResource, previous) => {
      if (containerResource) {
        return containerResource.result.value?.count ?? 0;
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
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  expandedElement: ContainerRow | null = null;

  constructor(
    protected containerService: ContainerService,
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    protected contentService: ContentService,
  ) {}

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

  toggleRow(row: any): void {
    const current = this.containerSelection();
    if (current.includes(row)) {
      this.containerSelection.set(current.filter((r) => r !== row));
    } else {
      this.containerSelection.set([...current, row]);
    }
  }

  handleStateClick(element: any) {
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
