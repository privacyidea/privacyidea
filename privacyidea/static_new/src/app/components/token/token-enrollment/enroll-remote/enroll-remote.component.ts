import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import { PrivacyideaServerService } from '../../../../services/privavyidea-server/privacyidea-server.service';

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
  text = TokenComponent.tokenTypes.find((type) => type.key === 'remote')?.text;
  @Input() checkPinLocally!: WritableSignal<boolean>;
  @Input() description!: WritableSignal<string>;
  @Input() remoteServer!: WritableSignal<{ url: string; id: string }>;
  @Input() remoteSerial!: WritableSignal<string>;
  @Input() remoteUser!: WritableSignal<string>;
  @Input() remoteRealm!: WritableSignal<string>;
  @Input() remoteResolver!: WritableSignal<string>;
  remoteServerOptions = signal<{ url: string; id: string }[]>([]);
  remoteErrorStateMatcher = new RemoteErrorStateMatcher();

  constructor(private privacyideaServerService: PrivacyideaServerService) {}

  ngOnInit(): void {
    this.privacyideaServerService
      .getRemoteServerOptions()
      .subscribe((response) => {
        const rawValue = response?.result?.value;
        const options =
          rawValue && typeof rawValue === 'object'
            ? Object.values(rawValue).map((option: any) => ({
                url: option.url,
                id: option.id,
              }))
            : [];
        this.remoteServerOptions.set(options);
      });
  }
}
