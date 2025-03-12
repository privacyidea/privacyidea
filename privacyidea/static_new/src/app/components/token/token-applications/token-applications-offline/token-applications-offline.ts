import {
  Component,
  effect,
  ElementRef,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MachineService } from '../../../../services/machine/machine.service';
import { TokenSelectedContent } from '../../token.component';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';

export const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'count', label: 'Count' },
  { key: 'rounds', label: 'Rounds' },
];

@Component({
  selector: 'app-token-applications-offline',
  standalone: true,
  imports: [
    MatTabsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    KeywordFilterComponent,
    MatFormField,
    MatIcon,
    MatInput,
    MatLabel,
    NgClass,
    CdkCopyToClipboard,
  ],
  templateUrl: './token-applications-offline.html',
  styleUrls: ['./token-applications-offline.scss'],
})
export class TokenApplicationsOffline {
  static columnsKeyMap = columnsKeyMap;
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true })
  selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input({ required: true }) length!: WritableSignal<number>;
  @Input({ required: true }) pageSize!: WritableSignal<number>;
  @Input({ required: true }) pageIndex!: WritableSignal<number>;
  @Input({ required: true }) filterValue!: WritableSignal<string>;
  @Input({ required: true }) sortby_sortdir!: WritableSignal<Sort>;
  @Input({ required: true }) toggleKeywordInFilter!: (
    filterKeyword: string,
    inputElement: HTMLInputElement,
    application: string,
  ) => void;
  @Input({ required: true }) fetchApplicationOfflineData!: () => void;
  @Input({ required: true }) tokenSelected!: (serial: string) => void;
  @Input({ required: true }) dataSource!: WritableSignal<
    MatTableDataSource<any>
  >;
  keywordClick = signal<string>('');
  displayedColumns: string[] = columnsKeyMap.map((c) => c.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.offlineApiFilter;
  advancedApiFilter = this.machineService.offlineAdvancedApiFilter;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('input') inputElement!: ElementRef<HTMLInputElement>;
  columnsKeyMap = columnsKeyMap;

  constructor(
    protected tableUtilsService: TableUtilsService,
    private machineService: MachineService,
  ) {
    effect(() => {
      const clickedKeyword = this.keywordClick();
      if (clickedKeyword) {
        this.toggleKeywordInFilter(
          clickedKeyword,
          this.inputElement.nativeElement,
          'offline',
        );
        this.keywordClick.set('');
      }
    });
  }
}
