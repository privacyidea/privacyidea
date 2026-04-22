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

import { NgClass, CommonModule } from "node_modules/@angular/common/types/_common_module-chunk";
import { signal, WritableSignal } from "node_modules/@angular/core/types/_chrome_dev_tools_performance-chunk";
import { Component, Renderer2, ElementRef, effect } from "node_modules/@angular/core/types/_discovery-chunk";
import { computed, linkedSignal, ViewChild, untracked } from "node_modules/@angular/core/types/core";
import { inject } from "node_modules/@angular/core/types/primitives-di";
import { FormsModule } from "node_modules/@angular/forms/types/forms";
import { MatDialog } from "node_modules/@angular/material/types/_dialog-chunk";
import { MatFormField, MatSuffix } from "node_modules/@angular/material/types/_form-field-chunk";
import { MatLabel } from "node_modules/@angular/material/types/_form-field-module-chunk";
import { MatIcon } from "node_modules/@angular/material/types/_icon-module-chunk";
import { MatOption } from "node_modules/@angular/material/types/_option-chunk";
import { MatButton, MatIconButton } from "node_modules/@angular/material/types/button";
import { MatCheckbox } from "node_modules/@angular/material/types/checkbox";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelTitle,
  MatExpansionPanelHeader
} from "node_modules/@angular/material/types/expansion";
import { MatInput } from "node_modules/@angular/material/types/input";
import { MatSelect } from "node_modules/@angular/material/types/select";
import { MatTooltip } from "node_modules/@angular/material/types/tooltip";
import { Router } from "node_modules/@angular/router/types/_router_module-chunk";
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
import { ContainerTemplateEditBodyComponent } from "../container-templates/container-template-edit/container-template-edit-body/container-template-edit-body.component";
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
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly renderer: Renderer2 = inject(Renderer2);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly wizard: boolean = false;
  private router = inject(Router);
  private observer!: IntersectionObserver;
  containerSerial = this.containerService.containerSerial;
  description = signal("");
  readonly tokens = computed<TokenEnrollmentPayload[]>(() => this.selectedTemplate()?.template_options.tokens ?? []);
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
  readonly availableTokenTypes = computed(() => {
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

  constructor(protected registrationDialog: MatDialog) {
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

      if (!serial) {
        return;
      }

      if (!this.containerService.containerDetailResource.hasValue()) {
        return;
      }

      const containerDetailResource = this.containerService.containerDetailResource.value();
      if (containerDetailResource?.result?.value) {
        const container = containerDetailResource.result.value.containers[0];
        const registrationState = container?.info?.registration_state;

        if (registrationState !== "client_wait") {
          this.registrationDialog.closeAll();
          this.containerService.stopPolling();

          if (
            container?.type === "smartphone" &&
            this.authService.containerWizard().registration &&
            this.authService.actionAllowed("container_register")
          ) {
            let registrationCompletedDialogComponent: any = ContainerRegistrationCompletedDialogComponent;
            if (this.wizard) {
              registrationCompletedDialogComponent = ContainerRegistrationCompletedDialogWizardComponent;
            }

            this.registrationDialog.open(registrationCompletedDialogComponent, {
              data: { containerSerial: serial } as ContainerRegistrationCompletedDialogData
            });
          } else if (this.wizard) {
            this.openRegistrationDialog({
              result: {
                value: {
                  container_serial: serial
                }
              }
            } as unknown as PiResponse<ContainerRegisterData>);
          }
        }
      }
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
    this.containerService.createContainer(createData).subscribe({
      next: (response) => {
        const containerSerial = response.result?.value?.container_serial;
        if (!containerSerial) {
          this.notificationService.openSnackBar("Container creation failed. No container serial returned.");
          return;
        }
        if (this.generateQRCode()) {
          this.registerContainer(containerSerial);
        } else if (this.wizard) {
          this.containerSerial.set(containerSerial);
        } else {
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
          this.containerSerial.set(containerSerial);
        }
      }
    });
  }

  registerContainer(serial: string, regenerate: boolean = false) {
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

  private openRegistrationDialog(response: PiResponse<ContainerRegisterData>) {
    this.dialogData.set({
      response: response,
      containerSerial: this.containerSerial,
      registerContainer: this.registerContainer.bind(this)
    });
    let dialogComponent: any = ContainerCreatedDialogComponent;
    if (this.wizard) {
      dialogComponent = ContainerCreatedDialogWizardComponent;
    }
    this.registrationDialog.open(dialogComponent, {
      data: this.dialogData
    });
  }
}
