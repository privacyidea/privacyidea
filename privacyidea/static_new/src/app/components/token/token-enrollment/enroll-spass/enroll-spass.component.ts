import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-spass',
  imports: [FormsModule, MatFormField, MatInput, MatLabel],
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
