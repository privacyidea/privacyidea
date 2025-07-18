import { NgClass } from '@angular/common';
import { Component, Inject } from '@angular/core';
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
import {
  AuthService,
  AuthServiceInterface,
} from '../../../../services/auth/auth.service';
import {
  ContainerService,
  ContainerServiceInterface,
} from '../../../../services/container/container.service';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../../services/content/content.service';
import {
  OverflowService,
  OverflowServiceInterface,
} from '../../../../services/overflow/overflow.service';
import {
  TableUtilsService,
  TableUtilsServiceInterface,
} from '../../../../services/table-utils/table-utils.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';
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
    protected override dialog: MatDialog,
    @Inject(ContainerService)
    protected override containerService: ContainerServiceInterface,
    @Inject(TokenService)
    protected override tokenService: TokenServiceInterface,
    @Inject(TableUtilsService)
    protected override tableUtilsService: TableUtilsServiceInterface,
    @Inject(OverflowService)
    protected override overflowService: OverflowServiceInterface,
    @Inject(ContentService)
    protected override contentService: ContentServiceInterface,
    @Inject(AuthService)
    protected override authService: AuthServiceInterface,
  ) {
    super(
      dialog,
      containerService,
      tokenService,
      tableUtilsService,
      overflowService,
      contentService,
      authService,
    );
  }
}
