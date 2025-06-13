import {
  Component,
  computed,
  EventEmitter,
  OnInit,
  Output,
} from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  PrivacyideaServerService,
  RemoteServer,
} from '../../../../services/privavyidea-server/privacyidea-server.service';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface RemoteEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'remote';
  remoteServer: RemoteServer | null; // or specific type if RemoteServer is complex
  remoteSerial: string;
  remoteUser: string;
  remoteRealm: string;
  remoteResolver: string;
  checkPinLocally: boolean;
}

export class RemoteErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value.id === '' : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-remote',
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatOption,
    MatSelect,
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-remote.component.html',
  styleUrl: './enroll-remote.component.scss',
})
export class EnrollRemoteComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'remote')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  checkPinLocallyControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);
  remoteServerControl = new FormControl<RemoteServer | null>(null, [
    Validators.required,
  ]);
  remoteSerialControl = new FormControl<string>('', [Validators.required]);
  remoteUserControl = new FormControl<string>(''); // Optional, depending on configuration
  remoteRealmControl = new FormControl<string>(''); // Optional
  remoteResolverControl = new FormControl<string>('', [Validators.required]);

  remoteForm = new FormGroup({
    checkPinLocally: this.checkPinLocallyControl,
    remoteServer: this.remoteServerControl,
    remoteSerial: this.remoteSerialControl,
    remoteUser: this.remoteUserControl,
    remoteRealm: this.remoteRealmControl,
    remoteResolver: this.remoteResolverControl,
  });

  remoteServerOptions = this.privacyideaServerService.remoteServerOptions;
  remoteErrorStateMatcher = new RemoteErrorStateMatcher();

  constructor(
    private privacyideaServerService: PrivacyideaServerService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      checkPinLocally: this.checkPinLocallyControl,
      remoteServer: this.remoteServerControl,
      remoteSerial: this.remoteSerialControl,
      remoteUser: this.remoteUserControl,
      remoteRealm: this.remoteRealmControl,
      remoteResolver: this.remoteResolverControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.remoteForm.invalid) {
      this.remoteForm.markAllAsTouched();
      return undefined;
    }

    const enrollmentData: RemoteEnrollmentOptions = {
      ...basicOptions,
      type: 'remote',
      checkPinLocally: !!this.checkPinLocallyControl.value,
      remoteServer: this.remoteServerControl.value,
      remoteSerial: this.remoteSerialControl.value ?? '',
      remoteUser: this.remoteUserControl.value ?? '',
      remoteRealm: this.remoteRealmControl.value ?? '',
      remoteResolver: this.remoteResolverControl.value ?? '',
    };

    return this.tokenService.enrollToken(enrollmentData);
  };
}
