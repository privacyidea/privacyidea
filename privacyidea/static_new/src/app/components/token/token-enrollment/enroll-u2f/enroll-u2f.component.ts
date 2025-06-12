import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface U2fEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'u2f';
  // Keine typspezifischen Felder für die Initialisierung über EnrollmentOptions
}
@Component({
  selector: 'app-enroll-u2f',
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-u2f.component.html',
  styleUrl: './enroll-u2f.component.scss',
})
export class EnrollU2fComponent {
  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'u2f')
    ?.text;
  @Input() description!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
