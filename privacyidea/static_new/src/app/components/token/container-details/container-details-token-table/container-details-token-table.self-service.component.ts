import { NgClass } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortHeader, MatSortModule } from '@angular/material/sort';
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableModule,
} from '@angular/material/table';
import { MatTooltip } from '@angular/material/tooltip';
import { AuthService } from '../../../../services/auth/auth.service';
import { ContainerService } from '../../../../services/container/container.service';
import { ContentService } from '../../../../services/content/content.service';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { TokenService } from '../../../../services/token/token.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { ContainerDetailsTokenTableComponent } from './container-details-token-table.component';

@Component({
  selector: 'app-container-details-token-table-self-service',
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatInput,
    MatLabel,
    MatPaginator,
    MatRow,
    MatSort,
    MatSortHeader,
    MatTable,
    NgClass,
    MatTableModule,
    MatSortModule,
    MatIcon,
    MatIconButton,
    MatButton,
    CopyButtonComponent,
    ReactiveFormsModule,
    FormsModule,
    MatTooltip,
  ],
  templateUrl: './container-details-token-table.self-service.component.html',
  styleUrl: './container-details-token-table.component.scss',
})
export class ContainerDetailsTokenTableSelfServiceComponent extends ContainerDetailsTokenTableComponent {
  constructor(
    protected override containerService: ContainerService,
    protected override tokenService: TokenService,
    protected override tableUtilsService: TableUtilsService,
    protected override overflowService: OverflowService,
    protected override dialog: MatDialog,
    protected override contentService: ContentService,
    protected override authService: AuthService,
  ) {
    console.log('ContainerDetailsTokenTableSelfServiceComponent initialized');
    super(
      containerService,
      tokenService,
      tableUtilsService,
      overflowService,
      dialog,
      contentService,
      authService,
    );
  }
}
