import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { TokenComponent } from '../../token.component';
import { MatCheckbox } from '@angular/material/checkbox';

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
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'motp')
    ?.text;
  @Input() motpPin!: WritableSignal<string>;
  @Input() description!: WritableSignal<string>;
  @Input() generateOnServer!: WritableSignal<boolean>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() repeatMotpPin!: WritableSignal<string>;
}
