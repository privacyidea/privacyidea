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
import { TokenService } from '../../../services/token/token.service';
import { EnrollTotpComponent } from './enroll-totp/enroll-totp.component';
import { Observable } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { TokenEnrollmentDialogComponent } from './token-enrollment-dialog/token-enrollment-dialog.component';

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
  protected readonly TokenEnrollmentDialogComponent =
    TokenEnrollmentDialogComponent;
  tokenTypesOptions = TokenComponent.tokenTypes;
  timezoneOptions = TIMEZONE_OFFSETS;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<string>;
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
  otpLength = signal('6');
  otpKey = signal('');
  hashAlgorithm = signal('sha1');
  description = signal('');
  selectedTimezoneOffset = signal('+01:00');
  selectedStartTime = signal(0);
  selectedEndTime = signal(0);
  selectedStartDate = signal(new Date());
  selectedEndDate = signal(new Date());
  timeStep = signal('30');
  response: WritableSignal<any> = signal(null);
  regenerateToken = signal(false);

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
        this.enrollToken(
          this.selectedType().key,
          this.generateOnServer(),
          this.otpLength(),
          this.otpKey(),
          this.hashAlgorithm(),
          this.description(),
          this.timeStep(),
          this.tokenSerial(),
        );
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

  enrollToken(
    type: string,
    generateOnServer: boolean,
    otpLength: string,
    otpKey: string,
    hashAlgorithm: string,
    description: string,
    timeStep: string,
    tokenSerial: string,
  ) {
    let response = new Observable();
    switch (type) {
      case 'hotp':
        response = this.tokenService.enrollHotpToken(
          generateOnServer,
          otpLength,
          otpKey,
          hashAlgorithm,
          description,
          tokenSerial,
        );
        break;
      case 'totp':
        response = this.tokenService.enrollTotpToken(
          generateOnServer,
          otpLength,
          otpKey,
          hashAlgorithm,
          description,
          timeStep,
          tokenSerial,
        );
        break;
    }
    response.subscribe({
      next: (response: any) => {
        if (!this.regenerateToken()) {
          this.notificationService.openSnackBar(
            'Token ' + response.detail.serial + ' enrolled successfully.',
          );
        }
        this.response.set(response);
        this.tokenSerial.set(response.detail.serial);
        this.dialog.open(TokenEnrollmentDialogComponent, {
          data: {
            response: response,
            tokenSerial: this.tokenSerial,
            selectedContent: this.selectedContent,
            regenerateToken: this.regenerateToken,
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
