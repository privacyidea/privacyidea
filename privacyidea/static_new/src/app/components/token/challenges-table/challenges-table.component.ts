import { NgClass } from '@angular/common';
import {
  Component,
  inject,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import {
  MatPaginator,
  MatPaginatorModule,
  PageEvent,
} from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  TableUtilsService,
  TableUtilsServiceInterface,
} from '../../../services/table-utils/table-utils.service';
import {
  Challenge,
  ChallengesService,
  ChallengesServiceInterface,
} from '../../../services/token/challenges/challenges.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../services/token/token.service';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';

const columnKeysMap = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'serial', label: 'Serial' },
  { key: 'transaction_id', label: 'Transaction ID' },
  { key: 'expiration', label: 'Expiration' },
  { key: 'otp_received', label: 'Received' },
];

@Component({
  selector: 'app-challenges-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    KeywordFilterComponent,
    NgClass,
    CopyButtonComponent,
  ],
  templateUrl: './challenges-table.component.html',
  styleUrls: ['./challenges-table.component.scss'],
})
export class ChallengesTableComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface =
    inject(TableUtilsService);
  private readonly challengesService: ChallengesServiceInterface =
    inject(ChallengesService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);

  columnsKeyMap = columnKeysMap;
  displayedColumns = columnKeysMap.map((c) => c.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.challengesService.apiFilter;
  advancedApiFilter = this.challengesService.advancedApiFilter;
  tokenSerial = this.tokenService.tokenSerial;
  pageSize = this.challengesService.pageSize;
  pageIndex = this.challengesService.pageIndex;
  filterValue = this.challengesService.filterValue;
  sortby_sortdir = this.challengesService.sort;
  length = linkedSignal({
    source: this.challengesService.challengesResource.value,
    computation: (res, prev) => {
      if (res) {
        return res.result?.value?.count;
      }
      return prev?.value ?? 0;
    },
  });
  challengesDataSource: WritableSignal<MatTableDataSource<Challenge>> =
    linkedSignal({
      source: this.challengesService.challengesResource.value,
      computation: (challengesResource, previous) => {
        if (challengesResource) {
          return new MatTableDataSource(
            challengesResource.result?.value?.challenges,
          );
        }
        return previous?.value ?? new MatTableDataSource<Challenge>([]);
      },
    });

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('filterInput', { static: true }) filterInput!: HTMLInputElement;

  onFilterChange(newFilter: string) {
    const recordsFromText = this.tableUtilsService.recordsFromText(newFilter);
    this.filterValue.set(recordsFromText);
    this.pageIndex.set(0);
  }

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    this.sortby_sortdir.set($event);
  }
}
