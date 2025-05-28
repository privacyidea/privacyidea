import {
  Component,
  effect,
  linkedSignal,
  signal,
  untracked,
} from '@angular/core';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { VersionService } from '../../../services/version/version.service';
import { TokenComponent } from '../token.component';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { UserService } from '../../../services/user/user.service';
import { RealmService } from '../../../services/realm/realm.service';
import { MatCheckbox } from '@angular/material/checkbox';
import { ContainerService } from '../../../services/container/container.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { MatDialog } from '@angular/material/dialog';
import { ContainerRegistrationDialogComponent } from './container-registration-dialog/container-registration-dialog.component';
import { TokenService } from '../../../services/token/token.service';
import { ContentService } from '../../../services/content/content.service';

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
  ],
  templateUrl: './container-create.component.html',
  styleUrl: './container-create.component.scss',
})
export class ContainerCreateComponent {
  protected readonly TokenComponent = TokenComponent;
  selectedContent = this.contentService.selectedContent;
  containerSerial = this.containerService.containerSerial;
  description = signal('');
  selectedTemplate = signal('');
  templateOptions = this.containerService.templates;
  onlyAddToRealm = signal(false);
  generateQRCode = signal(false);
  passphrasePrompt = signal('');
  passphraseResponse = signal('');
  registerResponse = signal<any>(null);
  pollResponse = signal<any>(null);

  constructor(
    protected registrationDialog: MatDialog,
    protected versioningService: VersionService,
    protected userService: UserService,
    protected realmService: RealmService,
    protected containerService: ContainerService,
    private notificationService: NotificationService,
    protected tokenService: TokenService,
    private contentService: ContentService,
  ) {
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
    this.openRegistrationDialog(this.registerResponse());
    this.pollContainerRolloutState(this.containerSerial(), 2000);
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
        user: this.userService.selectedUsername(),
        realm: this.onlyAddToRealm()
          ? this.userService.selectedUserRealm()
          : '',
      })
      .subscribe({
        next: (response: any) => {
          if (this.generateQRCode()) {
            this.containerService
              .registerContainer({
                container_serial: response.result?.value.container_serial,
                passphrase_response: this.passphraseResponse(),
                passphrase_prompt: this.passphrasePrompt(),
              })
              .subscribe((registerResponse) => {
                this.registerResponse.set(registerResponse);
                this.openRegistrationDialog(registerResponse);
                this.pollContainerRolloutState(
                  response.result?.value.container_serial,
                  5000,
                );
              });
          } else {
            this.notificationService.openSnackBar(
              `Container ${response.result?.value.container_serial} enrolled successfully.`,
            );
            this.selectedContent.set('container_details');
            this.containerSerial.set(response.result?.value.container_serial);
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

  private openRegistrationDialog(response: any) {
    this.registrationDialog.open(ContainerRegistrationDialogComponent, {
      data: {
        response: response,
        containerSerial: this.containerSerial,
        selectedContent: this.selectedContent,
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
        next: (pollResponse: any) => {
          this.pollResponse.set(pollResponse);
          if (
            pollResponse.result?.value.containers[0].info.registration_state !==
            'client_wait'
          ) {
            this.registrationDialog.closeAll();
            this.selectedContent.set('container_details');
            this.notificationService.openSnackBar(
              `Container ${this.containerSerial()} enrolled successfully.`,
            );
          }
        },
      });
  }
}
