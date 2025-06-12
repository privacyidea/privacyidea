import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface SpassEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'spass';
  // Keine typspezifischen Felder für die Initialisierung über EnrollmentOptions
}
@Component({
  selector: 'app-enroll-spass',
  imports: [FormsModule],
  templateUrl: './enroll-spass.component.html',
  styleUrl: './enroll-spass.component.scss',
})
export class EnrollSpassComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'spass')?.text;
  @Input() description!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
