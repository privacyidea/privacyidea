import { NgClass } from '@angular/common';
import {
  Component,
  computed,
  effect,
  Inject,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconButton } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { lastValueFrom } from 'rxjs';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  DialogService,
  DialogServiceInterface,
} from '../../../services/dialog/dialog.service';
import {
  TableUtilsService,
  TableUtilsServiceInterface,
} from '../../../services/table-utils/table-utils.service';
import {
  TokenDetails,
  TokenService,
  TokenServiceInterface,
} from '../../../services/token/token.service';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';

const columnKeysMap = [
  { key: 'select', label: '' },
  { key: 'serial', label: 'Serial' },
  { key: 'tokentype', label: 'Type' },
  { key: 'active', label: 'Active' },
  { key: 'description', label: 'Description' },
  { key: 'failcount', label: 'Fail Counter' },
  { key: 'rollout_state', label: 'Rollout State' },
  { key: 'username', label: 'User' },
  { key: 'user_realm', label: 'User Realm' },
  { key: 'realms', label: 'Token Realm' },
  { key: 'container_serial', label: 'Container' },
];

@Component({
  selector: 'app-token-table',
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
    MatIconModule,
    MatIconButton,
  ],
  templateUrl: './token-table.component.html',
  styleUrl: './token-table.component.scss',
})
export class TokenTableComponent {
  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = columnKeysMap.map((column) => column.key);
  readonly apiFilter = this.tokenService.apiFilter;
  readonly advancedApiFilter = this.tokenService.advancedApiFilter;
  tokenSelection = this.tokenService.tokenSelection;
  selectedContent = this.contentService.selectedContent;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;

  tokenResource = this.tokenService.tokenResource;

  filterValue = this.tokenService.filterValue;
  filterValueString: WritableSignal<string> = linkedSignal(() => {
    const filterMap = this.filterValue();
    return Object.entries(filterMap)
      .map(([key, value]) => `${key}: ${value}`)
      .join(' ');
  });

  pageSize = this.tokenService.pageSize;
  pageIndex = this.tokenService.pageIndex;
  sort = this.tokenService.sort;

  emptyResource = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => {
        const emptyRow: any = {};
        columnKeysMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
  });

  tokenDataSource: WritableSignal<MatTableDataSource<TokenDetails>> =
    linkedSignal({
      source: this.tokenResource.value,
      computation: (tokenResource, previous) => {
        if (tokenResource && tokenResource.result?.value) {
          return new MatTableDataSource(tokenResource.result?.value.tokens);
        }
        return previous?.value ?? new MatTableDataSource(this.emptyResource());
      },
    });

  totalLength: WritableSignal<number> = linkedSignal({
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource && tokenResource.result?.value) {
        return tokenResource.result?.value.count;
      }
      return previous?.value ?? 0;
    },
  });

  pageSizeOptions = computed(() => {
    const total = this.totalLength();
    const defaultSizeOptions = this.tokenService.defaultSizeOptions;
    if (total < defaultSizeOptions[defaultSizeOptions.length - 1]) {
      const filtered = defaultSizeOptions.filter((size) => size <= total);
      if (filtered.length < 2) {
        return defaultSizeOptions.slice(0, 2);
      }
      return [...filtered, total];
    }
    return defaultSizeOptions;
  });

  @ViewChild('filterHTMLInputElement', { static: true })
  filterInput!: HTMLInputElement;

  constructor(
    @Inject(TokenService)
    protected tokenService: TokenServiceInterface,
    @Inject(TableUtilsService)
    protected tableUtilsService: TableUtilsServiceInterface,
    @Inject(ContentService)
    protected contentService: ContentServiceInterface,
    @Inject(DialogService)
    protected dialogService: DialogServiceInterface,
  ) {
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
    return this.tokenSelection().length === this.tokenDataSource().data.length;
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.tokenSelection.set([]);
    } else {
      this.tokenSelection.set([...this.tokenDataSource().data]);
    }
  }

  toggleRow(tokenDetails: TokenDetails): void {
    const current = this.tokenSelection();
    if (current.includes(tokenDetails)) {
      this.tokenSelection.set(current.filter((r) => r !== tokenDetails));
    } else {
      this.tokenSelection.set([...current, tokenDetails]);
    }
  }

  toggleActive(tokenDetails: TokenDetails): void {
    if (!tokenDetails.revoked && !tokenDetails.locked) {
      this.tokenService
        .toggleActive(tokenDetails.serial, tokenDetails.active)
        .subscribe({
          next: () => {
            this.tokenResource.reload();
          },
        });
    }
  }

  resetFailCount(tokenDetails: TokenDetails): void {
    if (!tokenDetails.revoked && !tokenDetails.locked) {
      this.tokenService.resetFailCount(tokenDetails.serial).subscribe({
        next: () => {
          this.tokenResource.reload();
        },
      });
    }
  }

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.tokenService.eventPageSize = event.pageSize;
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    if ($event.direction === '') {
      this.sort.set({ active: 'serial', direction: 'asc' });
      return;
    }
    this.sort.set($event);
  }

  async deleteSelectedTokens() {
    if (this.tokenSelection().length === 0) {
      return;
    }
    const confirmation = await this.dialogService.confirm({
      data: {
        action: 'delete',
        title: 'Delete Tokens',
        serial_list: this.tokenSelection().map((token) => token.serial),
        type: 'token',
      },
    });
    if (!confirmation) {
      return;
    }
    // Extract serials from the selected tokens
    const tokenSerials = this.tokenSelection().map((token) => token.serial);
    try {
      await lastValueFrom(this.tokenService.deleteTokens(tokenSerials));
      this.tokenSelection.set([]);
      this.tokenResource.reload();
    } catch (error) {
      console.error('Error deleting tokens:', error);
      // Handle error appropriately, e.g., show a notification
    }
  }
}
