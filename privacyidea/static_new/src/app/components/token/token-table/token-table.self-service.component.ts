import { Component } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSortModule } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { TokenTableComponent } from './token-table.component';

@Component({
  selector: 'app-token-table-self-service',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    CopyButtonComponent,
    MatCheckboxModule,
    FormsModule,
  ],
  templateUrl: './token-table.self-service.component.html',
  styleUrl: './token-table.component.scss',
})
export class TokenTableSelfServiceComponent extends TokenTableComponent {
  readonly columnKeysMapSelfService = [
    { key: 'serial', label: 'Serial' },
    { key: 'tokentype', label: 'Type' },
    { key: 'active', label: 'Active' },
    { key: 'description', label: 'Description' },
    { key: 'failcount', label: 'Fail Counter' },
    { key: 'container_serial', label: 'Container' },
  ];
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService.map(
    (column: { key: string; label: string }) => column.key,
  );
}
