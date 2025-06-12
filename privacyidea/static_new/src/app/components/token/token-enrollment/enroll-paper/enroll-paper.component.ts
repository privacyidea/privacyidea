import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface PaperEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'paper';
  // Keine typspezifischen Felder für die Initialisierung über EnrollmentOptions
}
@Component({
  selector: 'app-enroll-paper',
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-paper.component.html',
  styleUrl: './enroll-paper.component.scss',
})
export class EnrollPaperComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'paper')?.text;
  @Input() description!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
