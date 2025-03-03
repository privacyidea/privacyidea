import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-tan',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tan.component.html',
  styleUrl: './enroll-tan.component.scss',
})
export class EnrollTanComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'tan')?.text;
  @Input() description!: WritableSignal<string>;
}
