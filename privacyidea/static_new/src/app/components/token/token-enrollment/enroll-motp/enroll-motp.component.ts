import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatCheckbox } from '@angular/material/checkbox';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-motp',
  imports: [
    FormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-motp.component.html',
  styleUrl: './enroll-motp.component.scss',
})
export class EnrollMotpComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'motp')?.text;
  @Input() motpPin!: WritableSignal<string>;
  @Input() description!: WritableSignal<string>;
  @Input() generateOnServer!: WritableSignal<boolean>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() repeatMotpPin!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
