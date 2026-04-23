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

import { NgClass, CommonModule } from "@angular/common";
import {
  Component,
  inject,
  Renderer2,
  signal,
  computed,
  WritableSignal,
  linkedSignal,
  ViewChild,
  ElementRef,
  effect,
  untracked,
  Signal
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelTitle,
  MatExpansionPanelHeader
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel, MatSuffix } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { PiResponse } from "src/app/app.component";
import { TokenEnrollmentPayload } from "src/app/mappers/token-api-payload/_token-api-payload.mapper";
import { ROUTE_PATHS } from "src/app/route_paths";
import { AuthServiceInterface, AuthService } from "src/app/services/auth/auth.service";
import { ContainerTemplateService } from "src/app/services/container-template/container-template.service";
import {
  ContainerServiceInterface,
  ContainerService,
  ContainerTemplate,
  ContainerType,
  ContainerRegisterData,
  ContainerCreateData
} from "src/app/services/container/container.service";
import { ContentServiceInterface, ContentService } from "src/app/services/content/content.service";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";
import { NotificationServiceInterface, NotificationService } from "src/app/services/notification/notification.service";
import { RealmServiceInterface, RealmService } from "src/app/services/realm/realm.service";
import { TokenServiceInterface, TokenService } from "src/app/services/token/token.service";
import { UserServiceInterface, UserService } from "src/app/services/user/user.service";
import { VersioningServiceInterface, VersioningService } from "src/app/services/version/version.service";
import { ClearButtonComponent } from "../../shared/clear-button/clear-button.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ContainerRegistrationConfigComponent } from "../container-registration/container-registration-config/container-registration-config.component";
import { UserAssignmentComponent } from "../user-assignment/user-assignment.component";
import {
  ContainerCreationDialogData,
  ContainerCreatedDialogComponent
} from "./container-created-dialog/container-created-dialog.component";
import { ContainerCreatedDialogWizardComponent } from "./container-created-dialog/container-created-dialog.wizard.component";
import {
  ContainerRegistrationCompletedDialogComponent,
  ContainerRegistrationCompletedDialogData
} from "./container-registration-completed-dialog/container-registration-completed-dialog.component";
import { ContainerRegistrationCompletedDialogWizardComponent } from "./container-registration-completed-dialog/container-registration-completed-dialog.wizard.component";
import { ContainerTemplateEditBodyComponent } from "../container-templates/container-template-edit/container-template-edit-body/container-template-edit-body.component";

@Component({
  selector: "app-container-create",
  imports: [
    MatButton,
    MatFormField,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    MatTooltip,
    ScrollToTopDirective,
    NgClass,
    CommonModule,
    ContainerRegistrationConfigComponent,
    UserAssignmentComponent,
    MatSuffix,
    ClearButtonComponent,
    ContainerTemplateEditBodyComponent
  ],
  templateUrl: "./container-create.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateComponent {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly renderer: Renderer2 = inject(Renderer2);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router = inject(Router);
  private observer!: IntersectionObserver;
  containerSerial = this.containerService.containerSerial;
  description = signal("");
  selectedTemplate = signal<ContainerTemplate | null>(null);
  selectedTemplateName = computed<string>(() => this.selectedTemplate()?.name ?? "");
  templateOptions = this.containerTemplateService.templates;
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
  availableTokenTypes = computed(() => {
    const containerType = this.selectedTemplate()?.container_type;
    if (!containerType) {
      return [];
    }
    return this.containerTemplateService.getTokenTypesForContainerType(containerType);
  });

  registerResponse = signal<PiResponse<ContainerRegisterData> | null>(null);
  pollResponse = signal<any>(null);
  userSelected = computed(() => this.userService.selectionUsernameFilter() !== "");
  public dialogData = signal<ContainerCreationDialogData | null>(null);

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild(UserAssignmentComponent)
  userAssignmentComponent!: UserAssignmentComponent;
  @ViewChild(ContainerRegistrationConfigComponent)
  registrationConfigComponent!: ContainerRegistrationConfigComponent;
  validInput = true;
  protected resetCreateOptions = () => {
    this.registerResponse.set(null);
    this.passphrasePrompt.set("");
    this.passphraseResponse.set("");
    this.userStorePassphrase.set(false);
    this.description.set("");
    this.selectedTemplate.set(null);
  };

  constructor() {
    // Clear container serial and detail resource when entering create page
    this.containerService.containerSerial.set("");
    this.containerService.containerDetailResource.set(undefined);

    effect(() => {
      this.containerService.selectedContainerType();
      untracked(() => {
        this.resetCreateOptions();
      });
    });

    effect(() => {
      const serial = this.containerService.containerSerial();

      if (!serial || !this.containerService.containerDetailResource.hasValue()) return;
      const containerDetailResource = this.containerService.containerDetailResource.value();
      if (!containerDetailResource?.result?.value) return;
      const container = containerDetailResource.result.value.containers[0];
      const registrationState = container?.info?.registration_state;
      if (registrationState !== "registered") return;

      this.dialogService.closeAllDialogs();
      this.containerService.stopPolling();

      this.openRegistrationCompletedDialog(serial);
    });
  }

  protected openRegistrationCompletedDialog(serial: string) {
    this.dialogService.openDialog({
      component: ContainerRegistrationCompletedDialogComponent,
      data: { containerSerial: serial } as ContainerRegistrationCompletedDialogData
    });
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

    const options = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const isSticky = entry.boundingClientRect.top < entry.rootBounds.top;

      if (isSticky) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    if (this.observer) {
      this.observer.disconnect();
    }
    this.containerService.stopPolling();
  }

  onValidInputChange(isValid: boolean) {
    this.validInput = isValid;
  }

  reopenEnrollmentDialog() {
    const currentResponse = this.registerResponse();
    if (currentResponse) {
      this.openRegistrationDialog(currentResponse);
      this.containerService.startPolling(this.containerSerial());
    }
  }

  createContainer() {
    this.registerResponse.set(null);
    const containerType = this.containerService.selectedContainerType()?.containerType;
    if (!containerType) return;
    const createData: ContainerCreateData = {
      container_type: containerType,
      description: this.description(),
      user: this.userService.selectionUsernameFilter()
    };
    if (createData.user || this.userAssignmentComponent?.onlyAddToRealm()) {
      createData.realm = this.userService.selectedUserRealm();
    }
    if (this.selectedTemplateName()) {
      createData.template_name = this.selectedTemplateName();
    }
    console.log("Creating container with data:", createData);
    this.containerService.createContainer(createData).subscribe({
      next: (response: PiResponse<{ container_serial: string }>) => {
        const containerSerial = response.result?.value?.container_serial;
        if (!containerSerial) {
          this.notificationService.openSnackBar("Container creation failed. No container serial returned.");
          return;
        }
        if (this.generateQRCode()) {
          this.registerContainer(containerSerial);
        } else {
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
          this.containerSerial.set(containerSerial);
        }
      }
    });
  }

  protected registerContainer(serial: string, regenerate: boolean = false) {
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
          this.openRegistrationDialog(registerResponse);
          this.containerService.startPolling(serial);
        }
      });
  }

  clearTemplateSelection() {
    this.selectedTemplate.set(null);
  }

  protected openRegistrationDialog(response: PiResponse<ContainerRegisterData>) {
    this.dialogData.set({
      response: response,
      containerSerial: this.containerSerial,
      registerContainer: this.registerContainer.bind(this)
    });

    this.dialogService.openDialog({
      component: ContainerCreatedDialogComponent,
      data: this.dialogData as Signal<ContainerCreationDialogData>
    });
  }
}
