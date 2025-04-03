import { Component, Input, WritableSignal } from '@angular/core';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { MatCheckbox } from '@angular/material/checkbox';
import { ErrorStateMatcher } from '@angular/material/core';

export class VascoErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid =
      control && control.value ? control.value.length !== 496 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-vasco',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-vasco.component.html',
  styleUrl: './enroll-vasco.component.scss',
})
export class EnrollVascoComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'vasco')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() useVascoSerial!: WritableSignal<boolean>;
  @Input() vascoSerial!: WritableSignal<string>;
  vascoErrorStatematcher = new VascoErrorStateMatcher();

  static convertOtpKeyToVascoSerial(otpHex: string): string {
    let vascoOtpStr = '';
    for (let i = 0; i < otpHex.length; i += 2) {
      vascoOtpStr += String.fromCharCode(parseInt(otpHex.slice(i, i + 2), 16));
    }
    return vascoOtpStr.slice(0, 10);
  }
}
