import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import { PrivacyideaServerService } from '../../../../services/privavyidea-server/privacyidea-server.service';

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

  constructor(private privacyideaServerService: PrivacyideaServerService) {}

  ngOnInit(): void {
    this.privacyideaServerService
      .getRemoteServerOptions()
      .subscribe((response) => {
        const options = Object.values(response.result.value).map(
          (option: any) => ({
            url: option.url,
            id: option.id,
          }),
        );
        this.remoteServerOptions.set(options);
      });
  }
}
