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
import { ContainerTableComponent } from './container-table.component';

@Component({
  selector: 'app-container-table-self-service',
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
  templateUrl: './container-table.self-service.component.html',
  styleUrl: './container-table.component.scss',
})
export class ContainerTableSelfServiceComponent extends ContainerTableComponent {
  readonly columnKeysMapSelfService = [
    { key: 'serial', label: 'Serial' },
    { key: 'type', label: 'Type' },
    { key: 'states', label: 'Status' },
    { key: 'description', label: 'Description' },
  ];
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService.map(
    (column: { key: string; label: string }) => column.key,
  );
}
