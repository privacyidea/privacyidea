import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { TokenComponent } from '../../token.component';
import { MatError } from '@angular/material/select';

@Component({
  selector: 'app-enroll-yubikey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel, MatHint, MatError],
  templateUrl: './enroll-yubikey.component.html',
  styleUrl: './enroll-yubikey.component.scss',
})
export class EnrollYubikeyComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'yubikey')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() otpLength!: WritableSignal<number>;
  @Input() testYubiKey!: WritableSignal<string>;

  ngOnInit() {
    this.otpLength.set(44);
  }
}
