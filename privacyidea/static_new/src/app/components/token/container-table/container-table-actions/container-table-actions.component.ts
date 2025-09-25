import { Component, computed, inject } from "@angular/core";
import { NgClass } from "@angular/common";
import { MatIcon } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { forkJoin } from "rxjs";
import { MatDialog } from "@angular/material/dialog";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";
import { AuthService } from "../../../../services/auth/auth.service";

@Component({
  selector: "app-container-table-actions",
  imports: [
    NgClass,
    MatButtonModule,
    MatIcon
  ],
  templateUrl: "./container-table-actions.component.html",
  styleUrl: "./container-table-actions.component.scss"
})
export class ContainerTableActionsComponent {
  private readonly dialog: MatDialog = inject(MatDialog);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly authService = inject(AuthService);
  containerSelection = this.containerService.containerSelection;
  containerSerial = this.containerService.containerSerial;
  selectedContainer = this.containerService.selectedContainer;

  deleteSelectedContainer(): void {
    const selectedContainers = this.containerSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: selectedContainers.map((container) => container.serial),
          title: "Delete All Containers",
          type: "container",
          action: "delete",
          numberOfContainers: selectedContainers.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            forkJoin(
              selectedContainers.map((container) => this.containerService.deleteContainer(container.serial))
            ).subscribe({
              next: () => {
                this.containerSelection.set([]);
                this.containerService.containerResource.reload();
              },
              error: (err) => {
                console.error("Error deleting containers:", err);
              }
            });
          }
        }
      });
  }
}
