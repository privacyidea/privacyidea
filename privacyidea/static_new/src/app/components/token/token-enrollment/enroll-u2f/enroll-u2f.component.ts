import { Component, Input, WritableSignal } from '@angular/core';
import { TokenComponent } from '../../token.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-enroll-u2f',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-u2f.component.html',
  styleUrl: './enroll-u2f.component.scss',
})
export class EnrollU2fComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'u2f')
    ?.text;
  @Input() description!: WritableSignal<string>;
}
