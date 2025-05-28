import {
  Component,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  MatPaginator,
  MatPaginatorModule,
  PageEvent,
} from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { NgClass } from '@angular/common';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { TokenService } from '../../../services/token/token.service';
import {
  Challenge,
  ChallengesService,
} from '../../../services/token/challenges/challenges.service';
import { ContentService } from '../../../services/content/content.service';

export const columnKeysMap = [
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
  columnsKeyMap = columnKeysMap;
  displayedColumns = columnKeysMap.map((c) => c.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.challengesService.apiFilter;
  advancedApiFilter = this.challengesService.advancedApiFilter;
  selectedContent = this.contentService.selectedContent;
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

  constructor(
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    private challengesService: ChallengesService,
    protected contentService: ContentService,
  ) {}

  onFilterChange(newFilter: string) {
    this.filterValue.set(newFilter);
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
