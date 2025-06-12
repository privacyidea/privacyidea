import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface TanEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'tan';
  // Keine typspezifischen Felder für die Initialisierung über EnrollmentOptions
}
@Component({
  selector: 'app-enroll-tan',
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tan.component.html',
  styleUrl: './enroll-tan.component.scss',
})
export class EnrollTanComponent {
  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'tan')
    ?.text;
  @Input() description!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
