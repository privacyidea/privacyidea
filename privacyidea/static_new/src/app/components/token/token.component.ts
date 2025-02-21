import { Component, effect, signal, ViewChild } from '@angular/core';
import { TokenTableComponent } from './token-table/token-table.component';
import { CommonModule, NgClass, NgTemplateOutlet } from '@angular/common';
import { ContainerTableComponent } from './container-table/container-table.component';
import { TokenDetailsComponent } from './token-details/token-details.component';
import { ContainerDetailsComponent } from './container-details/container-details.component';
import {
  MatDrawer,
  MatDrawerContainer,
  MatSidenavModule,
} from '@angular/material/sidenav';
import { MatFabButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { OverflowService } from '../../services/overflow/overflow.service';
import { TokenCardComponent } from './token-card/token-card.component';
import { NotificationService } from '../../services/notification/notification.service';
import { TokenGetSerial } from './token-get-serial/token-get-serial.component';
import { TokenEnrollmentComponent } from './token-enrollment/token-enrollment.component';
import { FilterTable } from '../universals/filter-table/filter-table.component';
import { Observable } from 'rxjs';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSortModule } from '@angular/material/sort';
import { TableUtilsService } from '../../services/table-utils/table-utils.service';
import { TokenApplications } from './token-applications/token-applications';

@Component({
  selector: 'app-token-grid',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatPaginatorModule,
    MatTableModule,
    MatSortModule,
    NgClass,
    MatIcon,
    MatFabButton,
    TokenTableComponent,
    TokenCardComponent,
    TokenDetailsComponent,
    TokenGetSerial,
    ContainerTableComponent,
    ContainerDetailsComponent,
    MatDrawerContainer,
    MatDrawer,
    MatSidenavModule,
    MatIcon,
    MatFabButton,
    TokenEnrollmentComponent,
    FilterTable,
    TokenApplications,
  ],
  templateUrl: './token.component.html',
  styleUrl: './token.component.scss',
})
export class TokenComponent {
  static tokenTypes = [
    {
      key: 'hotp',
      info: 'HOTP: Counter-based One Time Passwords',
      text: 'The HOTP token is an event based token. You can paste a secret key or have the server generate the secret and scan the QR code with a smartphone app like the privacyIDEA Authenticator turning your smartphone into an authentication device. You can also use other authenticator apps like Google Authenticator. But note, that these might have limitations in the supported hash algorithms or other parameters.',
    },
    {
      key: 'totp',
      info: 'TOTP: Time-based One Time Passwords',
      text: 'The TOTP token is a time based token. You can paste a secret key or have the server generate the secret and scan the QR code with a smartphone app like the privacyIDEA Authenticator turning your smartphone into an authentication device. You can also use other authenticator apps like Google Authenticator, Microsoft Authenticator, Authy or FreeOTP. But note, that these might have limitations in the supported hash algorithms or other parameters.',
    },
    {
      key: 'spass',
      info: 'SPass: Simple Pass token. Static passwords',
      text: 'The Simple Pass Token does not take additional arguments. You only need to specify an OTP PIN.\n',
    },
    {
      key: 'motp',
      info: 'mOTP: classical mobile One Time Passwords',
      text: 'The mOTP token is a time based OTP token for mobile devices. You can have the server generate the secret and scan the QR code.',
    },
    {
      key: 'sshkey',
      info: 'SSH Public Key: The public SSH key',
      text: 'The SSH Key Token stores the public SSH Key in the server. This can be used to authenticate to a secure shell.',
    },
    {
      key: 'yubikey',
      info: 'Yubikey AES mode: One Time Passwords with Yubikey',
      text: 'The Yubikey Token is an USB device that emits an event based One Time Password. You can initialize the Yubikey using the YubiKey personalization tools. The secret hex key and the final OTP length are needed here. For tokens compatible with the Yubico cloud service the OTP length must be 44 (12 characters UID and 32 characters OTP). When programming the token for the Yubico cloud service, the Public Identity Length must be 6 bytes, which will give you a UID with 12 characters. The current OTP length of a programmed YubiKey can automatically be determined by inserting it in the test field.',
    },
    {
      key: 'remote',
      info: 'Remote Token: Forward authentication request to another server',
      text: 'The remote token forwards the authentication request to another privacyIDEA server. You can choose if the PIN should be stripped and checked locally.',
    },
    {
      key: 'yubico',
      info: 'Yubikey Cloud mode: Forward authentication request to YubiCloud',
      text: 'The Yubico Cloud mode forwards the authentication request to the YubiCloud. The Yubikey needs to be registered with the YubiCloud.',
    },
    {
      key: 'radius',
      info: 'RADIUS: Forward authentication request to a RADIUS server',
      text: 'The RADIUS token forwards the authentication request to another RADIUS server. You can choose if the PIN should be stripped and checked locally.',
    },
    {
      key: 'sms',
      info: 'SMS: Send a One Time Password to the users mobile phone',
      text: 'The SMS Token sends an OTP value to the mobile phone of the user.',
    },
    {
      key: '4eyes',
      info: '4Eyes Token: Use tokens of two or more users to authenticate',
      text: 'The 4 Eyes token will only authenticate if two or more users are present at once. You can define how many existing tokens of the given realms need to be present to perform a successful authentication.',
    },
    {
      key: 'ASP',
      info: 'Application Specific Password: A token with a fixed password. Can be used for certain applications or services.',
      text: 'The Application Specific Password Token is a static password, that can be bound to certain services. This static password then can only be used to authenticate at this service.',
    },
    {
      key: 'cert',
      info: 'Certificate: Enroll an x509 Certificate Token.',
      text: 'The Certificate Token lets you enroll an x509 ceritificate by the given CA.',
    },
    {
      key: 'daypassword',
      info: 'DayPassword: A time-based token with a variable timestep and the possibility to use the OTP more than once.',
      text: 'The DayPassword token is a time based password token. You can paste a secret key or have the server generate the secret and scan the QR code with an authenticator app that supports the token.',
    },
    {
      key: 'email',
      info: 'EMail: Send a One Time Password to the users email address.',
      text: 'The Email Token sends the OTP value to the users email address.',
    },
    {
      key: 'indexsecret',
      info: 'Indexed Secret: Request certain positions of a shared secret from the user.',
      text: 'The indexed secret Token is based on a shared secret between privacyIDEA and the user. During authentication the user is asked for random positions from this known secret.',
    },
    {
      key: 'paper',
      info: 'PPR: One Time Passwords printed on a sheet of paper.',
      text: 'The Paper token will let you print a list of OTP values. These OTP values can be used to authenticate. You need to use on value after the other.',
    },
    {
      key: 'push',
      info: 'PUSH: Send a push notification to a smartphone.',
      text: 'With the PUSH token privacyIDEA sends a notification to your registered smartphone asking if you want to approve the authentication step. You can accept or deny the authentication on your smartphone. For the enrollment process and for the authentication process your smartphone needs an internet connection to privacyIDEA.',
    },
    {
      key: 'questionnaire',
      info: 'Questionnaire: Enroll Questions for the user.',
      text: 'The Questionnaire token will let you define answers to questions. When authenticating with this type of token, you will be asked a random question and then need to provide the previously defined answer.',
    },
    {
      key: 'registration',
      info: 'Registration: A token that creates sa registration code that can be used as a second factor once.',
      text: 'The registration token is a code, that the user can use to authenticate once! After using this code to login, the registration token is deleted and can not be used anymore. This is used, so that the user can enroll a token on his own, after logging in for the first time.',
    },
    {
      key: 'remote',
      info: 'Remote Token: Forward authentication request to another server.',
      text: 'The remote token forwards the authentication request to another privacyIDEA server. You can choose if the PIN should be stripped and checked locally.',
    },
    {
      key: 'tan',
      info: 'TAN: TANs printed on a sheet of paper.',
      text: 'The TAN token will let you print a list of OTP values. These OTP values can be used to authenticate. The values can be used in an arbitrary order.',
    },
    {
      key: 'tiqr',
      info: 'TiQR: Enraoll a TiQR token.',
      text: 'The TiQR token is a Smartphone App token, which allows easy authentication by just scanning a QR Code during the authentication process.',
    },
    {
      key: 'u2f',
      info: 'U2F: Enroll a U2F token.',
      text: 'The U2F token is a token defined by the Fido Alliance. You can register this token with any webservice and with as many web services you wish to.',
    },
    {
      key: 'vasco',
      info: 'VASCO Token: Authentication using VASCO tokens.',
      text: 'The VASCO token is a proprietary OTP token. You can paste the VASCO token blob in a hexlified format.',
    },
    {
      key: 'webauthn',
      info: 'WebAuthn: Entoll a Web Authentication token.',
      text: 'The WebAuthn token is a token defined by the W3C and the Fido Alliance. You can register this token with any webservice and with as many web services you wish to.\n',
    },
  ];
  selectedContent = signal('token_overview');
  tokenSerial = signal('');
  containerSerial = signal('');
  tokenIsActive = signal(true);
  revoked = signal(true);
  refreshTokenDetails = signal(false);
  refreshContainerDetails = signal(false);
  states = signal<string[]>([]);
  isProgrammaticChange = signal(false);
  @ViewChild('tokenDetailsComponent')
  tokenDetailsComponent!: TokenDetailsComponent;
  @ViewChild('containerDetailsComponent')
  containerDetailsComponent!: ContainerDetailsComponent;
  @ViewChild('tokenGetSerial') tokenGetSerial!: TokenGetSerial;
  @ViewChild('drawer') drawer!: MatDrawer;

  constructor(
    protected overflowService: OverflowService,
    private notificationService: NotificationService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      if (this.refreshTokenDetails()) {
        this.onRefreshTokenDetails();
      }
    });
    effect(() => {
      if (this.refreshContainerDetails()) {
        this.onRefreshContainerDetails();
      }
    });
  }

  onRefreshTokenDetails(): void {
    if (this.tokenDetailsComponent) {
      this.tokenDetailsComponent.showTokenDetail().subscribe({
        next: () => {
          this.refreshTokenDetails.set(false);
        },
        error: (error) => {
          console.error('Error refreshing token details.', error);
          this.notificationService.openSnackBar(
            'Error refreshing token details.',
          );
        },
      });
    } else {
      console.warn('TokenDetailsComponent is not yet initialized.');
      this.notificationService.openSnackBar(
        'TokenDetailsComponent is not yet initialized.',
      );
    }
  }

  onRefreshContainerDetails(): void {
    if (this.containerDetailsComponent) {
      this.containerDetailsComponent.showContainerDetail().subscribe({
        next: () => {
          this.refreshContainerDetails.set(false);
        },
        error: (error) => {
          console.error('Error refreshing token details.', error);
          this.notificationService.openSnackBar(
            'Error refreshing token details.',
          );
        },
      });
    } else {
      console.warn('ContainerDetailsComponent is not yet initialized.');
      this.notificationService.openSnackBar(
        'ContainerDetailsComponent is not yet initialized.',
      );
    }
  }

  fetchDataHandler(): Observable<any> {
    return Observable.create(() => {});
  }

  fetchResponseHandler(
    response: any,
  ): [number, MatTableDataSource<any, MatPaginator>] {
    return [0, new MatTableDataSource()];
  }

  columnsKeyMap = [
    { key: 'serial', label: 'Serial' },
    { key: 'service_id', label: 'Service ID' },
    { key: 'user', label: 'SSH user' },
  ];
  handleColumnClick(key: string, element: any) {}
}
