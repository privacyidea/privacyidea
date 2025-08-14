import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { KeywordFilterComponent } from '../shared/keyword-filter/keyword-filter.component';
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
} from '@angular/material/table';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { MatPaginator } from '@angular/material/paginator';
import { CopyButtonComponent } from '../shared/copy-button/copy-button.component';
import { RouterLink } from '@angular/router';
import { AuditComponent } from './audit.component';
import { MatDrawer, MatDrawerContainer, MatDrawerContent } from '@angular/material/sidenav';
import { MatIcon } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import {
  NavigationSelfServiceComponent
} from '../token/navigation-self-service/navigation-self-service.component';

@Component({
  selector: 'app-audit-self-service',
  imports: [
    MatCardModule,
    KeywordFilterComponent,
    MatCell,
    MatFormField,
    FormsModule,
    MatInput,
    MatPaginator,
    MatHeaderCellDef,
    MatHeaderCell,
    MatTable,
    MatCellDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatNoDataRow,
    MatRow,
    MatColumnDef,
    MatLabel,
    CopyButtonComponent,
    RouterLink,
    MatDrawerContainer,
    MatDrawer,
    MatDrawerContent,
    MatButtonModule,
    MatIcon,
    NavigationSelfServiceComponent
  ],
  templateUrl: './audit.self-service.component.html',
  styleUrl: './audit.component.scss',
})
export class AuditComponentSelfServiceComponent extends AuditComponent {}
