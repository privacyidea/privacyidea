import { NgClass } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatPaginator } from '@angular/material/paginator';
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
import { RouterLink } from '@angular/router';
import { CopyButtonComponent } from '../shared/copy-button/copy-button.component';
import { ScrollToTopDirective } from '../shared/directives/app-scroll-to-top.directive';
import { KeywordFilterComponent } from '../shared/keyword-filter/keyword-filter.component';
import { AuditComponent } from './audit.component';

@Component({
  selector: "app-audit-self-service",
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
    ScrollToTopDirective,
  ],
  templateUrl: "./audit.self-service.component.html",
  styleUrl: "./audit.component.scss"
})
export class AuditComponentSelfServiceComponent extends AuditComponent {
}
