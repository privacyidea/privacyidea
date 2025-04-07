import { Component, effect, signal, ViewChild } from '@angular/core';
import { TokenTableComponent } from './token-table/token-table.component';
import { CommonModule } from '@angular/common';
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
import { TokenApplications } from './token-applications/token-applications';
import { ChallengesTableComponent } from './challenges-table/challenges-table.component';
import { LoadingService } from '../../services/loading/loading-service';
import { ContainerCreateComponent } from './container-create/container-create.component';

export type TokenType =
  | 'hotp'
  | 'totp'
  | 'spass'
  | 'motp'
  | 'sshkey'
  | 'yubikey'
  | 'remote'
  | 'yubico'
  | 'radius'
  | 'sms'
  | '4eyes'
  | 'applspec'
  | 'certificate'
  | 'daypassword'
  | 'email'
  | 'indexedsecret'
  | 'paper'
  | 'push'
  | 'question'
  | 'registration'
  | 'tan'
  | 'tiqr'
  | 'u2f'
  | 'vasco'
  | 'webauthn'
  | 'passkey';

export type TokenSelectedContent =
  | 'token_overview'
  | 'token_details'
  | 'container_overview'
  | 'container_details'
  | 'container_create'
  | 'token_enrollment'
  | 'token_challenges'
  | 'token_applications'
  | 'token_get_serial';

export interface TokenTypeOption {
  key: TokenType;
  info: string;
  text: string;
}

@Component({
  selector: 'app-token-grid',
  standalone: true,
  imports: [
    CommonModule,
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
    TokenApplications,
    ChallengesTableComponent,
    ContainerCreateComponent,
  ],
  templateUrl: './token.component.html',
  styleUrl: './token.component.scss',
})
export class TokenComponent {
  static tokenTypeTexts = [
    {
      key: 'hotp',
      text: 'The HOTP token is an event based token. You can paste a secret key or have the server generate the secret and scan the QR code with a smartphone app like the privacyIDEA Authenticator turning your smartphone into an authentication device. You can also use other authenticator apps like Google Authenticator. But note, that these might have limitations in the supported hash algorithms or other parameters.',
    },
    {
      key: 'totp',
      text: 'The TOTP token is a time based token. You can paste a secret key or have the server generate the secret and scan the QR code with a smartphone app like the privacyIDEA Authenticator turning your smartphone into an authentication device. You can also use other authenticator apps like Google Authenticator, Microsoft Authenticator, Authy or FreeOTP. But note, that these might have limitations in the supported hash algorithms or other parameters.',
    },
    {
      key: 'spass',
      text: 'The Simple Pass Token does not take additional arguments. You only need to specify an OTP PIN.\n',
    },
    {
      key: 'motp',
      text: 'The mOTP token is a time based OTP token for mobile devices. You can have the server generate the secret and scan the QR code.',
    },
    {
      key: 'sshkey',
      text: 'The SSH Key Token stores the public SSH Key in the server. This can be used to authenticate to a secure shell.',
    },
    {
      key: 'yubikey',
      text: 'The Yubikey Token is an USB device that emits an event based One Time Password. You can initialize the Yubikey using the YubiKey personalization tools. The secret hex key and the final OTP length are needed here. For tokens compatible with the Yubico cloud service the OTP length must be 44 (12 characters UID and 32 characters OTP). When programming the token for the Yubico cloud service, the Public Identity Length must be 6 bytes, which will give you a UID with 12 characters. The current OTP length of a programmed YubiKey can automatically be determined by inserting it in the test field.',
    },
    {
      key: 'remote',
      text: 'The remote token forwards the authentication request to another privacyIDEA server. You can choose if the PIN should be stripped and checked locally.',
    },
    {
      key: 'yubico',
      text: 'The Yubico Cloud mode forwards the authentication request to the YubiCloud. The Yubikey needs to be registered with the YubiCloud.',
    },
    {
      key: 'radius',
      text: 'The RADIUS token forwards the authentication request to another RADIUS server. You can choose if the PIN should be stripped and checked locally.',
    },
    {
      key: 'sms',
      text: 'The SMS Token sends an OTP value to the mobile phone of the user.',
    },
    {
      key: '4eyes',
      text: 'The 4 Eyes token will only authenticate if two or more users are present at once. You can define how many existing tokens of the given realms need to be present to perform a successful authentication.',
    },
    {
      key: 'applspec',
      text: 'The Application Specific Password Token is a static password, that can be bound to certain services. This static password then can only be used to authenticate at this service.',
    },
    {
      key: 'certificate',
      text: 'The Certificate Token lets you enroll an x509 ceritificate by the given CA.',
    },
    {
      key: 'daypassword',
      text: 'The DayPassword token is a time based password token. You can paste a secret key or have the server generate the secret and scan the QR code with an authenticator app that supports the token.',
    },
    {
      key: 'email',
      text: 'The Email Token sends the OTP value to the users email address.',
    },
    {
      key: 'indexedsecret',
      text: 'The indexed secret Token is based on a shared secret between privacyIDEA and the user. During authentication the user is asked for random positions from this known secret.',
    },
    {
      key: 'paper',
      text: 'The Paper token will let you print a list of OTP values. These OTP values can be used to authenticate. You need to use on value after the other.',
    },
    {
      key: 'push',
      text: 'With the PUSH token privacyIDEA sends a notification to your registered smartphone asking if you want to approve the authentication step. You can accept or deny the authentication on your smartphone. For the enrollment process and for the authentication process your smartphone needs an internet connection to privacyIDEA.',
    },
    {
      key: 'question',
      text: 'The Questionnaire token will let you define answers to questions. When authenticating with this type of token, you will be asked a random question and then need to provide the previously defined answer.',
    },
    {
      key: 'registration',
      text: 'The registration token is a code, that the user can use to authenticate once! After using this code to login, the registration token is deleted and can not be used anymore. This is used, so that the user can enroll a token on his own, after logging in for the first time.',
    },
    {
      key: 'tan',
      text: 'The TAN token will let you print a list of OTP values. These OTP values can be used to authenticate. The values can be used in an arbitrary order.',
    },
    {
      key: 'tiqr',
      text: 'The TiQR token is a Smartphone App token, which allows easy authentication by just scanning a QR Code during the authentication process.',
    },
    {
      key: 'u2f',
      text: 'The U2F token is a token defined by the Fido Alliance. You can register this token with any webservice and with as many web services you wish to.',
    },
    {
      key: 'vasco',
      text: 'The VASCO token is a proprietary OTP token. You can paste the VASCO token blob in a hexlified format.',
    },
    {
      key: 'webauthn',
      text: 'The WebAuthn token is a token defined by the W3C and the Fido Alliance. You can register this token with any webservice and with as many web services you wish to.\n',
    },
    {
      key: 'passkey',
      text: 'The Passkey is a token defined by the W3C and the Fido Alliance. You can register this token with any webservice and with as many web services you wish to.',
    },
  ];
  tokenTypeOptions = signal<TokenTypeOption[]>([]);
  selectedContent = signal<TokenSelectedContent>('token_overview');
  tokenSerial = signal('');
  containerSerial = signal('');
  tokenIsActive = signal(true);
  revoked = signal(true);
  refreshTokenDetails = signal(false);
  refreshTokenOverview = signal(false);
  refreshContainerOverview = signal(false);
  refreshContainerDetails = signal(false);
  states = signal<string[]>([]);
  isProgrammaticChange = signal(false);
  isTokenDrawerOverflowing = signal(false);
  containerSelection = signal([]);
  tokenSelection = signal([]);
  @ViewChild('tokenDetailsComponent')
  tokenDetailsComponent!: TokenDetailsComponent;
  @ViewChild('containerDetailsComponent')
  containerDetailsComponent!: ContainerDetailsComponent;
  @ViewChild('tokenTableComponent') tokenTableComponent!: TokenTableComponent;
  @ViewChild('containerTableComponent')
  containerTableComponent!: ContainerTableComponent;
  @ViewChild('tokenGetSerial') tokenGetSerial!: TokenGetSerial;
  @ViewChild('drawer') drawer!: MatDrawer;

  constructor(
    protected overflowService: OverflowService,
    private notificationService: NotificationService,
    private loadingService: LoadingService,
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
    effect(() => {
      if (this.refreshTokenOverview()) {
        this.onRefreshTokenOverview();
      }
    });
    effect(() => {
      if (this.refreshContainerOverview()) {
        this.onRefreshContainerOverview();
      }
    });
    effect(() => {
      this.selectedContent();
      this.loadingService.clearAllLoadings();
      this.updateOverflowState();
    });
  }

  ngAfterViewInit() {
    window.addEventListener('resize', this.updateOverflowState.bind(this));
    this.updateOverflowState();
  }

  updateOverflowState() {
    setTimeout(() => {
      this.isTokenDrawerOverflowing.set(
        this.overflowService.isHeightOverflowing({
          selector: '.token-layout',
          thresholdSelector: '.drawer',
        }),
      );
    }, 400);
  }

  ngOnDestroy() {
    window.removeEventListener('resize', this.updateOverflowState);
  }

  onRefreshTokenOverview(): void {
    if (this.tokenTableComponent) {
      this.tokenTableComponent.fetchTokenData();
      this.refreshTokenOverview.set(false);
    }
  }

  onRefreshContainerOverview(): void {
    if (this.containerTableComponent) {
      this.containerTableComponent.fetchContainerData();
      this.refreshContainerOverview.set(false);
    }
  }

  onRefreshTokenDetails(): void {
    if (this.tokenDetailsComponent) {
      this.tokenDetailsComponent.showTokenDetail().subscribe({
        next: () => {
          this.refreshTokenDetails.set(false);
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
      });
    } else {
      console.warn('ContainerDetailsComponent is not yet initialized.');
      this.notificationService.openSnackBar(
        'ContainerDetailsComponent is not yet initialized.',
      );
    }
  }
}
