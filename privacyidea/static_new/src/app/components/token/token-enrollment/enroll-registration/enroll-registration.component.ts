import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface RegistrationEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'registration';
  // Keine typspezifischen Felder für die Initialisierung über EnrollmentOptions
}
@Component({
  selector: 'app-enroll-registration',
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-registration.component.html',
  styleUrl: './enroll-registration.component.scss',
})
export class EnrollRegistrationComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'registration')?.text;
  @Input() description!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
