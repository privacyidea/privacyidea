import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-totp',
  imports: [
    FormsModule,
    MatCheckbox,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatError,
  ],
  templateUrl: './enroll-totp.component.html',
  styleUrl: './enroll-totp.component.scss',
})
export class EnrollTotpComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'totp')
    ?.text;
  @Input() generateOnServer!: WritableSignal<boolean>;
  @Input() otpLength!: WritableSignal<number>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() hashAlgorithm!: WritableSignal<string>;
  @Input() timeStep!: WritableSignal<number | string>;
  @Input() description!: WritableSignal<string>;
}
