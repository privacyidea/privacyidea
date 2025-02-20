import {
  Component,
  effect,
  Injectable,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  MatFormField,
  MatHint,
  MatLabel,
  MatSuffix,
} from '@angular/material/form-field';
import { MatOption, MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../token.component';
import { EnrollHotpComponent } from './enroll-hotp/enroll-hotp.component';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { ContainerService } from '../../../services/container/container.service';
import { RealmService } from '../../../services/realm/realm.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { UserService } from '../../../services/user/user.service';
import {
  DateAdapter,
  MAT_DATE_FORMATS,
  MatNativeDateModule,
  NativeDateAdapter,
  provideNativeDateAdapter,
} from '@angular/material/core';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import {
  EnrollmentOptions,
  TokenService,
} from '../../../services/token/token.service';
import { EnrollTotpComponent } from './enroll-totp/enroll-totp.component';
import { MatDialog } from '@angular/material/dialog';
import { TokenEnrollmentDialogComponent } from './token-enrollment-dialog/token-enrollment-dialog.component';
import { EnrollSpassComponent } from './enroll-spass/enroll-spass.component';
import { EnrollMotpComponent } from './enroll-motp/enroll-motp.component';
import { NgClass } from '@angular/common';
import { EnrollSshkeyComponent } from './enroll-sshkey/enroll-sshkey.component';
import { EnrollYubikeyComponent } from './enroll-yubikey/enroll-yubikey.component';
import { EnrollRemoteComponent } from './enroll-remote/enroll-remote.component';
import { EnrollYubicoComponent } from './enroll-yubico/enroll-yubico.component';

export const CUSTOM_DATE_FORMATS = {
  parse: { dateInput: 'YYYY-MM-DD' },
  display: {
    dateInput: 'YYYY-MM-DD',
    monthYearLabel: 'MMM YYYY',
    dateA11yLabel: 'LL',
    monthYearA11yLabel: 'MMMM YYYY',
  },
};

export const TIMEZONE_OFFSETS = (() => {
  const offsets = [];
  for (let i = -12; i <= 14; i++) {
    const sign = i < 0 ? '-' : '+';
    const absOffset = Math.abs(i);
    const hours = String(absOffset).padStart(2, '0');
    const label = `UTC${sign}${hours}:00`;
    const value = `${sign}${hours}:00`;
    offsets.push({ label, value });
  }
  return offsets;
})();

@Injectable()
export class CustomDateAdapter extends NativeDateAdapter {
  private timezoneOffset = '+00:00';

  override format(date: Date, displayFormat: any): string {
    const adjustedDate = this._applyTimezoneOffset(date);
    const year = adjustedDate.getFullYear();
    const month = (adjustedDate.getMonth() + 1).toString().padStart(2, '0');
    const day = adjustedDate.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private _applyTimezoneOffset(date: Date): Date {
    const offsetParts = this.timezoneOffset.split(':').map(Number);
    const offsetMinutes = offsetParts[0] * 60 + (offsetParts[1] || 0);
    const adjustedTime = date.getTime() + offsetMinutes * 60 * 1000;
    return new Date(adjustedTime);
  }
}

@Component({
  selector: 'app-token-enrollment',
  imports: [
    MatFormField,
    MatSelect,
    MatOption,
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    EnrollHotpComponent,
    MatInput,
    MatLabel,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    MatNativeDateModule,
    MatDatepickerModule,
    MatSuffix,
    MatButton,
    MatIcon,
    EnrollTotpComponent,
    MatIconButton,
    EnrollSpassComponent,
    EnrollMotpComponent,
    NgClass,
    EnrollSshkeyComponent,
    EnrollYubikeyComponent,
    EnrollRemoteComponent,
    EnrollYubicoComponent,
  ],
  providers: [
    provideNativeDateAdapter(),
    { provide: DateAdapter, useFactory: () => new CustomDateAdapter('+00:00') },
    { provide: MAT_DATE_FORMATS, useValue: CUSTOM_DATE_FORMATS },
  ],
  templateUrl: './token-enrollment.component.html',
  styleUrls: ['./token-enrollment.component.scss'],
  standalone: true,
})
export class TokenEnrollmentComponent {
  tokenTypesOptions = TokenComponent.tokenTypes;
  timezoneOptions = TIMEZONE_OFFSETS;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<string>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  selectedType = signal(this.tokenTypesOptions[0]);
  setPinValue = signal('');
  repeatPinValue = signal('');
  selectedUserRealm = signal('');
  selectedUsername = signal('');
  filteredContainerOptions = signal<string[]>([]);
  filteredUserOptions = signal<string[]>([]);
  selectedContainer = signal<string>('');
  containerOptions = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  userOptions = signal<string[]>([]);
  generateOnServer = signal(true);
  otpLength = signal(6);
  otpKey = signal('');
  hashAlgorithm = signal('sha1');
  description = signal('');
  selectedTimezoneOffset = signal('+01:00');
  selectedStartTime = signal('');
  selectedEndTime = signal('');
  selectedStartDate = signal(new Date());
  selectedEndDate = signal(new Date());
  timeStep = signal('30');
  response: WritableSignal<any> = signal(null);
  regenerateToken = signal(false);
  motpPin = signal('');
  repeatMotpPin = signal('');
  sshPublicKey = signal('');
  checkPinLocally = signal(false);
  remoteServer = signal({ url: '', id: '' });
  remoteSerial = signal('');
  remoteUser = signal('');
  remoteRealm = signal('');
  remoteResolver = signal('');
  protected readonly TokenEnrollmentDialogComponent =
    TokenEnrollmentDialogComponent;
  yubikeyIdentifier = signal('');

  constructor(
    private containerService: ContainerService,
    private realmService: RealmService,
    private notificationService: NotificationService,
    private userService: UserService,
    private tokenService: TokenService,
    protected dialog: MatDialog,
  ) {
    effect(() => {
      const value = this.selectedContainer();
      const filteredOptions = this._filterContainerOptions(value || '');
      this.filteredContainerOptions.set(filteredOptions);
    });

    effect(() => {
      this.getContainerOptions();
    });

    effect(() => {
      if (this.selectedType()) {
        this.response.set(null);
        this.tokenSerial.set('');
      }
    });

    effect(() => {
      this.getRealmOptions();
      this.getDefaultRealm();
      if (this.selectedUserRealm()) {
        this.userService.getUsers(this.selectedUserRealm()).subscribe({
          next: (users: any) => {
            this.userOptions.set(
              users.result.value.map((user: any) => user.username),
            );
          },
          error: (error) => {
            console.error('Failed to get users.', error);
            this.notificationService.openSnackBar('Failed to get users.');
          },
        });
      }
    });

    effect(() => {
      const value = this.selectedUsername();
      const filteredOptions = this._filterUserOptions(value || '');
      this.filteredUserOptions.set(filteredOptions);
    });

    effect(() => {
      if (this.regenerateToken()) {
        this.enrollToken();
      }
    });
  }

  getRealmOptions() {
    this.realmService.getRealms().subscribe({
      next: (realms: any) => {
        this.realmOptions.set(Object.keys(realms.result.value));
      },
      error: (error) => {
        console.error('Failed to get realms.', error);
        this.notificationService.openSnackBar('Failed to get realms.');
      },
    });
  }

  getContainerOptions() {
    this.containerService.getContainerData().subscribe({
      next: (containers: any) => {
        this.containerOptions.set(
          Object.values(
            containers.result.value.containers as {
              serial: string;
            }[],
          ).map((container) => container.serial),
        );
      },
      error: (error) => {
        console.error('Failed to get container options.', error);
        this.notificationService.openSnackBar(
          'Failed to get container options.',
        );
      },
    });
  }

  formatDateTimeOffset(date: Date, time: string, offset: string): string {
    const timeMatch = time.match(/^(\d{2}):(\d{2})$/);
    if (!timeMatch) {
      return '';
    }
    const hours = parseInt(timeMatch[1], 10);
    const minutes = parseInt(timeMatch[2], 10);
    const newDate = new Date(date.getTime());

    newDate.setHours(hours, minutes, 0, 0);

    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, '0');
    const day = String(newDate.getDate()).padStart(2, '0');
    const formattedHours = String(newDate.getHours()).padStart(2, '0');
    const formattedMinutes = String(newDate.getMinutes()).padStart(2, '0');
    const offsetNoColon = offset.replace(':', '');

    return `${year}-${month}-${day}T${formattedHours}:${formattedMinutes}${offsetNoColon}`;
  }

  enrollToken() {
    const enrollmentOptions: EnrollmentOptions = {
      type: this.selectedType().key,
      generateOnServer: this.generateOnServer(),
      otpLength: this.otpLength(),
      otpKey: this.otpKey(),
      hashAlgorithm: this.hashAlgorithm(),
      timeStep: this.timeStep(),
      description: this.description(),
      tokenSerial: this.tokenSerial(),
      user: this.selectedUsername(),
      container_serial: this.selectedContainer(),
      validity_period_start: this.formatDateTimeOffset(
        this.selectedStartDate(),
        this.selectedStartTime(),
        this.selectedTimezoneOffset(),
      ),
      validity_period_end: this.formatDateTimeOffset(
        this.selectedEndDate(),
        this.selectedEndTime(),
        this.selectedTimezoneOffset(),
      ),
      pin: this.setPinValue(),
      motpPin: this.motpPin(),
      sshPublicKey: this.sshPublicKey(),
      remoteServer: this.remoteServer(),
      remoteSerial: this.remoteSerial(),
      remoteUser: this.remoteUser(),
      remoteRealm: this.remoteRealm(),
      remoteResolver: this.remoteResolver(),
      checkPinLocally: this.checkPinLocally(),
      yubicoIdentifier: this.yubikeyIdentifier(),
    };

    this.tokenService.enrollToken(enrollmentOptions).subscribe({
      next: (response: any) => {
        if (!this.regenerateToken()) {
          this.notificationService.openSnackBar(
            `Token ${response.detail.serial} enrolled successfully.`,
          );
        }
        this.response.set(response);
        this.tokenSerial.set(response.detail.serial);
        this.dialog.open(TokenEnrollmentDialogComponent, {
          data: {
            response: response,
            tokenSerial: this.tokenSerial,
            containerSerial: this.containerSerial,
            selectedContent: this.selectedContent,
            regenerateToken: this.regenerateToken,
            isProgrammaticChange: this.isProgrammaticChange,
          },
        });
        if (this.regenerateToken()) {
          this.regenerateToken.set(false);
        }
      },
      error: (error) => {
        console.error('Failed to enroll token.', error);
        this.notificationService.openSnackBar('Failed to enroll token.');
      },
    });
  }

  private _filterContainerOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.containerOptions().filter((option) =>
      option.toLowerCase().includes(filterValue),
    );
  }

  private _filterUserOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.userOptions().filter((option) =>
      option.toLowerCase().includes(filterValue),
    );
  }

  private getDefaultRealm() {
    this.realmService.getDefaultRealm().subscribe({
      next: (realm: any) => {
        this.selectedUserRealm.set(Object.keys(realm.result.value)[0]);
      },
      error: (error) => {
        console.error('Failed to get default realm.', error);
        this.notificationService.openSnackBar('Failed to get default realm.');
      },
    });
  }
}
