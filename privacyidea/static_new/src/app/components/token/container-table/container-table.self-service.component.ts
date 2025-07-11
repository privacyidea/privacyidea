import { Component, inject } from '@angular/core';
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
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { ConfirmationDialogComponent } from '../../shared/confirmation-dialog/confirmation-dialog.component';
import { MatDialog } from '@angular/material/dialog';

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
    MatIcon,
    MatIconButton,
  ],
  templateUrl: './container-table.self-service.component.html',
  styleUrl: './container-table.component.scss',
})
export class ContainerTableSelfServiceComponent extends ContainerTableComponent {
  private dialog = inject(MatDialog);
  readonly columnKeysMapSelfService = [
    { key: 'serial', label: 'Serial' },
    { key: 'type', label: 'Type' },
    { key: 'states', label: 'Status' },
    { key: 'description', label: 'Description' },
    { key: 'delete', label: 'Delete' },
  ];
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService.map(
    (column: { key: string; label: string }) => column.key,
  );

  deleteContainer(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [serial],
          title: 'Delete Container',
          type: 'container',
          action: 'delete',
          numberOfTokens: 1,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.deleteContainer(serial).subscribe({
              next: () => {
                this.containerService.containerResource.reload();
              },
            });
          }
        },
      });
  }
}
