import { Component, effect, inject, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatOption } from '@angular/material/core';
import { MatDialog } from '@angular/material/dialog';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { MatTooltip } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { PiResponse } from '../../../app.component';
import { ROUTE_PATHS } from '../../../app.routes';
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
} from '../../../services/container/container.service';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../../../services/notification/notification.service';
import {
  RealmService,
  RealmServiceInterface,
} from '../../../services/realm/realm.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../services/token/token.service';
import {
  UserService,
  UserServiceInterface,
} from '../../../services/user/user.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../services/version/version.service';
import { ScrollToTopDirective } from '../../shared/directives/app-scroll-to-top.directive';
import { TokenComponent } from '../token.component';
import { ContainerRegistrationDialogComponent } from './container-registration-dialog/container-registration-dialog.component';

export type ContainerTypeOption = 'generic' | 'smartphone' | 'yubikey';

@Component({
  selector: 'app-container-create',
  imports: [
    MatButton,
    MatFormField,
    MatHint,
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
  ],
  templateUrl: './container-create.component.html',
  styleUrl: './container-create.component.scss',
})
export class ContainerCreateComponent {
  protected readonly versioningService: VersioningServiceInterface =
    inject(VersioningService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  protected readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  protected readonly TokenComponent = TokenComponent;
  private router = inject(Router);
  containerSerial = this.containerService.containerSerial;
  description = signal('');
  selectedTemplate = signal('');
  templateOptions = this.containerService.templates;
  onlyAddToRealm = signal(false);
  generateQRCode = signal(false);
  passphrasePrompt = signal('');
  passphraseResponse = signal('');
  registerResponse = signal<PiResponse<ContainerRegisterData> | null>(null);
  pollResponse = signal<any>(null);

  constructor(protected registrationDialog: MatDialog) {
    effect(() => {
      if (
        this.containerService.selectedContainerType().containerType ===
        'smartphone'
      ) {
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

  reopenEnrollmentDialog() {
    const currentResponse = this.registerResponse();
    if (currentResponse) {
      this.openRegistrationDialog(currentResponse);
      this.pollContainerRolloutState(this.containerSerial(), 2000);
    }
  }

  createContainer() {
    this.pollResponse.set(null);
    this.registerResponse.set(null);
    this.containerService
      .createContainer({
        container_type:
          this.containerService.selectedContainerType().containerType,
        description: this.description(),
        user_realm: this.userService.selectedUserRealm(),
        template: this.selectedTemplate(),
        user: this.userService.userNameFilter(),
        realm: this.onlyAddToRealm()
          ? this.userService.selectedUserRealm()
          : '',
      })
      .subscribe({
        next: (response) => {
          const containerSerial = response.result?.value?.container_serial;
          if (!containerSerial) {
            this.notificationService.openSnackBar(
              'Container creation failed. No container serial returned.',
            );
            return;
          }
          if (this.generateQRCode()) {
            this.containerService
              .registerContainer({
                container_serial: containerSerial,
                passphrase_response: this.passphraseResponse(),
                passphrase_prompt: this.passphrasePrompt(),
              })
              .subscribe((registerResponse) => {
                this.registerResponse.set(registerResponse);
                this.openRegistrationDialog(registerResponse);
                this.pollContainerRolloutState(containerSerial, 5000);
              });
          } else {
            this.notificationService.openSnackBar(
              `Container ${containerSerial} enrolled successfully.`,
            );
            this.router.navigateByUrl(
              ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial,
            );
            this.containerSerial.set(containerSerial);
          }
        },
      });
  }

  private resetCreateOptions = () => {
    this.registerResponse.set(null);
    this.pollResponse.set(null);
    this.passphrasePrompt.set('');
    this.passphraseResponse.set('');
    this.description.set('');
    this.selectedTemplate.set('');
  };

  private openRegistrationDialog(response: PiResponse<ContainerRegisterData>) {
    this.registrationDialog.open(ContainerRegistrationDialogComponent, {
      data: {
        response: response,
        containerSerial: this.containerSerial,
      },
    });
  }

  private pollContainerRolloutState(
    containerSerial: string,
    startTime: number,
  ) {
    return this.containerService
      .pollContainerRolloutState(containerSerial, startTime)
      .subscribe({
        next: (pollResponse) => {
          this.pollResponse.set(pollResponse);
          if (
            pollResponse.result?.value?.containers[0].info
              .registration_state !== 'client_wait'
          ) {
            this.registrationDialog.closeAll();
            this.router.navigateByUrl(
              ROUTE_PATHS.TOKENS_CONTAINERS + containerSerial,
            );
            this.notificationService.openSnackBar(
              `Container ${this.containerSerial()} enrolled successfully.`,
            );
          }
        },
      });
  }
}
