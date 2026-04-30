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
  Signal,
  untracked,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInputModule, MatSuffix } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { PiResponse } from "src/app/app.component";
import { ROUTE_PATHS } from "src/app/route_paths";
import { AuthService, AuthServiceInterface } from "src/app/services/auth/auth.service";
import { ContainerTemplateService } from "src/app/services/container-template/container-template.service";
import {
  ContainerCreateData,
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerTemplate,
  ContainerType
} from "src/app/services/container/container.service";
import { DialogService, DialogServiceInterface } from "src/app/services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "src/app/services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "src/app/services/token/token.service";
import { UserService, UserServiceInterface } from "src/app/services/user/user.service";
import { ClearButtonComponent } from "../../shared/clear-button/clear-button.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ContainerRegistrationConfigComponent } from "../container-registration/container-registration-config/container-registration-config.component";
import { ContainerTemplateEditBodyComponent } from "../container-templates/container-template-edit/container-template-edit-body/container-template-edit-body.component";
import { UserAssignmentComponent } from "../user-assignment/user-assignment.component";
import {
  ContainerCreatedDialogComponent,
  ContainerCreationDialogData
} from "./container-created-dialog/container-created-dialog.component";
import {
  ContainerRegistrationCompletedDialogComponent,
  ContainerRegistrationCompletedDialogData
} from "./container-registration-completed-dialog/container-registration-completed-dialog.component";

@Component({
  selector: "app-container-create",
  imports: [
    MatButton,
    MatFormField,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatIconButton,
    MatTooltip,
    ScrollToTopDirective,
    NgClass,
    CommonModule,
    UserAssignmentComponent,
    MatSuffix,
    ClearButtonComponent,
    ContainerTemplateEditBodyComponent,
    MatInputModule,
    MatExpansionModule,
    ContainerRegistrationConfigComponent
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
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly renderer: Renderer2 = inject(Renderer2);
  private readonly router = inject(Router);

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild(UserAssignmentComponent) userAssignmentComponent!: UserAssignmentComponent;
  @ViewChild(ContainerRegistrationConfigComponent) registrationConfigComponent!: ContainerRegistrationConfigComponent;

  private observer!: IntersectionObserver;
  validInput = true;

  containerSerial = signal("");
  description = signal("");
  userSelected = computed(() => this.userService.selectionUsernameFilter() !== "");

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
  pollResponse = signal<any>(null);
  public dialogData = signal<ContainerCreationDialogData | null>(null);

  constructor() {
    this.containerSerial.set("");
    this.containerService.containerDetailsResource.set(undefined);

    effect(() => {
      this.containerService.selectedContainerType();
      untracked(() => this.resetCreateOptions());
    });

    effect(() => {
      const serial = this.containerSerial();
      if (!serial || !this.containerService.containerDetailsResource.hasValue()) return;

      const containerDetailResource = this.containerService.containerDetailsResource.value();
      if (!containerDetailResource?.result?.value) return;

      const container = containerDetailResource.result.value.containers[0];
      if (container?.info?.registration_state === "registered") {
        this.dialogService.closeAllDialogs();
        this.containerService.stopPolling();
        this.openRegistrationCompletedDialog(serial);
      }
    });
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;

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
    if (this.observer) this.observer.disconnect();
    this.containerService.stopPolling();
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
      user: this.userService.selectionUsernameFilter()
    };

    if (createData.user || this.userAssignmentComponent?.onlyAddToRealm()) {
      createData.realm = this.userService.selectedUserRealm();
    }

    const template = this.selectedTemplate();
    if (template && template.template_options.tokens.length > 0) {
      createData.name = template.name;
      createData.template = template;
      createData.template.template_display = template.name != "" ? template.name + ": " : "";
      createData.template.template_display += template.template_options.tokens.map((token) => token.type).join(", ");
    }

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
          this.onCreationSuccess(containerSerial);
        }
      }
    });
  }

  protected onCreationSuccess(serial: string) {
    this.containerService.containerSerial.set(serial);
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + serial);
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

  reopenEnrollmentDialog() {
    const currentResponse = this.registerResponse();
    if (currentResponse) {
      this.openRegistrationDialog(currentResponse);
      this.containerService.startPolling(this.containerService.containerSerial());
    }
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
