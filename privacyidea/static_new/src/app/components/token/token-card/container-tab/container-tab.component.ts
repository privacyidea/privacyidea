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
import { NgClass } from "@angular/common";
import { Component, computed, inject, signal, ViewChild, WritableSignal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatList, MatListItem } from "@angular/material/list";
import { forkJoin } from "rxjs";
import { tabToggleState } from "../../../../../styles/animations/animations";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface, ContainerUnregisterData
} from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "../../../../route_paths";
import { AuthService } from "../../../../services/auth/auth.service";
import { PiResponse } from "../../../../app.component";
import { ContainerRegistrationConfigComponent } from "../../container-registration/container-registration-config/container-registration-config.component";
import { ContainerRegistrationInitDialogComponent } from "../../container-registration/container-registration-init-dialog/container-registration-init-dialog.component";
import { ContainerRegistrationFinalizeDialogComponent } from "../../container-registration/container-registration-finalize-dialog/container-registration-finalize-dialog.component";
import { NotificationService } from "../../../../services/notification/notification.service";

export type ContainerRegisterFinalizeDate = {
  response: PiResponse<ContainerRegisterData>,
  registerContainer: (userStorePW?: boolean, passphrasePrompt?: string,
                      passphraseResponse?: string, rollover?: boolean, regenerate?: boolean) => void,
  rollover: boolean
};

@Component({
  selector: "app-container-tab",
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, NgClass, MatDivider, RouterLink],
  templateUrl: "./container-tab.component.html",
  styleUrl: "./container-tab.component.scss",
  animations: [tabToggleState]
})
export class ContainerTabComponent {
  private readonly dialog: MatDialog = inject(MatDialog);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly authService = inject(AuthService);
  protected readonly notificationService = inject(NotificationService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private router = inject(Router);
  containerSelection = this.containerService.containerSelection;
  containerSerial = this.containerService.containerSerial;
  containerType = computed(() => {
    const containerDetail = this.containerService.containerDetailResource.value();
    return containerDetail?.result?.value?.containers[0]?.type ?? [];
  });
  registrationState = computed(() => {
    const containerDetail = this.containerService.containerDetailResource.value();
    return containerDetail?.result?.value?.containers[0]?.info?.registration_state ?? "";
  });

  selectedContainer = this.containerService.selectedContainer;
  containerIsSelected = computed(() => this.containerSerial() !== "");
  states = computed(() => {
    const containerDetail = this.containerService.containerDetailResource.value();
    return containerDetail?.result?.value?.containers[0]?.states ?? [];
  });
  version!: string;

  dialogData: WritableSignal<ContainerRegisterFinalizeDate | null> = signal(null);

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  onClickContainerOverview() {
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
  }

  enrollTokenInContainer() {
    this.contentService.isProgrammaticTabChange.set(true);
    this.selectedContainer.set(this.containerSerial());
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_ENROLLMENT);
  }

  toggleActive(): void {
    this.containerService.toggleActive(this.containerSerial(), this.states()).subscribe(() => {
      this.containerService.containerDetailResource.reload();
    });
  }

  deleteContainer() {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [this.containerSerial()],
          title: "Delete Container",
          type: "container",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          this.containerService.deleteContainer(this.containerSerial()).subscribe(() => {
            const prev = this.contentService.previousUrl();

            if (prev.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
              this.contentService.isProgrammaticTabChange.set(true);
              this.router.navigateByUrl(prev);
            } else {
              this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
            }
          });
        }
      });
  }

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

  lostContainer() {
    // TODO: Missing API endpoint
  }

  damagedContainer() {
    // TODO: Missing API endpoint
  }

  @ViewChild(ContainerRegistrationConfigComponent)
  registrationConfigComponent!: ContainerRegistrationConfigComponent;
  passphrasePrompt: string = "";
  passphraseResponse: string = "";
  userStorePW: boolean = false;

  openRegisterInitDialog(rollover: boolean) {
    const container = this.containerService.containerDetailResource.value()?.result?.value?.containers?.[0];
    this.dialog.open(ContainerRegistrationInitDialogComponent, {
      data: {
        registerContainer: this.registerContainer.bind(this),
        rollover: rollover,
        containerHasOwner: (container?.users?.length ?? 0) > 0 || false
      }
    });
  }

  registerContainer(userStorePW?: boolean, passphrasePrompt?: string, passphraseResponse?: string, rollover?: boolean,
                    regenerate: boolean = false) {
    this.userStorePW = userStorePW ?? this.userStorePW;
    this.passphrasePrompt = passphrasePrompt ?? this.passphrasePrompt;
    this.passphraseResponse = passphraseResponse ?? this.passphraseResponse;
    if (!regenerate) {
      this.dialog.closeAll();
    }
    this.containerService
      .registerContainer({
        container_serial: this.containerSerial(),
        passphrase_user: this.userStorePW,
        passphrase_response: this.passphraseResponse,
        passphrase_prompt: this.passphrasePrompt,
        rollover: rollover ?? false
      })
      .subscribe((registerResponse) => {
        if (regenerate) {
          this.dialogData.update(data => data ? { ...data, response: registerResponse } : data);
        } else {
          this.openRegisterFinalizeDialog(registerResponse, rollover);
          this.pollContainerRolloutState(5000);
        }
      });
  }

  unregisterContainer() {
    this.containerService
      .unregister(this.containerSerial())
      .subscribe((unregisterResponse: PiResponse<ContainerUnregisterData>) => {
        if (unregisterResponse?.result?.value?.success) {
          this.notificationService.openSnackBar("Container unregistered successfully.");
        } else {
          this.notificationService.openSnackBar("Failed to unregister container.");
        }
        this.containerService.containerDetailResource.reload();
      });
  }

  private openRegisterFinalizeDialog(response: PiResponse<ContainerRegisterData>, rollover?: boolean) {
    this.dialogData.set({
      response: response,
      registerContainer: this.registerContainer.bind(this),
      rollover: rollover || false
    });
    const dialogRef = this.dialog.open(ContainerRegistrationFinalizeDialogComponent, {
      data: this.dialogData
    });
    dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }

  private pollContainerRolloutState(startTime: number) {
    return this.containerService.pollContainerRolloutState(this.containerSerial(), startTime).subscribe({
      next: (response) => {
        if (response?.result?.value?.containers[0].info.registration_state === "registered") {
          this.dialog.closeAll();
          this.containerService.containerDetailResource.reload();
        }
      }
    });
  }
}
