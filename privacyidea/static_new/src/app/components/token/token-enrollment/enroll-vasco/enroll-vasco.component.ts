import { Component, effect, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { MatCheckbox } from '@angular/material/checkbox';

@Component({
  selector: 'app-enroll-vasco',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatCheckbox,
  ],
  templateUrl: './enroll-vasco.component.html',
  styleUrl: './enroll-vasco.component.scss',
})
export class EnrollVascoComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'vasco')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() useVascoSerial!: WritableSignal<boolean>;
  @Input() vascoSerial!: WritableSignal<string>;

  constructor() {
    effect(() => {
      if (this.useVascoSerial()) {
        const otpHex = this.otpKey();
        const serial = this.convertOtpKeyToVascoSerial(otpHex);
        this.vascoSerial.set(serial);
      }
    });
  }

  private convertOtpKeyToVascoSerial(otpHex: string): string {
    let vascoOtpStr = '';
    for (let i = 0; i < otpHex.length; i += 2) {
      vascoOtpStr += String.fromCharCode(parseInt(otpHex.slice(i, i + 2), 16));
    }
    return vascoOtpStr.slice(0, 10);
  }
}
