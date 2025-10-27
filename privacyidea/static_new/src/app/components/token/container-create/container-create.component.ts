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
  Renderer2,
  signal,
  untracked,
  ViewChild
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
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
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { PiResponse } from "../../../app.component";
import { ROUTE_PATHS } from "../../../route_paths";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface
} from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { TokenComponent } from "../token.component";
import {
  ContainerCreatedDialogComponent,
  ContainerCreationDialogData
} from "./container-created-dialog/container-created-dialog.component";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { ContainerRegistrationConfigComponent } from "../container-registration/container-registration-config/container-registration-config.component";

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
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatError,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    MatTooltip,
    ScrollToTopDirective,
    NgClass,
    ClearableInputComponent,
    CommonModule,
    ContainerRegistrationConfigComponent
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
  protected readonly TokenComponent = TokenComponent;
  protected readonly renderer: Renderer2 = inject(Renderer2);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private router = inject(Router);
  private observer!: IntersectionObserver;
  containerSerial = this.containerService.containerSerial;
  description = signal("");
  selectedTemplate = signal("");
  templateOptions = this.containerService.templates;
  onlyAddToRealm = signal(false);
  generateQRCode = signal(false);
  passphrasePrompt = signal("");
  passphraseResponse = signal("");
  userStorePassphrase = signal(false);
  registerResponse = signal<PiResponse<ContainerRegisterData> | null>(null);
  userSelected = computed(() => this.userService.selectionUsernameFilter() !== "");
  public dialogData = signal<ContainerCreationDialogData | null>(null);

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild(ContainerRegistrationConfigComponent)
  registrationConfigComponent!: ContainerRegistrationConfigComponent;

  constructor(protected registrationDialog: MatDialog) {
    effect(() => {
      if (this.containerService.selectedContainerType().containerType === "smartphone") {
        this.generateQRCode.set(true);
      } else {
        this.generateQRCode.set(false);
      }
    });
    effect(() => {
      this.containerService.selectedContainerType();
      untracked(() => {
        this.resetCreateOptions();
      });
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
  }

  validInput = true;

  onValidInputChange(isValid: boolean) {
    this.validInput = isValid;
  }


  reopenEnrollmentDialog() {
    const currentResponse = this.registerResponse();
    if (currentResponse) {
      this.openRegistrationDialog(currentResponse);
      this.pollContainerRolloutState(this.containerSerial(), 2000);
    }
  }

  createContainer() {
    this.registerResponse.set(null);
    const createData = {
      container_type: this.containerService.selectedContainerType().containerType,
      description: this.description(),
      template: this.selectedTemplate(),
      user: this.userService.selectionUsernameFilter(),
      realm: ""
    };
    if (createData.user || this.onlyAddToRealm()) {
      createData.realm = this.userService.selectedUserRealm();
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
        passphrase_response: this.registrationConfigComponent.passphraseResponse(),
        passphrase_prompt: this.registrationConfigComponent.passphrasePrompt()
      })
      .subscribe((registerResponse) => {
        this.registerResponse.set(registerResponse);
        if (regenerate) {
          this.dialogData.update(data => data ? { ...data, response: registerResponse } : data);
        } else {
          this.openRegistrationDialog(registerResponse);
          this.pollContainerRolloutState(serial, 5000);
        }
      });
  }

  private resetCreateOptions = () => {
    this.registerResponse.set(null);
    this.passphrasePrompt.set("");
    this.passphraseResponse.set("");
    this.userStorePassphrase.set(false);
    this.description.set("");
    this.selectedTemplate.set("");
  };

  private openRegistrationDialog(response: PiResponse<ContainerRegisterData>) {
    this.dialogData.set({
      response: response,
      containerSerial: this.containerSerial,
      registerContainer: this.registerContainer.bind(this)
    });
    this.registrationDialog.open(ContainerCreatedDialogComponent, {
      data: this.dialogData
    });
  }

  private pollContainerRolloutState(containerSerial: string, startTime: number) {
    return this.containerService.pollContainerRolloutState(containerSerial, startTime).subscribe({
      next: (response) => {
        if (response?.result?.value?.containers[0].info.registration_state !== "client_wait") {
          this.registrationDialog.closeAll();
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
        }
      }
    });
  }
}
