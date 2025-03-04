import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-registration',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-registration.component.html',
  styleUrl: './enroll-registration.component.scss',
})
export class EnrollRegistrationComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'registration')
    ?.text;
  @Input() description!: WritableSignal<string>;
}
