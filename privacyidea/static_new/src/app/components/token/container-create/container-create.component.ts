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
import { CommonModule, NgClass } from "@angular/common";
import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  Renderer2,
  signal,
  untracked,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatDialog } from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatFormField, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { PiResponse } from "../../../app.component";
import { ROUTE_PATHS } from "../../../route_paths";
import {
  ContainerCreateData,
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerType
} from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import {
  ContainerCreatedDialogComponent,
  ContainerCreationDialogData
} from "./container-created-dialog/container-created-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { ContainerRegistrationConfigComponent } from "../container-registration/container-registration-config/container-registration-config.component";
import {
  ContainerRegistrationCompletedDialogComponent,
  ContainerRegistrationCompletedDialogData
} from "./container-registration-completed-dialog/container-registration-completed-dialog.component";
import { ContainerRegistrationCompletedDialogWizardComponent } from "./container-registration-completed-dialog/container-registration-completed-dialog.wizard.component";
import { ContainerCreatedDialogWizardComponent } from "./container-created-dialog/container-created-dialog.wizard.component";
import { UserAssignmentComponent } from "../user-assignment/user-assignment.component";
import { ClearButtonComponent } from "../../shared/clear-button/clear-button.component";

export type ContainerTypeOption = "generic" | "smartphone" | "yubikey";

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
    ClearButtonComponent
  ],
  templateUrl: "./container-create.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateComponent {
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly renderer: Renderer2 = inject(Renderer2);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly wizard: boolean = false;
  private router = inject(Router);
  private observer!: IntersectionObserver;
  containerSerial = this.containerService.containerSerial;
  description = signal("");
  selectedTemplate = signal("");
  templateOptions = this.containerService.templates;
  generateQRCode: WritableSignal<boolean> = linkedSignal({
      source: this.containerService.selectedContainerType,
      computation: (containerType: ContainerType) => containerType.containerType === "smartphone"
    }
  );
  passphrasePrompt = signal("");
  passphraseResponse = signal("");
  userStorePassphrase = signal(false);
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
    this.selectedTemplate.set("");
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
      const containerDetailResource = this.containerService.containerDetailResource.value();
      const serial = this.containerService.containerSerial();

      if (!serial) {
        return;
      }

      if (containerDetailResource?.result?.value) {
        const registrationState = containerDetailResource.result.value.containers[0]?.info?.registration_state;

        if (registrationState !== "client_wait") {
          this.registrationDialog.closeAll();
          this.containerService.stopPolling();

          let registrationCompletedDialogComponent: any = ContainerRegistrationCompletedDialogComponent;
          if (this.wizard) {
            registrationCompletedDialogComponent = ContainerRegistrationCompletedDialogWizardComponent;
          }

          this.registrationDialog.open(registrationCompletedDialogComponent,
            { data: { "containerSerial": serial } as ContainerRegistrationCompletedDialogData });
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
    const createData: ContainerCreateData = {
      container_type: this.containerService.selectedContainerType().containerType,
      description: this.description(),
      user: this.userService.selectionUsernameFilter()
    };
    if (createData.user || this.userAssignmentComponent?.onlyAddToRealm()) {
      createData.realm = this.userService.selectedUserRealm();
    }
    if (this.selectedTemplate()) {
      createData.template_name = this.selectedTemplate();
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
        passphrase_user: false,
        passphrase_response: this.registrationConfigComponent?.passphraseResponse() || "",
        passphrase_prompt: this.registrationConfigComponent?.passphrasePrompt() || ""
      })
      .subscribe((registerResponse) => {
        this.registerResponse.set(registerResponse);
        if (regenerate) {
          this.dialogData.update(data => data ? { ...data, response: registerResponse } : data);
        } else {
          this.openRegistrationDialog(registerResponse);
          this.containerService.startPolling(serial);
        }
      });
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

  clearTemplateSelection() {
    this.selectedTemplate.set("");
  }
}