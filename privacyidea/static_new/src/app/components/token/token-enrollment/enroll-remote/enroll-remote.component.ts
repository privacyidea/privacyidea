import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  PrivacyideaServerService,
  RemoteServer,
} from '../../../../services/privavyidea-server/privacyidea-server.service';
import { TokenService } from '../../../../services/token/token.service';

export class RemoteErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value.id === '' : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-remote',
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
export class EnrollRemoteComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'remote')?.text;
  @Input() checkPinLocally!: WritableSignal<boolean>;
  @Input() description!: WritableSignal<string>;
  @Input() remoteServer!: WritableSignal<RemoteServer>;
  @Input() remoteSerial!: WritableSignal<string>;
  @Input() remoteUser!: WritableSignal<string>;
  @Input() remoteRealm!: WritableSignal<string>;
  @Input() remoteResolver!: WritableSignal<string>;

  remoteServerOptions = this.privacyideaServerService.remoteServerOptions;
  remoteErrorStateMatcher = new RemoteErrorStateMatcher();

  constructor(
    private privacyideaServerService: PrivacyideaServerService,
    private tokenService: TokenService,
  ) {}
}
