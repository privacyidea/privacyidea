import { NgClass } from "@angular/common";
import { Component, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatSortModule } from "@angular/material/sort";
import { MatTableModule } from "@angular/material/table";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { ScrollAdjusterDirective } from "../../shared/directives/scroll-adjuster.directive";
import { TokenTableComponent } from "./token-table.component";

@Component({
  selector: "app-token-table-self-service",
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
    ScrollAdjusterDirective
  ],
  templateUrl: "./token-table.self-service.component.html",
  styleUrl: "./token-table.component.scss"
})
export class TokenTableSelfServiceComponent extends TokenTableComponent {
  readonly columnKeysMapSelfService = [
    { key: "serial", label: "Serial" },
    { key: "tokentype", label: "Type" },
    { key: "description", label: "Description" },
    { key: "container_serial", label: "Container" },
    { key: "active", label: "Active" },
    { key: "failcount", label: "Fail Counter" },
    { key: "revoke", label: "Revoke" },
    { key: "delete", label: "Delete" }
  ];
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService.map(
    (column: { key: string; label: string }) => column.key
  );
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private dialog = inject(MatDialog);

  ngOnInit(): void {
    this.pageSize.set(5);
  }

  revokeToken(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [serial],
          title: "Revoke Token",
          type: "token",
          action: "revoke",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          this.tokenService.revokeToken(serial).subscribe({
            next: () => {
              if (result) {
                this.tokenService.tokenResource.reload();
              }
            }
          });
        }
      });
  }

  deleteToken(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [serial],
          title: "Delete Token",
          type: "token",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          this.tokenService.deleteToken(serial).subscribe({
            next: () => {
              if (result) {
                this.tokenService.tokenResource.reload();
              }
            }
          });
        }
      });
  }
}
