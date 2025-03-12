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
import { TokenSelectedContent } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import {
  MatCell,
  MatCellDef,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { MatFormField, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { MatIcon } from '@angular/material/icon';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';

export const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'serviceid', label: 'Service ID' },
  { key: 'ssh_user', label: 'SSH User' },
];

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [
    MatTabsModule,
    KeywordFilterComponent,
    MatCell,
    MatCellDef,
    MatFormField,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    MatIcon,
    CdkCopyToClipboard,
  ],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
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
  @Input({ required: true }) dataSource!: WritableSignal<
    MatTableDataSource<any>
  >;
  @Input({ required: true }) fetchApplicationSshData!: () => void;
  @Input({ required: true }) tokenSelected!: (serial: string) => void;
  keywordClick = signal<string>('');
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.sshApiFilter;
  advancedApiFilter = this.machineService.sshAdvancedApiFilter;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('input') inputElement!: ElementRef<HTMLInputElement>;
  columnsKeyMap = columnsKeyMap;

  constructor(
    private machineService: MachineService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      const clickedKeyword = this.keywordClick();
      if (clickedKeyword) {
        this.toggleKeywordInFilter(
          clickedKeyword,
          this.inputElement.nativeElement,
          'ssh',
        );
        this.keywordClick.set('');
      }
    });
  }

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }
}
