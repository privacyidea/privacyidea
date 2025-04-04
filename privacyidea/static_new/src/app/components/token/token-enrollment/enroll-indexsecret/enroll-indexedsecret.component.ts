import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-indexedsecret',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-indexedsecret.component.html',
  styleUrl: './enroll-indexedsecret.component.scss',
})
export class EnrollIndexedsecretComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'indexedsecret')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() otpKey!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
