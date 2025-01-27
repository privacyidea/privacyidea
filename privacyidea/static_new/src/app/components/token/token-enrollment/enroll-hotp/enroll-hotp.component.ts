import { Component, Input, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import {
  MatFormField,
  MatHint,
  MatLabel,
  MatOption,
  MatSelect,
} from '@angular/material/select';
import { MatInput } from '@angular/material/input';

@Component({
  selector: 'app-enroll-hotp',
  imports: [
    MatCheckbox,
    FormsModule,
    MatSelect,
    MatOption,
    MatLabel,
    MatFormField,
    MatInput,
    MatHint,
  ],
  templateUrl: './enroll-hotp.component.html',
  styleUrl: './enroll-hotp.component.scss',
})
export class EnrollHotpComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'hotp')?.text;
  @Input() generateOnServer!: WritableSignal<boolean>;
  @Input() otpLength!: WritableSignal<number>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() hashAlgorithm!: WritableSignal<string>;
  @Input() description!: WritableSignal<string>;
  protected readonly TokenComponent = TokenComponent;
}
