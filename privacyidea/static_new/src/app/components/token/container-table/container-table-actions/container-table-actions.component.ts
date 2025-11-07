/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { Component, inject } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { forkJoin } from "rxjs";
import { MatDialog } from "@angular/material/dialog";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { RouterLink } from "@angular/router";
import { DocumentationService } from "../../../../services/documentation/documentation.service";

@Component({
  selector: "app-container-table-actions",
  imports: [MatButtonModule, MatIcon, RouterLink],
  templateUrl: "./container-table-actions.component.html",
  styleUrl: "./container-table-actions.component.scss"
})
export class ContainerTableActionsComponent {
  private readonly dialog: MatDialog = inject(MatDialog);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly documentationService = inject(DocumentationService);
  protected readonly authService = inject(AuthService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
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
