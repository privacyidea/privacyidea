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
import { TokenTableComponent } from './token-table.component';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { ConfirmationDialogComponent } from '../../shared/confirmation-dialog/confirmation-dialog.component';
import { MatDialog } from '@angular/material/dialog';

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
    MatIconButton,
    MatIcon,
  ],
  templateUrl: './token-table.self-service.component.html',
  styleUrl: './token-table.component.scss',
})
export class TokenTableSelfServiceComponent extends TokenTableComponent {
  private dialog = inject(MatDialog);
  readonly columnKeysMapSelfService = [
    { key: 'serial', label: 'Serial' },
    { key: 'tokentype', label: 'Type' },
    { key: 'description', label: 'Description' },
    { key: 'container_serial', label: 'Container' },
    { key: 'active', label: 'Active' },
    { key: 'failcount', label: 'Fail Counter' },
    { key: 'revoke', label: 'Revoke' },
    { key: 'delete', label: 'Delete' },
  ];
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService.map(
    (column: { key: string; label: string }) => column.key,
  );

  ngOnInit(): void {
    this.pageSize.set(5);
  }

  revokeToken(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [serial],
          title: 'Revoke Token',
          type: 'token',
          action: 'revoke',
          numberOfTokens: 1,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          this.tokenService.revokeToken(serial).subscribe({
            next: () => {
              if (result) {
                this.tokenService.tokenResource.reload();
              }
            },
          });
        },
      });
  }

  deleteToken(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [serial],
          title: 'Delete Token',
          type: 'token',
          action: 'delete',
          numberOfTokens: 1,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          this.tokenService.deleteToken(serial).subscribe({
            next: () => {
              if (result) {
                this.tokenService.tokenResource.reload();
              }
            },
          });
        },
      });
  }
}
