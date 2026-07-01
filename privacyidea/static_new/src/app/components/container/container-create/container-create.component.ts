/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import { CommonModule, NgClass } from "@angular/common";
import {
  Component,
  OnDestroy,
  OnInit,
  ViewChild,
  WritableSignal,
  computed,
  effect,
  inject,
  linkedSignal,
  signal,
  untracked
} from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatOption } from "@angular/material/core";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import {
  ContainerCreatedDialogComponent,
  ContainerCreationDialogData
} from "@components/container/container-create/container-created-dialog/container-created-dialog.component";
import {
  ContainerRegistrationCompletedDialogComponent,
  ContainerRegistrationCompletedDialogData
} from "@components/container/container-create/container-registration-completed-dialog/container-registration-completed-dialog.component";
import {
  ContainerTokensEnrolledDialogComponent,
  ContainerTokensEnrolledDialogData
} from "@components/container/container-create/container-tokens-enrolled-dialog/container-tokens-enrolled-dialog.component";
import { ContainerRegistrationConfigComponent } from "@components/container/container-registration/container-registration-config/container-registration-config.component";
import { ContainerCreateFormComponent } from "@components/shared/container-create-form/container-create-form.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { UserAssignmentComponent } from "@components/token/user-assignment/user-assignment.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import {
  ContainerCreateData,
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerTemplate,
  ContainerType
} from "@services/container/container.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { firstValueFrom } from "rxjs";

@Component({
  selector: "app-container-create",
  imports: [
    MatButton,
    MatFormField,
    MatIcon,
    MatOption,
    MatSelect,
    MatIconButton,
    MatTooltip,
    ScrollToTopDirective,
    StickyHeaderDirective,
    NgClass,
    CommonModule,
    UserAssignmentComponent,
    ContainerCreateFormComponent
  ],
  templateUrl: "./container-create.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateComponent implements OnInit, OnDestroy {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly containerTemplateService = inject(ContainerTemplateService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router = inject(Router);
  private readonly pendingChangesService = inject(PendingChangesService);

  @ViewChild(UserAssignmentComponent) userAssignmentComponent!: UserAssignmentComponent;
  @ViewChild(ContainerRegistrationConfigComponent) registrationConfigComponent!: ContainerRegistrationConfigComponent;

  validInput = true;

  description = signal("");
  containerSerial = this.containerService.containerSerial;
  selectedUser = this.userService.selectionUsernameFilter;
  selectedUserRealm = this.userService.selectedUserRealm;
  isUserSelected = computed(() => this.userService.selectionUsernameFilter() !== "");

  templateOptions = this.containerTemplateService.templates;
  selectedTemplate: WritableSignal<ContainerTemplate> = linkedSignal({
    source: this.containerService.selectedContainerType,
    computation: (selectedContainerType, previous) => {
      if (previous?.value && selectedContainerType?.containerType === previous.value.container_type) {
        return previous.value;
      }
      return this._getEmptyTemplate();
    }
  });
  templateIsSelected = computed(() => this.selectedTemplate()?.name !== "");

  availableTokenTypes = computed(() => {
    const containerType = this.selectedTemplate()?.container_type;
    return containerType ? this.containerTemplateService.getTokenTypesForContainerType(containerType) : [];
  });

  generateQRCode: WritableSignal<boolean> = linkedSignal({
    source: this.containerService.selectedContainerType,
    computation: (containerType?: ContainerType) =>
      containerType?.containerType === "smartphone" &&
      this.authService.actionAllowed("container_register") &&
      this.authService.actionAllowed("container_create")
  });

  passphrasePrompt = signal("");
  passphraseResponse = signal("");
  userStorePassphrase = signal(false);

  registerResponse = signal<PiResponse<ContainerRegisterData> | null>(null);
  public dialogData = signal<ContainerCreationDialogData | null>(null);

  constructor() {
    this.containerSerial.set("");
    this.containerService.containerDetailsResource.set(undefined);

    effect(() => {
      this.containerService.selectedContainerType();
      untracked(() => this.resetCreateOptions());
    });

    effect(() => {
      const containerDetail = this.containerService.containerDetail();
      if (!containerDetail) return;

      if (containerDetail?.info?.registration_state === "registered") {
        const serial = containerDetail.serial;
        this.dialogService.closeAllDialogs();
        this.openRegistrationCompletedDialog(serial);
      }
    });
  }

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(
      () => this.description() !== "" || this.selectedTemplate().name !== "" || this.selectedUser() !== ""
    );
    this.pendingChangesService.registerValidChanges(() => this.validInput);
    this.pendingChangesService.registerSave(() => this._saveForPendingChanges());
  }

  private async _saveForPendingChanges(): Promise<boolean> {
    const containerType = this.containerService.selectedContainerType()?.containerType;
    if (!containerType || !this.validInput) return false;

    const createData: ContainerCreateData = {
      type: containerType,
      description: this.description(),
      user: this.userAssignmentComponent?.onlyAddToRealm()
        ? ""
        : this.userAssignmentComponent?.userFilter() || this.userService.selectedUser()?.username || ""
    };
    if (createData.user || this.userAssignmentComponent?.onlyAddToRealm()) {
      createData.realm = this.selectedUserRealm();
    }
    const template = this.selectedTemplate();
    if (template && template.template_options.tokens.length > 0) {
      createData.name = template.name;
      createData.template = template;
    }

    try {
      await firstValueFrom(this.containerService.createContainer(createData));
      return true;
    } catch {
      return false;
    }
  }

  ngOnDestroy(): void {
    this.containerService.stopPolling();
    this.pendingChangesService.clearAllRegistrations();
  }

  protected onValidInputChange(isValid: boolean) {
    this.validInput = isValid;
  }

  protected onTemplateChange(template: ContainerTemplate) {
    this.selectedTemplate.set(template);
  }

  protected clearTemplateSelection() {
    this.selectedTemplate.set(this._getEmptyTemplate());
  }

  protected compareTemplates = (t1: ContainerTemplate | null, t2: ContainerTemplate | null): boolean => {
    return t1?.name === t2?.name;
  };

  createContainer() {
    this.registerResponse.set(null);
    const containerType = this.containerService.selectedContainerType()?.containerType;
    if (!containerType) return;

    const createData: ContainerCreateData = {
      type: containerType,
      description: this.description(),
      user: this.userAssignmentComponent?.onlyAddToRealm()
        ? ""
        : this.userAssignmentComponent?.userFilter() || this.userService.selectedUser()?.username || ""
    };

    if (createData.user || this.userAssignmentComponent?.onlyAddToRealm()) {
      createData.realm = this.selectedUserRealm();
    }

    const template = this.selectedTemplate();
    if (template && template.template_options.tokens.length > 0) {
      createData.name = template.name;
      createData.template = template;
    }

    this.containerService.createContainer(createData).subscribe({
      next: (response) => {
        const containerSerial = response.result?.value?.container_serial;
        if (!containerSerial) {
          this.notificationService.error($localize`Container creation failed. No container serial returned.`);
          return;
        }
        this.pendingChangesService.clearAllRegistrations();
        if (this.generateQRCode()) {
          this.registerContainer(containerSerial);
        } else {
          const tokensRecord = response.result?.value?.tokens;
          const enrolledTokens = tokensRecord
            ? Object.entries(tokensRecord).map(([serial, detail]) => ({ ...detail, serial }))
            : [];
          if (enrolledTokens.length > 0) {
            this.openTokensEnrolledDialog({ enrolledTokens, containerSerial });
          } else {
            this.onCreationSuccess(containerSerial);
          }
        }
      }
    });
  }

  protected onCreationSuccess(serial: string) {
    this.containerService.containerSerial.set(serial);
    this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS_DETAILS + serial);
  }

  protected registerContainer(serial: string, regenerate = false) {
    this.containerService
      .registerContainer({
        container_serial: serial,
        passphrase_user: this.registrationConfigComponent?.userStorePassphrase() || false,
        passphrase_response: this.registrationConfigComponent?.passphraseResponse() || "",
        passphrase_prompt: this.registrationConfigComponent?.passphrasePrompt() || ""
      })
      .subscribe((registerResponse) => {
        this.registerResponse.set(registerResponse);
        if (regenerate) {
          this.dialogData.update((data) => (data ? { ...data, response: registerResponse } : data));
        } else {
          this.containerSerial.set(serial);
          this.openRegistrationDialog(registerResponse, serial);
        }
      });
  }

  reopenEnrollmentDialog() {
    const currentResponse = this.registerResponse();
    if (currentResponse) {
      this.openRegistrationDialog(currentResponse, this.containerService.containerSerial());
    }
  }

  protected openRegistrationDialog(response: PiResponse<ContainerRegisterData>, serial: string) {
    this.dialogData.set({
      response: response,
      containerSerial: this.containerSerial,
      registerContainer: this.registerContainer.bind(this)
    });

    const dialogRef = this.dialogService.openDialog({
      component: ContainerCreatedDialogComponent,
      data: this.dialogData
    });

    this.containerService.startPolling(serial);
    dialogRef.afterClosed().subscribe(() => this.containerService.stopPolling());
  }

  protected openTokensEnrolledDialog(data: ContainerTokensEnrolledDialogData) {
    this.dialogService.openDialog({
      component: ContainerTokensEnrolledDialogComponent,
      data,
      configOverride: { minWidth: "750px", disableClose: true }
    });
  }

  protected openRegistrationCompletedDialog(serial: string) {
    this.dialogService.openDialog({
      component: ContainerRegistrationCompletedDialogComponent,
      data: { containerSerial: serial } as ContainerRegistrationCompletedDialogData
    });
  }

  protected resetCreateOptions = () => {
    this.registerResponse.set(null);
    this.passphrasePrompt.set("");
    this.passphraseResponse.set("");
    this.userStorePassphrase.set(false);
    this.description.set("");
    this.clearTemplateSelection();
  };

  private _getEmptyTemplate(): ContainerTemplate {
    return {
      container_type: this.containerService.selectedContainerType()?.containerType ?? "",
      default: false,
      name: "",
      template_options: { tokens: [] }
    };
  }
}
